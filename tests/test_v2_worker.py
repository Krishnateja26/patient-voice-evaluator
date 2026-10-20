from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from voice_evaluator.agent import models, worker
from voice_evaluator.config import Settings


@pytest.mark.parametrize("recorder_fails", [True, False])
async def test_local_recording_armed_before_dial_and_cleanup(tmp_path, monkeypatch, recorder_fails):
    settings = Settings(
        _env_file=None,
        enable_live_calls=True,
        livekit_url="wss://example.test",
        livekit_api_key="test",
        livekit_api_secret="test",
        sip_outbound_trunk_id="ST_test",
        caller_number="+12125550123",
        artifacts_dir=tmp_path,
    )
    order = []
    callbacks = {}

    class Session:
        def on(self, name, callback=None):
            def register(fn):
                callbacks[name] = fn
                return fn

            return register(callback) if callback else register

        async def start(self, **kwargs):
            assert kwargs["room_options"].participant_identity == "assessment-line"
            assert kwargs["record"] is False
            order.append("session_ready")

        aclose = AsyncMock()

    session = Session()

    class Room:
        connect = AsyncMock()
        disconnect = AsyncMock()

        def on(self, name):
            return lambda fn: fn

    room = Room()
    monkeypatch.setattr(worker.rtc, "Room", lambda: room)

    class Recorder:
        def __init__(self, folder, identity, on_failure=None):
            self.folder = folder

        async def start(self, *args):
            order.append("recording_ready")
            if recorder_fails:
                raise RuntimeError("Disk recording unavailable")

        close = AsyncMock()

        def finalize(self):
            path = self.folder / "recording.mp3"
            path.write_bytes(b"test-recording")
            return path

    recorder = Recorder(tmp_path, "test")

    def create_recorder(folder, identity, on_failure=None):
        recorder.folder = folder
        return recorder

    monkeypatch.setattr(worker, "LocalRecorder", create_recorder)
    monkeypatch.setattr(worker, "AgentSession", lambda **kwargs: session)
    monkeypatch.setattr(worker, "room_token", lambda *args, **kwargs: "test-token")
    for name in ("STT", "LLM", "TTS", "TurnDetector"):
        monkeypatch.setattr(models.inference, name, lambda **kwargs: object())

    async def dial(request):
        assert order == ["recording_ready", "session_ready"]
        assert request.sip_call_to == "+18054398008"
        assert request.sip_number == "+12125550123"
        order.append("dialed")
        callbacks["close"](None)

    sip = SimpleNamespace(create_sip_participant=AsyncMock(side_effect=dial))
    client = SimpleNamespace(
        sip=sip, room=SimpleNamespace(delete_room=AsyncMock()), aclose=AsyncMock()
    )
    monkeypatch.setattr(worker.api, "LiveKitAPI", lambda *args: client)
    monkeypatch.setattr(
        worker, "ingest_recording", lambda call, path: call.update_metadata(audio_validated=True)
    )
    if recorder_fails:
        with pytest.raises(RuntimeError, match="Disk recording unavailable"):
            await worker.run_call("weekend_appointment_request", settings=settings)
        sip.create_sip_participant.assert_not_awaited()
    else:
        call = await worker.run_call("weekend_appointment_request", settings=settings)
        assert call.read_metadata()["status"] == "ended"
        assert call.read_metadata()["termination_reason"] == "session_closed"
        assert call.read_metadata()["recording_source"] == "local_rtc_subscriber"
        assert call.has_recording()
        session.aclose.assert_awaited_once()
    recorder.close.assert_awaited_once()
    client.room.delete_room.assert_awaited_once()
    client.aclose.assert_awaited_once()
    room.disconnect.assert_awaited_once()


async def test_standalone_call_owns_http_session(monkeypatch):
    sessions = []

    async def fake_call(*args, **kwargs):
        sessions.append(worker.http_context.http_session())
        assert not sessions[-1].closed
        raise RuntimeError("simulated provider failure")

    monkeypatch.setattr(worker, "_run_call", fake_call)
    with pytest.raises(RuntimeError, match="simulated provider failure"):
        await worker.run_call("test")
    assert sessions[0].closed


