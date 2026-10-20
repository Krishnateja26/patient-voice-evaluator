from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
from typer.testing import CliRunner

from voice_evaluator.artifacts.store import CallArtifacts
from voice_evaluator.cli import app
from voice_evaluator.config import Settings
from voice_evaluator.recording import local
from voice_evaluator.recording.audio import ingest_recording


async def test_capture_subscribed_speakers_encode_locally(tmp_path, monkeypatch):
    handlers = {}

    class Room:
        connect = AsyncMock()
        disconnect = AsyncMock()

        def on(self, name):
            def register(fn):
                handlers[name] = fn
                return fn

            return register

    monkeypatch.setattr(local.rtc, "Room", Room)

    class Stream:
        def __init__(self, track, **kwargs):
            self.track = track

        def __aiter__(self):
            return self.frames()

        async def frames(self):
            frequency = 300 if self.track.speaker == "patient" else 700
            data = (
                (5000 * np.sin(2 * np.pi * frequency * np.arange(32000) / local.RATE))
                .astype("<i2")
                .tobytes()
            )
            yield SimpleNamespace(frame=SimpleNamespace(data=data))

        aclose = AsyncMock()

    monkeypatch.setattr(local.rtc, "AudioStream", Stream)
    call = CallArtifacts("call-001", tmp_path)
    call.write_metadata(
        {
            "recording_source": "local_rtc_subscriber",
            "recording_channel_mapping": ["patient", "agent"],
        }
    )
    recorder = local.LocalRecorder(call.dir, "patient-test")
    await recorder.start("wss://example.test", "test-token")
    for identity, speaker in (
        ("patient-test", "patient"),
        ("assessment-line", "agent"),
        ("unknown", "ignored"),
    ):
        handlers["track_subscribed"](
            SimpleNamespace(kind=local.rtc.TrackKind.KIND_AUDIO, speaker=speaker),
            None,
            SimpleNamespace(identity=identity),
        )
    import asyncio

    await asyncio.gather(*recorder.tasks)
    await recorder.close()
    path = recorder.finalize()
    ingest_recording(call, path)
    assert path == call.recording_mp3
    assert call.read_metadata()["audio_validated"] is True
    assert set(recorder.tracks) == {"patient", "agent"}
    assert 1.9 < call.read_metadata()["audio_duration_seconds"] < 2.1


def test_one_command_saves_transcript_and_runs_evaluation(tmp_path, monkeypatch):
    from voice_evaluator.agent import worker
    from voice_evaluator.evaluation import pipeline

    call = CallArtifacts("call-001", tmp_path)
    call.recording_mp3.write_bytes(b"mocked-audio")
    call.write_metadata({"recording_source": "local_rtc_subscriber"})
    call.write_json(
        call.dir / "live_transcript.json",
        [
            {"role": "user", "text": "How can I help?", "elapsed_seconds": 1},
            {"role": "assistant", "text": "An appointment please.", "elapsed_seconds": 2},
        ],
    )
    settings = Settings(
        _env_file=None,
        enable_live_calls=True,
        livekit_url="wss://example.test",
        livekit_api_key="key",
        livekit_api_secret="secret",
        sip_outbound_trunk_id="ST_test",
        caller_number="+12125550123",
        artifacts_dir=tmp_path,
    )
    monkeypatch.setattr("voice_evaluator.cli.get_settings", lambda: settings)
    run = AsyncMock(return_value=call)
    monkeypatch.setattr(worker, "run_call", run)
    evaluations = []
    monkeypatch.setattr(pipeline, "evaluate_call", lambda *args, **kwargs: evaluations.append(args))
    result = CliRunner().invoke(app, ["call", "--execute"])
    assert result.exit_code == 0, result.output
    run.assert_awaited_once()
    assert call.has_transcript()
    assert call.transcript_txt.is_file()
    assert call.read_json(call.transcript_json)["transcript_source"] == "live_observations"
    assert evaluations
    assert "Saved call-001" in result.output


def test_no_storage_or_manual_worker_setup_required():
    settings = Settings(_env_file=None)
    assert not any("S3" in field for field in settings.missing_for_real_calls())
    assert "recording_s3_bucket" not in Settings.model_fields
    result = CliRunner().invoke(app, ["--help"])
    assert "fetch-recording" not in result.output
