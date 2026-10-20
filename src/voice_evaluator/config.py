"""Version 2 settings. Live calls are disabled by default."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSESSMENT_NUMBER = "+18054398008"
ALLOWED_DESTINATIONS = frozenset({ASSESSMENT_NUMBER})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    sip_outbound_trunk_id: str = ""
    caller_number: str = ""
    enable_live_calls: bool = False
    stt_model: str = "deepgram/nova-3"
    llm_model: str = "openai/gpt-4.1-mini"
    tts_model: str = "cartesia/sonic-3"
    tts_voice: str = "f786b574-daa5-4673-aa0c-cbe3e8534c02"
    openai_api_key: str = ""
    transcribe_model: str = "whisper-1"
    judge_model: str = "gpt-4.1"
    adjudicator_model: str = "gpt-4.1-mini"
    enable_adjudication: bool = False
    endpointing_mode: Literal["fixed", "dynamic"] = "dynamic"
    endpoint_min_delay: float = Field(default=0.3, ge=0, le=5)
    endpoint_max_delay: float = Field(default=2.5, ge=0.1, le=10)
    interruption_mode: Literal["adaptive", "vad"] = "adaptive"
    interruption_min_duration: float = Field(default=0.5, ge=0, le=5)
    interruption_min_words: int = Field(default=0, ge=0, le=10)
    preemptive_generation: bool = True
    simulation_seed: int = Field(default=42, ge=0, le=2147483647)
    max_call_seconds: int = Field(default=210, ge=30, le=420)
    artifacts_dir: Path = REPO_ROOT / "artifacts"
    scenarios_dir: Path = REPO_ROOT / "scenarios"
    prompts_dir: Path = REPO_ROOT / "prompts"

    @field_validator("stt_model", "llm_model", "tts_model")
    @classmethod
    def reject_speech_to_speech(cls, value: str) -> str:
        normalized = value.lower().replace("-", "").replace("_", "")
        if any(token in normalized for token in ("realtime", "geminilive", "speechtospeech")):
            raise ValueError("Only separate STT, text LLM, and TTS models are permitted")
        return value

    @model_validator(mode="after")
    def valid_timing_range(self):
        if self.endpoint_min_delay > self.endpoint_max_delay:
            raise ValueError("Endpoint minimum must not exceed maximum")
        return self

    def missing_for_real_calls(self):
        names = [
            "livekit_url",
            "livekit_api_key",
            "livekit_api_secret",
            "sip_outbound_trunk_id",
            "caller_number",
            "tts_voice",
        ]
        missing = [name.upper() for name in names if not getattr(self, name).strip()]
        return missing

    def missing_for_offline_analysis(self):
        return [] if self.openai_api_key else ["OPENAI_API_KEY"]


@lru_cache(maxsize=1)
def get_settings():
    return Settings()


def reset_settings_cache():
    get_settings.cache_clear()
