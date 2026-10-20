"""Evidence-based readiness. Unknown and missing evidence never pass."""

import ast
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from voice_evaluator.artifacts.store import load_all_calls
from voice_evaluator.config import ASSESSMENT_NUMBER, REPO_ROOT
from voice_evaluator.recording.audio import sha256

QUALITY = (
    "coherence",
    "naturalness",
    "turn_taking",
    "pauses",
    "interruptions",
    "latency",
    "audio",
    "scenario_steering",
    "state_consistency",
    "conversation_completeness",
)


class CallReview(BaseModel):
    reviewer: str = Field(min_length=2)
    notes: str = Field(min_length=10)
    listened_to_audio: bool
    both_sides_audible: bool
    transcript_matches_audio: bool
    meaningful_conversation: bool
    dimensions: dict[str, Literal["pass", "fail"]]

    @model_validator(mode="after")
    def all_dimensions(self):
        if set(self.dimensions) != set(QUALITY):
            raise ValueError("Review must score all ten conversation-quality dimensions")
        return self


def call_qualification(call):
    """Return every disqualifying reason; no duration-only minimum is invented."""
    reasons = []
    meta = call.read_metadata()
    recording = call.recording_path
    if not recording or not meta.get("audio_validated"):
        reasons.append("Recording missing or undecoded")
    elif sha256(recording) != meta.get("recording_sha256"):
        reasons.append("Recording changed since validation")
    if not call.has_transcript() or not call.transcript_txt.is_file():
        reasons.append("Canonical JSON/text transcript missing")
    else:
        try:
            data = call.read_json(call.transcript_json)
            turns = data.get("turns", [])
            if {t.get("speaker") for t in turns} != {"patient", "agent"} or len(turns) < 2:
                reasons.append("Transcript lacks both named speakers")
            if data.get("recording_sha256") != meta.get("recording_sha256"):
                reasons.append("Transcript is not tied to the recording hash")
        except (ValueError, TypeError, AttributeError):
            reasons.append("Transcript is malformed")
    if meta.get("destination") != ASSESSMENT_NUMBER:
        reasons.append("Destination missing or unauthorized")
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", str(meta.get("caller_number", ""))):
        reasons.append("Originating number missing or not E.164")
    if meta.get("status") != "ended":
        reasons.append("Call did not end normally; investigate before qualification")
    snapshot = call.dir / "scenario.json"
    if not snapshot.is_file() and not call.scenario_path.is_file():
        reasons.append("Scenario snapshot missing")
    review = meta.get("call_review")
    try:
        parsed = CallReview.model_validate(review)
        if not all(
            (
                parsed.listened_to_audio,
                parsed.both_sides_audible,
                parsed.transcript_matches_audio,
                parsed.meaningful_conversation,
                *[v == "pass" for v in parsed.dimensions.values()],
            )
        ):
            reasons.append("Human audio/quality review did not pass")
        if not recording or review.get("recording_sha256") != sha256(recording):
            reasons.append("Human review is not tied to current audio")
        if not call.has_transcript() or review.get("transcript_sha256") != sha256(
            call.transcript_json
        ):
            reasons.append("Human review is not tied to current transcript")
    except (ValueError, TypeError, AttributeError):
        reasons.append("Complete human call-quality review missing")
    return reasons


@dataclass
class ReviewItem:
    area: str
    status: str
    requirements: str
    evidence: str
    correction: str


def audit(settings, root: Path = REPO_ROOT):
    calls = load_all_calls(settings.artifacts_dir)
    qualified = []
    rejected = {}
    for call in calls:
        reasons = call_qualification(call)
        if reasons:
            rejected[call.call_id] = reasons
        else:
            qualified.append(call)
    rows = []

    def add(area, status, req, evidence, correction=""):
        rows.append(ReviewItem(area, status, req, evidence, correction))

    source = root / "src/voice_evaluator/agent/worker.py"
    banned = []
    session_args = set()
    for f in (root / "src/voice_evaluator").rglob("*.py"):
        tree = ast.parse(f.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                name = ast.unparse(node.func)
                if any(
                    term in name for term in ("RealtimeModel", "realtime.connect", "gemini_live")
                ):
                    banned.append(str(f.relative_to(root)))
                if name == "AgentSession":
                    session_args.update(k.arg for k in node.keywords)
    architecture = source.is_file() and {"stt", "llm", "tts"} <= session_args and not banned
    add(
        "Architecture",
        "PASS" if architecture else "FAIL",
        "C07-C09",
        "Python AgentSession has separately identifiable STT/LLM/TTS; no prohibited live model construction"
        if architecture
        else str(banned),
        "Replace noncompliant live components" if not architecture else "",
    )
    caller_numbers = {c.read_metadata().get("caller_number") for c in calls}
    destinations = {c.read_metadata().get("destination") for c in calls}
    telephony = bool(qualified) and len(caller_numbers) == 1 and destinations == {ASSESSMENT_NUMBER}
    add(
        "Telephony",
        "PASS" if telephony else "FAIL",
        "C03,C29,C40",
        f"{len(qualified)} qualified calls; {len(caller_numbers)} distinct originating IDs",
        "Configure LiveKit/SIP, preserve caller identity, make and review real calls"
        if not telephony
        else "",
    )
    for area, req in (
        ("Voice behavior", "C27,C34-C36"),
        ("Scenario realism", "C04,C25,C35"),
        ("Turn handling", "C34"),
        ("Interruptions", "C25,C34"),
        ("Latency", "C36"),
    ):
        add(
            area,
            "PASS WITH ISSUES" if qualified else "FAIL",
            req,
            f"{len(qualified)} human-reviewed calls; complete campaign coverage must also be reviewed",
            "Listen to pilot recordings, correct caller defects and record measured results",
        )
    add(
        "Recording",
        "PASS" if len(qualified) >= 10 else "FAIL",
        "C13-C14",
        f"{len(qualified)} qualified audio bundles; {len(calls)} total folders",
        "Retrieve and decode at least ten complete recordings, verify both voices, match hashes and review quality",
    )
    add(
        "Transcription",
        "PASS" if len(qualified) >= 10 else "FAIL",
        "C05,C13-C14",
        f"{len(qualified)} canonical transcripts tied to reviewed audio",
        "Transcribe routed channels and review wording, attribution and audio correspondence",
    )
    add(
        "Evaluation",
        "PASS WITH ISSUES",
        "C15,C28",
        "Deterministic, scenario, exact-evidence and adjudication layers exist; real-call calibration pending",
        "Evaluate canonical evidence and manually verify important findings",
    )
    report = root / "BUG_REPORT.md"
    report_ready = (
        report.is_file() and bool(qualified) and any(c.has_evaluation() for c in qualified)
    )
    add(
        "Bug reporting",
        "PASS WITH ISSUES" if report_ready else "FAIL",
        "C15,C28",
        "Report generator requires human verification for final findings; no useful verified findings established yet",
        "Produce concise verified findings with call, exact transcript and recording references",
    )
    documentation = all(
        (root / name).is_file()
        for name in (
            "README.md",
            "ARCHITECTURE.md",
            ".env.example",
            "ITERATION_LOG.md",
            "docs/SERVICE_SETUP.md",
        )
    )
    add(
        "Documentation",
        "PASS WITH ISSUES" if documentation else "FAIL",
        "C11-C12,C20-C22,C30-C31",
        "Local setup/reasoning documents present"
        if documentation
        else "Required guidance or iteration log missing",
        "Test actual account setup; add measured pilot iterations and final provider rationale",
    )
    add(
        "Repository requirements",
        "FAIL",
        "C23-C24,C37",
        "No independently checked private repository or collaborator evidence in this local audit",
        "Create a neutral-name private repository and verify reviewer access; keep it private",
    )
    add(
        "Submission requirements",
        "FAIL",
        "C01,C16-C19,C31,C38-C40",
        "Account context, call-based iteration, two videos and submitted form remain unverified",
        "Review product account, complete campaign/videos in own voice with webcam, verify access and submit correct caller number",
    )
    return {
        "verdict": "NOT SUBMISSION READY",
        "qualified_calls": len(qualified),
        "total_calls": len(calls),
        "rejected_calls": rejected,
        "reviews": [asdict(r) for r in rows],
        "note": "This local audit cannot certify external account settings, video content or submission status.",
    }


def render_audit(data):
    lines = [
        "# Strict compliance review",
        "",
        f"**{data['verdict']}**",
        "",
        f"Qualified calls: {data['qualified_calls']}/10; captured folders: {data['total_calls']}.",
        "",
        "| Area | Verdict | Requirement IDs | Evidence | Required correction |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in data["reviews"]:
        lines.append(
            "| "
            + " | ".join(
                str(row[key]).replace("|", "/")
                for key in ("area", "status", "requirements", "evidence", "correction")
            )
            + " |"
        )
    lines += [
        "",
        data["note"],
        "",
        "Requirement text and page references: docs/COMPLIANCE_CHECKLIST.md.",
    ]
    return "\n".join(lines) + "\n"
