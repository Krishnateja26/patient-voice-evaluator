from typer.testing import CliRunner

from voice_evaluator.cli import app
from voice_evaluator.config import Settings


def test_call_never_dispatches_without_explicit_execute(monkeypatch):
    monkeypatch.setattr("voice_evaluator.cli.get_settings", lambda: Settings(_env_file=None))
    result = CliRunner().invoke(app, ["call", "weekend_appointment_request"])
    assert result.exit_code != 0
    assert "--execute" in result.output


def test_execute_cannot_override_disabled_calls(monkeypatch):
    monkeypatch.setattr(
        "voice_evaluator.cli.get_settings",
        lambda: Settings(_env_file=None, enable_live_calls=False),
    )
    result = CliRunner().invoke(app, ["call", "weekend_appointment_request", "--execute"])
    assert result.exit_code != 0
    assert "ENABLE_LIVE_CALLS" in result.output


def test_incomplete_config_cannot_dispatch(monkeypatch):
    monkeypatch.setattr(
        "voice_evaluator.cli.get_settings", lambda: Settings(_env_file=None, enable_live_calls=True)
    )
    result = CliRunner().invoke(app, ["call", "weekend_appointment_request", "--execute"])
    assert result.exit_code != 0
    assert "LIVEKIT_API_KEY" in result.output


def test_cli_has_no_destination_option():
    result = CliRunner().invoke(app, ["call", "--help"])
    assert "--to" not in result.output


def test_offline_scenario_listing():
    result = CliRunner().invoke(app, ["scenarios"])
    assert result.exit_code == 0
    assert "weekend_appointment_request" in result.output


def test_realtime_models_rejected():
    import pytest
    from pydantic import ValidationError

    for model in ("openai/gpt-realtime", "gemini-live", "speech-to-speech"):
        with pytest.raises(ValidationError):
            Settings(_env_file=None, llm_model=model)
