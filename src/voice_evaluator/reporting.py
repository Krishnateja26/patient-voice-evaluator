"""Aggregate reporting: BUG_REPORT.md and submission readiness.

The bug report is generated from the per-call evaluations, but generation is not
the last step. Findings land in the report marked as candidates; a person moves
them to confirmed by setting ``human_verified`` after listening to the audio.
The generator preserves that flag across regenerations so verification work is
never lost when the report is rebuilt.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

from voice_evaluator.artifacts.store import CallArtifacts
from voice_evaluator.config import ASSESSMENT_NUMBER, Settings
from voice_evaluator.evaluation.schema import CallEvaluation, Finding, Severity

MIN_REQUIRED_CALLS = 10


# --------------------------------------------------------------- bug report


def render_bug_report(calls: list[CallArtifacts], *, verified_only: bool = False) -> str:
    """Build BUG_REPORT.md from evaluated calls."""
    evaluations: list[tuple[CallArtifacts, CallEvaluation]] = []
    for call in calls:
        data = call.read_json(call.evaluation_json)
        if data:
            evaluations.append((call, CallEvaluation.model_validate(data)))

    findings: list[tuple[CallArtifacts, str, Finding]] = []
    for call, evaluation in evaluations:
        pool = (
            [f for f in evaluation.findings_with_evidence() if f.human_verified]
            if verified_only
            else evaluation.all_findings
        )
        if verified_only and pool:
            from voice_evaluator.compliance import call_qualification
            from voice_evaluator.recording.audio import sha256

            if call_qualification(call) or evaluation.transcript_sha256 != sha256(
                call.transcript_json
            ):
                continue
        findings.extend((call, evaluation.scenario_id, f) for f in pool)

    findings.sort(key=lambda row: (row[2].severity.rank, row[0].call_id))

    by_severity: dict[Severity, int] = defaultdict(int)
    by_category: dict[str, int] = defaultdict(int)
    for _, _, finding in findings:
        by_severity[finding.severity] += 1
        by_category[finding.category.value] += 1

    verified_count = sum(1 for _, _, f in findings if f.human_verified)

    lines: list[str] = [
        "# Bug report — Pretty Good AI voice agent",
        "",
        f"Generated {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} from "
        f"{len(evaluations)} evaluated calls to {ASSESSMENT_NUMBER}.",
        "",
        "## How to read this",
        "",
        "Every entry cites a call id and a timestamp. The audio is at "
        "`artifacts/calls/<call-id>/recording.mp3` and the transcript at "
        "`artifacts/calls/<call-id>/transcript.txt`, so each claim can be checked in "
        "under a minute.",
        "",
        "Findings come from three layers: rule-based checks on the transcript "
        "(`deterministic`), the scenario's own pass/fail contract (`assertion`), and an "
        "LLM evaluator whose quotes are verified against the transcript before they are "
        "accepted (`judge`). Entries marked **verified** were additionally checked against "
        "the audio by a person.",
        "",
        "## Summary",
        "",
        f"- Calls analysed: **{len(evaluations)}**",
        f"- Findings: **{len(findings)}** ({verified_count} human-verified)",
        "",
        "| Severity | Count |",
        "| --- | --- |",
    ]
    for severity in Severity:
        lines.append(f"| {severity.value} | {by_severity.get(severity, 0)} |")

    lines += ["", "| Category | Count |", "| --- | --- |"]
    for category, count in sorted(by_category.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {category} | {count} |")

    lines += ["", "## Findings", ""]
    if not findings:
        lines += ["No findings recorded yet. Run `voice-evaluator evaluate` on captured calls.", ""]

    current_severity: Severity | None = None
    for call, scenario_id, finding in findings:
        if finding.severity != current_severity:
            current_severity = finding.severity
            lines += [f"### {finding.severity.value.upper()}", ""]
        lines += _render_finding(call, scenario_id, finding)

    lines += _render_call_index(evaluations)
    return "\n".join(lines)


def _render_finding(call: CallArtifacts, scenario_id: str, finding: Finding) -> list[str]:
    verified = " · **verified**" if finding.human_verified else ""
    first_evidence = next((e for e in finding.evidence if e.timestamp), None)
    where = f"{call.call_id} at {first_evidence.timestamp}" if first_evidence else call.call_id
    artifact_dir = call.dir.name

    lines = [
        f"#### `{finding.id}` — {finding.title}",
        "",
        f"**Severity:** {finding.severity.value} · **Category:** {finding.category.value} · "
        f"**Confidence:** {finding.confidence} · **Found by:** {finding.source.value}{verified}",
        "",
        f"**Where:** {where}  ",
        f"**Scenario:** `{scenario_id}`  ",
        f"**Audio:** `artifacts/calls/{artifact_dir}/{call.recording_path.name if call.recording_path else 'MISSING_AUDIO'}`  ",
        f"**Transcript:** `artifacts/calls/{artifact_dir}/transcript.txt`",
        "",
        f"**Expected:** {finding.expected}",
        "",
        f"**Actual:** {finding.actual}",
        "",
        f"**Why it matters:** {finding.why_it_matters}",
        "",
    ]
    if finding.evidence:
        lines += ["**Transcript evidence**", ""]
        for evidence in finding.evidence:
            speaker = evidence.speaker.upper() if evidence.speaker else "?"
            flag = "" if evidence.quote_verified else "  _(unverified quote)_"
            lines += [f"> `[{speaker} {evidence.timestamp}]` {evidence.quote}{flag}", ">"]
        lines.append("")
    if finding.reproduction:
        lines += [f"**Reproduce:** {finding.reproduction}", ""]
    lines += ["---", ""]
    return lines


def _render_call_index(evaluations: list[tuple[CallArtifacts, CallEvaluation]]) -> list[str]:
    lines = [
        "## Call index",
        "",
        "| Call | Scenario | Duration | Turns | Task success | Findings |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for call, evaluation in evaluations:
        success = evaluation.judge.task_success if evaluation.judge else "-"
        lines.append(
            f"| [{call.call_id}](artifacts/calls/{call.dir.name}/) | `{evaluation.scenario_id}` | "
            f"{evaluation.duration_seconds:.0f}s | {evaluation.turn_count} | {success} | "
            f"{len(evaluation.all_findings)} |"
        )
    lines.append("")
    return lines


# ------------------------------------------------------ submission status


@dataclass
class ChecklistItem:
    name: str
    ok: bool
    detail: str


@dataclass
class SubmissionStatus:
    items: list[ChecklistItem] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for item in self.items if item.ok)

    @property
    def total(self) -> int:
        return len(self.items)

    @property
    def complete(self) -> bool:
        return self.passed == self.total


def submission_status(settings: Settings) -> SubmissionStatus:
    """Expose strict audit results without inventing extra challenge clauses."""
    from voice_evaluator.compliance import audit

    data = audit(settings)
    return SubmissionStatus(
        items=[
            ChecklistItem(
                row["area"], row["status"] == "PASS", row["evidence"] + "; " + row["correction"]
            )
            for row in data["reviews"]
        ]
    )
