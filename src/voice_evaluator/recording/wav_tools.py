"""Dual-channel WAV handling, using only the standard library.

Twilio returns the call as a two-channel WAV where each party occupies its own
channel. Splitting those channels is the entire basis of speaker attribution in
this project, so it is worth not depending on an external binary for it:

* ``ffmpeg`` is not installed on most reviewers' machines and would become a
  setup step that can fail.
* ``audioop``, the obvious stdlib answer, was removed in Python 3.13.

So the split is done here by hand. It is a byte de-interleave, which is exact,
endian-agnostic and fast enough for three-minute calls.
"""

from __future__ import annotations

import math
import wave
from dataclasses import dataclass
from pathlib import Path


class AudioError(RuntimeError):
    """Raised when a recording cannot be read or is not usable."""


@dataclass
class WavInfo:
    channels: int
    sample_width: int
    frame_rate: int
    frame_count: int

    @property
    def duration_seconds(self) -> float:
        return self.frame_count / self.frame_rate if self.frame_rate else 0.0


@dataclass
class ChannelStats:
    """Loudness summary for one channel, used to prove both sides are audible."""

    rms: float
    peak: float
    silence_ratio: float
    duration_seconds: float

    @property
    def is_audible(self) -> bool:
        """Heuristic: real speech has energy and is not silent almost throughout."""
        return self.rms > 40.0 and self.silence_ratio < 0.97


def read_info(path: Path) -> WavInfo:
    with wave.open(str(path), "rb") as wf:
        return WavInfo(
            channels=wf.getnchannels(),
            sample_width=wf.getsampwidth(),
            frame_rate=wf.getframerate(),
            frame_count=wf.getnframes(),
        )


def split_channels(source: Path, out_dir: Path, names: list[str]) -> dict[str, Path]:
    """Write one mono WAV per channel of *source*.

    ``names`` labels the channels in order, e.g. ``["agent", "patient"]``.
    Returns a mapping of name -> written path.
    """
    if not source.exists():
        raise AudioError(f"recording not found: {source}")

    with wave.open(str(source), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if channels != len(names):
        raise AudioError(
            f"{source.name} has {channels} channel(s) but {len(names)} name(s) were given "
            f"({', '.join(names)}). Dual-channel recording may not have been enabled."
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    frame_size = width * channels
    view = memoryview(frames)
    frame_count = len(frames) // frame_size

    for index, name in enumerate(names):
        mono = bytearray(frame_count * width)
        base = index * width
        # For each byte position inside a sample, take every frame_size-th byte.
        for byte_offset in range(width):
            mono[byte_offset::width] = view[base + byte_offset :: frame_size]

        destination = out_dir / f"channel_{index}_{name}.wav"
        with wave.open(str(destination), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(width)
            out.setframerate(rate)
            out.writeframes(bytes(mono))
        written[name] = destination

    return written


def channel_stats(path: Path, *, window_ms: int = 40, silence_rms: float = 25.0) -> ChannelStats:
    """Measure loudness of a mono WAV.

    Used by the quality gate that checks both sides of a call were actually
    captured. A channel that is flat silence means the recording is unusable as
    evidence regardless of what the transcript says.
    """
    with wave.open(str(path), "rb") as wf:
        if wf.getnchannels() != 1:
            raise AudioError(f"{path.name} is not mono")
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    samples = _to_int_samples(frames, width)
    if not samples:
        return ChannelStats(rms=0.0, peak=0.0, silence_ratio=1.0, duration_seconds=0.0)

    peak = float(max(abs(s) for s in samples))
    total = sum(float(s) * float(s) for s in samples)
    rms = math.sqrt(total / len(samples))

    window = max(1, int(rate * window_ms / 1000))
    silent_windows = 0
    window_count = 0
    for start in range(0, len(samples) - window + 1, window):
        chunk = samples[start : start + window]
        chunk_rms = math.sqrt(sum(float(s) * float(s) for s in chunk) / len(chunk))
        window_count += 1
        if chunk_rms < silence_rms:
            silent_windows += 1

    return ChannelStats(
        rms=round(rms, 1),
        peak=peak,
        silence_ratio=round(silent_windows / window_count, 3) if window_count else 1.0,
        duration_seconds=round(len(samples) / rate, 2) if rate else 0.0,
    )


def _to_int_samples(raw: bytes, width: int) -> list[int]:
    """Decode PCM bytes into signed integers centred on zero."""
    if width == 2:
        return [
            int.from_bytes(raw[i : i + 2], "little", signed=True) for i in range(0, len(raw) - 1, 2)
        ]
    if width == 1:
        # 8-bit WAV is unsigned; shift it to be centred on zero and scale to
        # 16-bit so the thresholds above apply uniformly.
        return [(byte - 128) * 256 for byte in raw]
    raise AudioError(f"unsupported sample width: {width} bytes")
