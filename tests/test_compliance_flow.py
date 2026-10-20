from types import SimpleNamespace
from unittest.mock import AsyncMock

import av
import numpy as np
import pytest

from voice_evaluator.agent.barge_in import BargeInScheduler
from voice_evaluator.artifacts.store import CallArtifacts, load_all_calls, resolve_call_dir
from voice_evaluator.compliance import QUALITY, audit, call_qualification
from voice_evaluator.config import Settings
from voice_evaluator.evaluation import pipeline
from voice_evaluator.recording.audio import ingest_recording, sha256
from voice_evaluator.scenarios.loader import load_one
from voice_evaluator.scenarios.models import Behavior
from voice_evaluator.telephony.guard import InvalidPhoneNumber, pin_caller_number
from voice_evaluator.transcription.transcriber import ChannelTranscript, Segment


def write_mp3(path, silent_right=False):
    rate = 16000
    time = np.arange(rate * 2, dtype=np.float32) / rate
    left = (0.25 * np.sin(2 * np.pi * 300 * time)).astype(np.float32)
    right = (
        np.zeros_like(left)
        if silent_right
        else (0.2 * np.sin(2 * np.pi * 700 * time)).astype(np.float32)
    )
    with av.open(str(path), "w") as output:
        stream = output.add_stream("libmp3lame", rate=rate)
        stream.layout = "stereo"
        frame = av.AudioFrame.from_ndarray(np.stack([left, right]), format="fltp", layout="stereo")
        frame.sample_rate = rate
        for packet in stream.encode(frame):
            output.mux(packet)
        for packet in stream.encode(None):
            output.mux(packet)


def prepared(tmp_path):
    call = CallArtifacts("call-001", tmp_path / "artifacts")
    call.write_scenario(load_one("weekend_appointment_request"))
    call.write_metadata(
        {
            "call_id": call.call_id,
            "scenario_id": "weekend_appointment_request",
            "recording_source": "local_rtc_subscriber",
            "recording_channel_mapping": ["patient", "agent"],
            "destination": "+18054398008",
            "caller_number": "+12125550123",
            "status": "ended",
        }
    )
    source = tmp_path / "source.mp3"
    write_mp3(source)
    ingest_recording(call, source)
    return call


def test_uuid_call_discovery_and_ogg_recognition(tmp_path):
    identifier = "call-" + "a" * 32
    call = CallArtifacts(identifier, tmp_path)
    call.recording_ogg.write_bytes(b"OggS-test")
    assert [item.call_id for item in load_all_calls(tmp_path)] == [identifier]
    assert resolve_call_dir(identifier, tmp_path) == call.dir
    assert call.has_recording()
    assert call.recording_path.name == "recording.ogg"
    with pytest.raises(ValueError):
        resolve_call_dir("../../escape", tmp_path)
    with pytest.raises(ValueError):
        CallArtifacts("call-001", tmp_path, existing_dir=tmp_path.parent)


def test_campaign_caller_pin_is_persistent_and_fail_closed(tmp_path):
    assert pin_caller_number("(212) 555-0123", tmp_path) == "+12125550123"
    assert pin_caller_number("+12125550123", tmp_path) == "+12125550123"
    with pytest.raises(InvalidPhoneNumber, match="differs"):
        pin_caller_number("+12125550124", tmp_path)
    (tmp_path / "caller_identity.json").write_text("broken")
    with pytest.raises(InvalidPhoneNumber, match="invalid"):
        pin_caller_number("+12125550123", tmp_path)


def test_real_mp3_decode_and_channel_mapping(tmp_path):
    call = prepared(tmp_path)
    metadata = call.read_metadata()
    assert metadata["audio_validated"] is True
    assert 1.9 < metadata["audio_duration_seconds"] < 2.1
    assert metadata["recording_sha256"] == sha256(call.recording_mp3)
    assert sha256(call.dir / "channels/patient.wav") != sha256(call.dir / "channels/agent.wav")
    assert call_qualification(call)  # synthetic sounds and file presence never qualify a call


def test_dead_channel_and_corrupt_audio_rejected(tmp_path):
    call = CallArtifacts("call-001", tmp_path / "artifacts")
    call.write_metadata(
        {
            "recording_source": "local_rtc_subscriber",
            "recording_channel_mapping": ["patient", "agent"],
        }
    )
    source = tmp_path / "silent.mp3"
    write_mp3(source, silent_right=True)
    with pytest.raises(ValueError, match="insufficient"):
        ingest_recording(call, source)
    source.write_bytes(b"corrupt audio")
    with pytest.raises(av.error.InvalidDataError):
        ingest_recording(call, source)
    assert call.read_metadata()["audio_validated"] is False


def test_canonical_transcript_uses_correct_speakers_and_hash(tmp_path, monkeypatch):
    call = prepared(tmp_path)
    settings = Settings(
        _env_file=None, openai_api_key="not-used", artifacts_dir=tmp_path / "artifacts"
    )
    monkeypatch.setattr(pipeline, "OpenAI", lambda **kwargs: object())
    seen = []

    def transcribe(client, path, *, speaker, model):
        seen.append((speaker, path.name))
        return ChannelTranscript(
            speaker=speaker,
            model="mock",
            text="Appointment please" if speaker == "patient" else "What day?",
            segments=[
                Segment(
                    speaker=speaker,
                    start=0 if speaker == "agent" else 1,
                    end=0.5 if speaker == "agent" else 1.5,
                    text="What day?" if speaker == "agent" else "Appointment please",
                )
            ],
        )

    monkeypatch.setattr(pipeline, "transcribe_channel", transcribe)
    pipeline.transcribe_call(call, settings)
    assert seen == [("patient", "patient.wav"), ("agent", "agent.wav")]
    transcript = call.read_json(call.transcript_json)
    assert transcript["recording_sha256"] == sha256(call.recording_mp3)
    assert {t["speaker"] for t in transcript["turns"]} == {"agent", "patient"}
    review = {
        "reviewer": "Human tester",
        "notes": "Synthetic fixture explicitly represents a completed human review for gate testing only",
        "listened_to_audio": True,
        "both_sides_audible": True,
        "transcript_matches_audio": True,
        "meaningful_conversation": True,
        "dimensions": dict.fromkeys(QUALITY, "pass"),
        "recording_sha256": sha256(call.recording_mp3),
        "transcript_sha256": sha256(call.transcript_json),
    }
    call.update_metadata(call_review=review)
    assert call_qualification(call) == []
    call.transcript_json.write_text(call.transcript_json.read_text() + " ")
    assert "Human review is not tied to current transcript" in call_qualification(call)
    call.recording_mp3.write_bytes(b"changed")
    assert "Recording changed since validation" in call_qualification(call)


def test_zero_calls_cannot_pass_telephony_recording_or_submission(tmp_path):
    result = audit(Settings(_env_file=None, artifacts_dir=tmp_path / "artifacts"))
    assert result["verdict"] == "NOT SUBMISSION READY"
    rows = {r["area"]: r for r in result["reviews"]}
    for area in (
        "Telephony",
        "Recording",
        "Transcription",
        "Repository requirements",
        "Submission requirements",
    ):
        assert rows[area]["status"] == "FAIL"
        assert rows[area]["requirements"] and rows[area]["correction"]


async def test_real_barge_in_attempt_is_single_and_cancelable(monkeypatch):
    events = []
    timeline = SimpleNamespace(record=lambda kind, **kw: events.append(kind))
    handle = SimpleNamespace(wait_for_playout=AsyncMock())
    say = []
    session = SimpleNamespace(
        agent_state="listening", say=lambda text, **kw: say.append(text) or handle
    )
    behavior = Behavior(
        interrupt_agent=True,
        interruption_utterance="Sorry, what date?",
        interruption_after_seconds=0,
        interruption_after_turns=2,
    )
    scheduler = BargeInScheduler(session, behavior, timeline)
    scheduler.on_item(SimpleNamespace(item=SimpleNamespace(role="user")))
    scheduler.on_state(SimpleNamespace(new_state="speaking"))
    assert scheduler.task is None
    scheduler.on_item(SimpleNamespace(item=SimpleNamespace(role="user")))
    scheduler.on_state(SimpleNamespace(new_state="speaking"))
    await scheduler.task
    scheduler.on_state(SimpleNamespace(new_state="speaking"))
    assert say == ["Sorry, what date?"]
    assert events == ["patient_barge_in_attempt"]
    await scheduler.aclose()


async def test_pending_barge_in_cancelled_when_target_finishes():
    timeline = SimpleNamespace(record=lambda *args, **kwargs: None)
    session = SimpleNamespace(
        agent_state="listening", say=lambda *args, **kwargs: pytest.fail("No speech should play")
    )
    behavior = Behavior(
        interrupt_agent=True,
        interruption_utterance="Wait",
        interruption_after_seconds=2,
        interruption_after_turns=0,
    )
    scheduler = BargeInScheduler(session, behavior, timeline)
    scheduler.on_state(SimpleNamespace(new_state="speaking"))
    scheduler.on_state(SimpleNamespace(new_state="listening"))
    await scheduler.aclose()
    assert not scheduler.attempted


def test_cached_evaluation_cannot_survive_changed_transcript(tmp_path):
    call = prepared(tmp_path)
    canonical = {
        "recording_sha256": sha256(call.recording_mp3),
        "timestamps_available": True,
        "turns": [
            {
                "index": 0,
                "speaker": "agent",
                "start": 0,
                "end": 0.5,
                "text": "What can I help with?",
            },
            {
                "index": 1,
                "speaker": "patient",
                "start": 0.6,
                "end": 1.5,
                "text": "An appointment please.",
            },
        ],
    }
    call.write_json(call.transcript_json, canonical)
    call.transcript_txt.write_text("What can I help with? An appointment please.")
    settings = Settings(_env_file=None, artifacts_dir=tmp_path / "artifacts")
    evaluation = pipeline.evaluate_call(call, settings, use_judge=False)
    assert evaluation.transcript_sha256 == sha256(call.transcript_json)
    call.transcript_json.write_text(call.transcript_json.read_text() + " ")
    with pytest.raises(pipeline.PipelineError, match="changed"):
        pipeline.evaluate_call(call, settings, use_judge=False)


def test_human_review_cli_exposes_documented_option():
    from typer.testing import CliRunner

    from voice_evaluator.cli import app

    result = CliRunner().invoke(app, ["review-call", "--help"])
    assert result.exit_code == 0
    assert "--review-file" in result.output
