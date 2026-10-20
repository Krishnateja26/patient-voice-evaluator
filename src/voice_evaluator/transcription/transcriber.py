"""Post-call ASR on separately routed speaker channels.

Live conversation items are diagnostic. Canonical text is generated from the
saved recording; timestamps are ASR estimates and still require audio review.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from openai import OpenAI

log = logging.getLogger("voice_evaluator.transcription")

# Fallback model used when the configured model does not return timestamps.
# Timestamps are not optional here: without them the two channels cannot be
# interleaved into a single conversation.
TIMESTAMPED_FALLBACK_MODEL = "whisper-1"

# Models discovered at runtime not to support `verbose_json` + segment
# timestamps. A rejected request still costs money -- and a call has two
# channels, so without this the same doomed attempt is paid for twice per call,
# every call. Remembering the refusal turns that into one wasted request per
# process, and the set is rebuilt on each run so the day a model gains
# timestamp support it is picked up automatically.
_NO_TIMESTAMP_SUPPORT: set[str] = set()


def reset_transcription_capability_cache() -> None:
    """Forget which models refused timestamps. For tests."""
    _NO_TIMESTAMP_SUPPORT.clear()


@dataclass
class Segment:
    speaker: str
    start: float
    end: float
    text: str
    confidence: float | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "speaker": self.speaker,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "text": self.text,
            "confidence": self.confidence,
        }


@dataclass
class ChannelTranscript:
    speaker: str
    model: str
    text: str
    segments: list[Segment] = field(default_factory=list)
    had_timestamps: bool = True


def transcribe_channel(
    client: OpenAI,
    audio_path: Path,
    *,
    speaker: str,
    model: str,
    language: str = "en",
) -> ChannelTranscript:
    """Transcribe one mono channel, preferring timestamped output.

    Falls back to a model known to return segment timestamps if the configured
    one refuses ``verbose_json``.
    """
    candidates = [m for m in (model, TIMESTAMPED_FALLBACK_MODEL) if m not in _NO_TIMESTAMP_SUPPORT]
    if not candidates:
        candidates = [TIMESTAMPED_FALLBACK_MODEL]

    for attempt_model in dict.fromkeys(candidates):
        try:
            return _transcribe_verbose(client, audio_path, speaker, attempt_model, language)
        except Exception as exc:  # noqa: BLE001 - provider errors vary by model
            _NO_TIMESTAMP_SUPPORT.add(attempt_model)
            log.info(
                "%s does not return segment timestamps (%s); using %s for the rest of this run",
                attempt_model,
                exc,
                TIMESTAMPED_FALLBACK_MODEL,
            )

    # Last resort: plain text, one segment spanning the channel.
    log.warning("falling back to untimed transcription for %s", audio_path.name)
    with audio_path.open("rb") as fh:
        response = client.audio.transcriptions.create(model=model, file=fh, language=language)
    text = getattr(response, "text", "") or ""
    return ChannelTranscript(
        speaker=speaker,
        model=model,
        text=text,
        segments=[Segment(speaker=speaker, start=0.0, end=0.0, text=text)] if text else [],
        had_timestamps=False,
    )


def _transcribe_verbose(
    client: OpenAI, audio_path: Path, speaker: str, model: str, language: str
) -> ChannelTranscript:
    with audio_path.open("rb") as fh:
        response = client.audio.transcriptions.create(
            model=model,
            file=fh,
            language=language,
            response_format="verbose_json",
            timestamp_granularities=["segment"],
        )

    raw_segments = getattr(response, "segments", None) or []
    if not raw_segments:
        raise ValueError(f"{model} returned no segments")

    segments: list[Segment] = []
    for raw in raw_segments:
        text = (_attr(raw, "text") or "").strip()
        if not text:
            continue
        segments.append(
            Segment(
                speaker=speaker,
                start=float(_attr(raw, "start") or 0.0),
                end=float(_attr(raw, "end") or 0.0),
                text=text,
                confidence=_segment_confidence(raw),
            )
        )

    return ChannelTranscript(
        speaker=speaker,
        model=model,
        text=(getattr(response, "text", "") or " ".join(s.text for s in segments)).strip(),
        segments=segments,
        had_timestamps=True,
    )


def _attr(obj: object, name: str) -> object:
    """Read a field from either an SDK model or a plain dict."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _segment_confidence(raw: object) -> float | None:
    """Whisper reports avg_logprob; convert it to a rough 0-1 confidence.

    This is only used to flag low-confidence evidence for human review, so an
    approximation is fine. It must never be presented as a calibrated number.
    """
    avg_logprob = _attr(raw, "avg_logprob")
    if avg_logprob is None:
        return None
    try:
        import math

        return round(min(1.0, math.exp(float(avg_logprob))), 3)
    except (TypeError, ValueError, OverflowError):
        return None
