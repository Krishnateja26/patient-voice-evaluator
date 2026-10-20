"""The live caller uses only LiveKit Inference services."""

from unittest.mock import Mock

from voice_evaluator.agent import models
from voice_evaluator.agent.session import turn_options
from voice_evaluator.config import Settings


def settings(**overrides):
    return Settings(_env_file=None, **overrides)


def test_llm_uses_livekit_project_credentials(monkeypatch):
    llm = Mock(return_value="livekit-llm")
    monkeypatch.setattr(models.inference, "LLM", llm)
    configured = settings(livekit_api_key="lk-key", livekit_api_secret="lk-secret")

    assert models.build_llm(configured) == "livekit-llm"
    llm.assert_called_once_with(
        model="openai/gpt-4.1-mini", api_key="lk-key", api_secret="lk-secret"
    )


def test_speech_uses_livekit_project_credentials(monkeypatch):
    stt = Mock(return_value="livekit-stt")
    tts = Mock(return_value="livekit-tts")
    monkeypatch.setattr(models.inference, "STT", stt)
    monkeypatch.setattr(models.inference, "TTS", tts)
    configured = settings(livekit_api_key="lk-key", livekit_api_secret="lk-secret")

    assert models.build_speech(configured) == ("livekit-stt", "livekit-tts", None)
    stt.assert_called_once_with(
        model="deepgram/nova-3", language="en", api_key="lk-key", api_secret="lk-secret"
    )
    tts.assert_called_once_with(
        model="cartesia/sonic-3",
        voice="f786b574-daa5-4673-aa0c-cbe3e8534c02",
        api_key="lk-key",
        api_secret="lk-secret",
    )


def test_live_call_credentials_do_not_require_openai_key():
    configured = settings(
        livekit_url="wss://example.test",
        livekit_api_key="lk-key",
        livekit_api_secret="lk-secret",
        sip_outbound_trunk_id="ST_test",
        caller_number="+12125550123",
    )

    assert configured.openai_api_key == ""
    assert configured.missing_for_real_calls() == []


def test_turn_options_use_livekit_turn_detector(monkeypatch):
    detector = object()
    monkeypatch.setattr(models.inference, "TurnDetector", Mock(return_value=detector))

    options = turn_options(settings())

    assert options["turn_detection"] is detector
    assert options["endpointing"]["mode"] == "dynamic"
    assert options["interruption"]["mode"] == "adaptive"
    assert options["preemptive_generation"]["enabled"] is True
