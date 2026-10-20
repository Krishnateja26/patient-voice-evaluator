"""Post-call pipeline: recording -> transcript -> evaluation -> bug candidates.

Runs entirely offline against artifacts already on disk, so it can be re-run any
number of times without touching the phone network. That separation is what
makes it cheap to improve the evaluator after the calls have been made.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from openai import OpenAI

from voice_evaluator.artifacts.store import CallArtifacts, resolve_call_dir
from voice_evaluator.config import Settings
from voice_evaluator.evaluation import assertions, deterministic
from voice_evaluator.evaluation.judge import evaluate_with_judge
from voice_evaluator.evaluation.schema import CallEvaluation, Finding
from voice_evaluator.recording.downloader import analyse_recording
from voice_evaluator.recording.wav_tools import AudioError
from voice_evaluator.scenarios.loader import load_one
from voice_evaluator.scenarios.models import Scenario
from voice_evaluator.transcription.merge import (
    MergedTranscript,
    merge_channels,
    reconcile_overlaps,
    render_text,
)
from voice_evaluator.transcription.transcriber import ChannelTranscript, transcribe_channel
from voice_evaluator.utils.events import read_events

log = logging.getLogger("voice_evaluator.pipeline")


class PipelineError(RuntimeError):
    pass


def transcribe_call(
    artifacts: CallArtifacts, settings: Settings, *, force: bool = False
) -> MergedTranscript:
    """Produce transcript.json / transcript.txt from the recording."""
    if artifacts.has_transcript() and not force:
        log.info("%s already transcribed; use --force to redo", artifacts.call_id)
        return _load_transcript(artifacts)

    if artifacts.read_metadata().get("recording_source") == "local_rtc_subscriber":
        return _transcribe_local(artifacts, settings)

    if not artifacts.recording_wav.exists():
        raise PipelineError(
            f"{artifacts.call_id}: no local recording.wav to transcribe. Run "
            f"'voice-evaluator call --execute' to create local call evidence."
        )

    try:
        recording = analyse_recording(artifacts)
    except AudioError as exc:
        raise PipelineError(f"{artifacts.call_id}: {exc}") from exc

    client = OpenAI(api_key=settings.openai_api_key)
    channels: list[ChannelTranscript] = []
    for speaker, path in recording.channel_paths.items():
        log.info("transcribing %s channel of %s", speaker, artifacts.call_id)
        channels.append(
            transcribe_channel(client, path, speaker=speaker, model=settings.transcribe_model)
        )

    transcript = merge_channels(channels)
    metadata = artifacts.read_metadata()
    reconcile_overlaps(
        transcript, observed_interruptions=observed_interruptions(artifacts, metadata)
    )
    header = _transcript_header(artifacts, metadata, recording.duration_seconds)

    artifacts.write_json(artifacts.transcript_json, transcript.to_dict())
    artifacts.transcript_txt.write_text(render_text(transcript, header=header), encoding="utf-8")
    artifacts.update_metadata(
        transcribed_at=datetime.now(UTC).isoformat(),
        transcription_models=transcript.models_used,
        transcript_turn_count=len(transcript.turns),
    )
    return transcript


def evaluate_call(
    artifacts: CallArtifacts,
    settings: Settings,
    *,
    scenario: Scenario | None = None,
    use_judge: bool = True,
    force: bool = False,
) -> CallEvaluation:
    """Run all evaluation layers over an already-transcribed call."""
    if artifacts.has_evaluation() and not force:
        from voice_evaluator.recording.audio import sha256

        cached = artifacts.read_json(artifacts.evaluation_json) or {}
        if not artifacts.has_transcript() or cached.get("transcript_sha256") != sha256(
            artifacts.transcript_json
        ):
            raise PipelineError("Canonical transcript changed; re-evaluate with --force")
        log.info("%s already evaluated; use --force to redo", artifacts.call_id)
        return CallEvaluation.model_validate(artifacts.read_json(artifacts.evaluation_json))

    metadata = artifacts.read_metadata()
    if metadata.get("recording_source") == "local_rtc_subscriber":
        from voice_evaluator.recording.audio import sha256

        recording = artifacts.recording_path
        data = artifacts.read_json(artifacts.transcript_json) or {}
        if (
            recording is None
            or not metadata.get("audio_validated")
            or sha256(recording) != metadata.get("recording_sha256")
            or (data and data.get("recording_sha256") != metadata.get("recording_sha256"))
        ):
            raise PipelineError(
                "Recording/transcript evidence is missing or changed; validate and transcribe the local recording again"
            )
    scenario_id = metadata.get("scenario_id", "")
    if scenario is None:
        scenario = _load_scenario_for_call(artifacts, scenario_id, settings)

    transcript = (
        _load_transcript(artifacts)
        if artifacts.has_transcript()
        else transcribe_call(artifacts, settings)
    )

    metrics = dict(metadata.get("metrics") or {})
    metrics.setdefault("duration_seconds", metadata.get("audio_duration_seconds", 0.0))

    det_findings = deterministic.run_all(transcript, call_id=artifacts.call_id, metrics=metrics)
    assert_findings = assertions.run_all(scenario, transcript, call_id=artifacts.call_id)
    warnings = deterministic.quality_gate_warnings(transcript, metrics)
    warnings += list(metadata.get("recording_warnings") or [])
    transcript_data = artifacts.read_json(artifacts.transcript_json) or {}
    if transcript_data.get("transcript_source") == "live_observations":
        warnings.append(
            "Live text is not independent audio ASR; verify quotations against recording before reporting"
        )

    judge_result = None
    if use_judge:
        if not settings.openai_api_key:
            warnings.append("judge skipped: OPENAI_API_KEY is not set")
        else:
            client = OpenAI(api_key=settings.openai_api_key)
            try:
                judge_result = evaluate_with_judge(
                    client=client,
                    scenario=scenario,
                    transcript=transcript,
                    metrics=metrics,
                    deterministic_titles=[f.title for f in det_findings + assert_findings],
                    settings=settings,
                    call_id=artifacts.call_id,
                )
            except Exception as exc:
                log.exception("judge failed for %s", artifacts.call_id)
                warnings.append(f"judge failed: {exc}")

    from voice_evaluator.recording.audio import sha256

    evaluation = CallEvaluation(
        call_id=artifacts.call_id,
        transcript_sha256=sha256(artifacts.transcript_json),
        scenario_id=scenario.id,
        evaluated_at=datetime.now(UTC).isoformat(),
        judge_model=settings.judge_model if judge_result else None,
        call_completed=bool(metadata.get("call_completed", False)),
        duration_seconds=float(metrics.get("duration_seconds") or 0.0),
        turn_count=len(transcript.turns),
        deterministic_findings=det_findings,
        assertion_findings=assert_findings,
        judge=judge_result,
        quality_gate_warnings=sorted(set(warnings)),
        metrics=metrics,
    )

    artifacts.write_json(artifacts.evaluation_json, evaluation)
    markdown = render_evaluation_markdown(evaluation, scenario)
    display_name = artifacts.read_metadata().get("call_name")
    if display_name:
        markdown = markdown.replace(
            f"# Evaluation — {evaluation.call_id}", f"# {display_name} — Evaluation", 1
        )
    artifacts.evaluation_md.write_text(markdown, encoding="utf-8")
    artifacts.update_metadata(
        evaluated_at=evaluation.evaluated_at,
        finding_count=len(evaluation.all_findings),
        task_success=judge_result.task_success if judge_result else None,
    )
    return evaluation


# --------------------------------------------------------------- rendering


def render_evaluation_markdown(evaluation: CallEvaluation, scenario: Scenario) -> str:
    lines: list[str] = [
        f"# Evaluation — {evaluation.call_id}",
        "",
        f"**Scenario:** `{scenario.id}` — {scenario.title}  ",
        f"**Category:** {scenario.category.value} · **Difficulty:** {scenario.difficulty.value}  ",
        f"**Duration:** {evaluation.duration_seconds:.0f}s · **Turns:** {evaluation.turn_count}  ",
        f"**Evaluated:** {evaluation.evaluated_at}",
        "",
        "## What the caller wanted",
        "",
        scenario.objective,
        "",
    ]

    if scenario.hypothesis:
        lines += ["**Weakness being probed:** " + scenario.hypothesis, ""]

    if evaluation.judge:
        j = evaluation.judge
        lines += [
            "## Outcome",
            "",
            f"**Task success:** `{j.task_success}` — {j.task_success_justification}",
            "",
            j.conversation_summary,
            "",
            "### Dimension scores",
            "",
            "| Dimension | Score | Justification |",
            "| --- | --- | --- |",
        ]
        for name, dim in j.dimensions.items():
            justification = dim.justification.replace("|", "\\|")
            lines.append(f"| {name} | {dim.score}/5 | {justification} |")
        lines.append("")

        if j.expected_behavior_verdicts:
            lines += ["### Expected behaviours", ""]
            for v in j.expected_behavior_verdicts:
                icon = {"met": "PASS", "not_met": "FAIL", "unclear": "????"}[v.verdict]
                lines.append(f"- **[{icon}]** {v.behavior} — {v.justification}")
            lines.append("")

        if j.forbidden_behavior_verdicts:
            lines += ["### Forbidden behaviours", ""]
            for v in j.forbidden_behavior_verdicts:
                # "met" here means the forbidden thing happened.
                icon = {"met": "FAIL", "not_met": "PASS", "unclear": "????"}[v.verdict]
                lines.append(f"- **[{icon}]** {v.behavior} — {v.justification}")
            lines.append("")

    findings = evaluation.all_findings
    lines += [f"## Bug candidates ({len(findings)})", ""]
    if not findings:
        lines += ["No defects were identified in this call.", ""]
    for finding in findings:
        lines += _render_finding(finding)

    if evaluation.quality_gate_warnings:
        lines += ["## Harness warnings", ""]
        lines += [
            "These concern this test harness or the recording, not the agent under test.",
            "",
        ]
        lines += [f"- {w}" for w in evaluation.quality_gate_warnings]
        lines.append("")

    if evaluation.metrics:
        lines += ["## Measured metrics", "", "```json"]
        import json as _json

        lines.append(_json.dumps(evaluation.metrics, indent=2, default=str))
        lines += ["```", ""]

    if evaluation.judge and evaluation.judge.notes:
        lines += ["## Evaluator notes", "", evaluation.judge.notes, ""]

    return "\n".join(lines)


def _render_finding(finding: Finding) -> list[str]:
    lines = [
        f"### [{finding.severity.value.upper()}] {finding.title}",
        "",
        f"- **Category:** {finding.category.value}",
        f"- **Source:** {finding.source.value} · **Confidence:** {finding.confidence}",
        f"- **Expected:** {finding.expected}",
        f"- **Actual:** {finding.actual}",
        f"- **Why it matters:** {finding.why_it_matters}",
    ]
    if finding.source.value == "judge":
        lines.append(
            f"- **Adjudication:** {finding.adjudication_verdict}: {finding.adjudication_reason}"
        )
        lines.append(f"- **Human verified:** {finding.human_verified}")
    if finding.reproduction:
        lines.append(f"- **Reproduce:** {finding.reproduction}")
    if finding.evidence:
        lines += ["", "**Evidence**", ""]
        for e in finding.evidence:
            flag = (
                ""
                if e.quote_verified
                else "  _(evidence rejected: " + ", ".join(e.verification_errors) + ")_"
            )
            speaker = e.speaker.upper() if e.speaker else "?"
            lines.append(f"> `[{speaker} {e.timestamp}]` {e.quote}{flag}")
            lines.append(">")
    lines.append("")
    return lines


# ----------------------------------------------------------------- helpers


def _transcript_header(artifacts: CallArtifacts, metadata: dict, duration: float) -> str:
    return "\n".join(
        [
            f"Call: {artifacts.call_id}",
            f"Scenario: {metadata.get('scenario_id', 'unknown')} — {metadata.get('scenario_title', '')}",
            f"Placed: {metadata.get('started_at', 'unknown')}",
            f"Duration: {duration:.1f}s",
            f"Caller: {metadata.get('from_number', 'unknown')} -> {metadata.get('to_number', 'unknown')}",
            "Speaker labels derive from separate recording channels, not diarisation.",
            "=" * 70,
        ]
    )


def observed_interruptions(artifacts: CallArtifacts, metadata: dict | None = None) -> int | None:
    """How many interruptions the bridge counted from the live audio stream.

    This is the authoritative figure: the bridge saw speech-onset events on the
    wire, rather than reconstructing timing from a transcript. Returns None when
    the call produced no usable stream record, in which case transcript-derived
    overlaps have nothing to be checked against.
    """
    metadata = metadata if metadata is not None else artifacts.read_metadata()
    metrics = metadata.get("metrics") or {}
    if "interruptions_by_agent" in metrics or "interruptions_by_patient" in metrics:
        return int(metrics.get("interruptions_by_agent", 0)) + int(
            metrics.get("interruptions_by_patient", 0)
        )

    # Older calls, or calls whose metrics were lost, still have the event log.
    events = read_events(artifacts.events_path)
    if not events:
        return None
    if not any(e.get("event") == "media_stream.connected" for e in events):
        return None
    return sum(1 for e in events if str(e.get("event", "")).startswith("barge_in."))


def _load_transcript(artifacts: CallArtifacts) -> MergedTranscript:
    from voice_evaluator.transcription.merge import Turn

    data = artifacts.read_json(artifacts.transcript_json) or {}
    return MergedTranscript(
        turns=[
            Turn(
                index=t["index"],
                speaker=t["speaker"],
                start=t["start"],
                end=t["end"],
                text=t["text"],
                confidence=t.get("confidence"),
                overlaps_previous=t.get("overlaps_previous", False),
            )
            for t in data.get("turns", [])
        ],
        overlap_events=data.get("overlap_events", []),
        models_used=data.get("models_used", {}),
        timestamps_available=data.get("timestamps_available", True),
        clamped_segments=data.get("clamped_segments", 0),
        suppressed_overlaps=data.get("suppressed_overlaps", []),
        observed_interruptions=data.get("observed_interruptions"),
    )


def _load_scenario_for_call(
    artifacts: CallArtifacts, scenario_id: str, settings: Settings
) -> Scenario:
    """Prefer the scenario snapshot stored with the call, so re-evaluation is exact."""
    json_snapshot = artifacts.dir / "scenario.json"
    if json_snapshot.exists():
        return Scenario.model_validate_json(json_snapshot.read_text(encoding="utf-8"))
    if artifacts.scenario_path.exists():
        import yaml

        raw = yaml.safe_load(artifacts.scenario_path.read_text(encoding="utf-8"))
        return Scenario.model_validate(raw)
    if scenario_id:
        return load_one(scenario_id, settings.scenarios_dir)
    raise PipelineError(
        f"{artifacts.call_id}: cannot determine which scenario was run "
        f"(no scenario.yaml and no scenario_id in metadata)"
    )


def find_call_dir(call_id: str, artifacts_dir: Path | None = None) -> CallArtifacts:
    existing = resolve_call_dir(call_id, artifacts_dir)
    if existing is None:
        artifacts = CallArtifacts(call_id, artifacts_dir)
        raise PipelineError(f"no call artifacts found for '{call_id}' at {artifacts.dir}")
    artifacts = CallArtifacts(call_id, artifacts_dir, existing_dir=existing)
    if not artifacts.metadata_path.exists():
        raise PipelineError(f"no call artifacts found for '{call_id}' at {artifacts.dir}")
    return artifacts


def _transcribe_local(artifacts, settings):
    from voice_evaluator.recording.audio import sha256

    metadata = artifacts.read_metadata()
    recording = artifacts.recording_path
    if not metadata.get("audio_validated") or recording is None:
        raise PipelineError("Fetch and validate the call recording before transcription")
    if sha256(recording) != metadata.get("recording_sha256"):
        raise PipelineError("Recording changed since validation; re-ingest before transcription")
    if metadata.get("recording_channel_mapping") != ["patient", "agent"]:
        raise PipelineError("Unknown speaker channel mapping")
    for speaker in ("patient", "agent"):
        path = artifacts.dir / "channels" / f"{speaker}.wav"
        if not path.is_file() or sha256(path) != metadata.get("channel_sha256", {}).get(speaker):
            raise PipelineError(
                "Speaker channel changed since recording validation; validate the local recording again"
            )
    if not settings.openai_api_key:
        raise PipelineError("OPENAI_API_KEY is needed for post-call transcription")
    client = OpenAI(api_key=settings.openai_api_key)
    channels = [
        transcribe_channel(
            client,
            artifacts.dir / "channels" / f"{speaker}.wav",
            speaker=speaker,
            model=settings.transcribe_model,
        )
        for speaker in ("patient", "agent")
    ]
    transcript = merge_channels(channels)
    # No synthetic SDK observation times are substituted for audio-aligned ASR timestamps.
    data = transcript.to_dict()
    data["recording_sha256"] = sha256(recording)
    data["speaker_attribution_source"] = (
        "Local room participant identities; human audio review pending"
    )
    artifacts.write_json(artifacts.transcript_json, data)
    artifacts.transcript_txt.write_text(
        render_text(transcript, header=f"Call: {artifacts.call_id}; audio: {recording.name}"),
        encoding="utf-8",
    )
    artifacts.update_metadata(
        transcribed_at=datetime.now(UTC).isoformat(),
        transcript_turn_count=len(transcript.turns),
        transcript_recording_sha256=sha256(recording),
    )
    return transcript
