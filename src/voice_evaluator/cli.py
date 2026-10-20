"""Offline-first CLI and explicit dispatch for the LiveKit worker."""

import asyncio
import json

import typer

from voice_evaluator.agent.prompt import build_patient_prompt
from voice_evaluator.config import get_settings
from voice_evaluator.scenarios.loader import load_all, load_one

app = typer.Typer(no_args_is_help=True)


@app.command()
def scenarios():
    """List validated patient scenarios without contacting a provider."""
    for scenario in load_all():
        typer.echo(f"{scenario.id}: {scenario.title}")


@app.command()
def dry_run(scenario_id: str, seed: int = 42):
    """Print the patient instructions; makes no calls."""
    scenario = load_one(scenario_id)
    if scenario.simulation:
        from voice_evaluator.agent.patient import CONTROLLED_PERSONA
        from voice_evaluator.agent.state import PatientState

        typer.echo(
            CONTROLLED_PERSONA + "\n" + PatientState(scenario.simulation, seed).renderer_context()
        )
    else:
        typer.echo(build_patient_prompt(scenario))


@app.command()
def preflight():
    """Check configuration without contacting a provider."""
    settings = get_settings()
    missing = settings.missing_for_real_calls()
    typer.echo("Missing: " + ", ".join(missing) if missing else "Required settings present")
    typer.echo(f"Live calls enabled: {settings.enable_live_calls}")
    if missing:
        raise typer.Exit(1)


@app.command()
def call(
    scenario_id: str = typer.Argument("schedule_new_patient_knee"),
    execute: bool = False,
    seed: int = typer.Option(42, min=0, max=2147483647),
):
    """One command: call, record locally, export transcript and evaluate."""
    load_one(scenario_id)
    settings = get_settings()
    if not execute or not settings.enable_live_calls:
        raise typer.BadParameter("Use --execute and ENABLE_LIVE_CALLS=true to place a call")
    missing = settings.missing_for_real_calls()
    if missing:
        raise typer.BadParameter("Missing: " + ", ".join(missing))
    from voice_evaluator.agent.worker import install_known_cleanup_filter, run_call
    from voice_evaluator.evaluation.pipeline import evaluate_call, transcribe_call
    from voice_evaluator.transcription.live import export_live_transcript

    mark_recording_validated = install_known_cleanup_filter()
    artifacts = asyncio.run(run_call(scenario_id, seed=seed, settings=settings))
    if artifacts.read_metadata().get("audio_validated"):
        # This one-shot CLI process can still have native handles collected as it
        # exits. Filter the SDK's exact duplicate-drop assertion only after audio
        # has been decoded and validated; all other unraisable errors stay visible.
        mark_recording_validated()
    export_live_transcript(artifacts)
    # Optional offline ASR and semantic judging use the same direct API credential.
    # A provider failure keeps the local audio/live transcript available for review.
    if settings.openai_api_key:
        try:
            transcribe_call(artifacts, settings, force=True)
        except Exception:  # noqa: BLE001 - retain evidence rather than discard a recorded call
            typer.echo("Offline ASR unavailable; saved live transcript needs audio review.")
    try:
        evaluate_call(artifacts, settings, use_judge=bool(settings.openai_api_key), force=True)
    except Exception:  # noqa: BLE001 - a judge failure cannot erase the recording
        typer.echo("Evaluation incomplete; recording and transcript are preserved for rerun.")
    typer.echo(f"Saved {artifacts.read_metadata().get('call_name', artifacts.call_id)}: {artifacts.dir}")
    typer.echo(
        "Listen before the next call. Findings remain candidates until checked against audio."
    )


@app.command()
def transcribe(call_id: str, force: bool = False):
    """Transcribe validated separate speaker channels; uses paid offline ASR."""
    from voice_evaluator.evaluation.pipeline import find_call_dir, transcribe_call

    settings = get_settings()
    result = transcribe_call(find_call_dir(call_id, settings.artifacts_dir), settings, force=force)
    typer.echo(f"Transcribed {len(result.turns)} audio-aligned turns")


@app.command()
def evaluate(call_id: str, use_judge: bool = False, force: bool = False):
    """Evaluate a canonical transcript. --use-judge enables paid text requests."""
    from voice_evaluator.evaluation.pipeline import evaluate_call, find_call_dir

    settings = get_settings()
    result = evaluate_call(
        find_call_dir(call_id, settings.artifacts_dir), settings, use_judge=use_judge, force=force
    )
    typer.echo(f"{len(result.all_findings)} candidates; none automatically human verified")


@app.command("review-call")
def review_call(
    call_id: str, review_file: str = typer.Option(..., help="Completed human review JSON")
):
    """Record your own audio review from a completed review JSON file."""
    from datetime import UTC, datetime
    from pathlib import Path

    from voice_evaluator.compliance import CallReview
    from voice_evaluator.evaluation.pipeline import find_call_dir
    from voice_evaluator.recording.audio import sha256

    call = find_call_dir(call_id, get_settings().artifacts_dir)
    review = CallReview.model_validate_json(Path(review_file).read_text(encoding="utf-8"))
    if call.recording_path is None or not call.has_transcript():
        raise typer.BadParameter("Audio and canonical transcript must exist before review")
    data = review.model_dump() | {
        "recording_sha256": sha256(call.recording_path),
        "transcript_sha256": sha256(call.transcript_json),
        "reviewed_at": datetime.now(UTC).isoformat(),
    }
    call.update_metadata(call_review=data)
    from voice_evaluator.compliance import call_qualification

    reasons = call_qualification(call)
    call.update_metadata(call_completed=not reasons)
    typer.echo("Call qualified" if not reasons else "Not qualified: " + "; ".join(reasons))


@app.command()
def report():
    """Generate the final report using only human-verified findings."""
    from voice_evaluator.artifacts.store import load_all_calls
    from voice_evaluator.config import REPO_ROOT
    from voice_evaluator.reporting import render_bug_report

    (REPO_ROOT / "BUG_REPORT.md").write_text(
        render_bug_report(load_all_calls(), verified_only=True), encoding="utf-8"
    )
    typer.echo("BUG_REPORT.md generated; unreviewed candidates excluded")


@app.command()
def verify():
    """Save a strict offline audit; exits nonzero while requirements remain open."""
    from voice_evaluator.compliance import audit, render_audit
    from voice_evaluator.config import REPO_ROOT

    data = audit(get_settings())
    (REPO_ROOT / "COMPLIANCE_REVIEW.md").write_text(render_audit(data), encoding="utf-8")
    (REPO_ROOT / "artifacts" / "compliance_review.json").write_text(
        json.dumps(data, indent=2), encoding="utf-8"
    )
    typer.echo(render_audit(data))
    if data["verdict"] != "SUBMISSION READY":
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
