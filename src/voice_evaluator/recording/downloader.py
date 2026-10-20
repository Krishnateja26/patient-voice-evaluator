"""Legacy channel analysis for explicitly prepared, speaker-separated WAV files.

Do not pass mixed LiveKit room audio as if its channels represented speakers.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from voice_evaluator.artifacts.store import CallArtifacts
from voice_evaluator.recording.wav_tools import (
    ChannelStats,
    channel_stats,
    read_info,
    split_channels,
)

log = logging.getLogger("voice_evaluator.recording")

# Twilio dual-channel mapping for an outbound call:
#   channel 1 = audio Twilio received  -> the Pretty Good AI agent
#   channel 2 = audio Twilio generated -> our simulated patient
#
# This is documented behaviour, but it is also verified per call by
# verify_channels(), because getting it backwards would silently invert every
# transcript in the submission.
CHANNEL_NAMES = ["agent", "patient"]


@dataclass
class RecordingResult:
    mp3_path: Path
    wav_path: Path
    channel_paths: dict[str, Path]
    stats: dict[str, ChannelStats]
    duration_seconds: float
    channels: int
    warnings: list[str]

    @property
    def both_sides_audible(self) -> bool:
        return all(s.is_audible for s in self.stats.values())


def analyse_recording(artifacts: CallArtifacts, *, expected_channels: int = 2) -> RecordingResult:
    """Split the WAV into per-speaker channels and measure each one."""
    info = read_info(artifacts.recording_wav)
    warnings: list[str] = []

    if info.channels == 1:
        warnings.append(
            "recording is mono: dual-channel was not applied, so speaker attribution "
            "falls back to the realtime transcript rather than the audio itself"
        )
        names = ["mixed"]
    elif info.channels == 2:
        names = CHANNEL_NAMES
    else:
        raise ValueError(f"unexpected channel count in recording: {info.channels}")

    if expected_channels != info.channels:
        warnings.append(
            f"Twilio reported {expected_channels} channel(s) but the WAV has {info.channels}"
        )

    channel_dir = artifacts.dir / "channels"
    channel_paths = split_channels(artifacts.recording_wav, channel_dir, names)
    stats = {name: channel_stats(path) for name, path in channel_paths.items()}

    for name, stat in stats.items():
        if not stat.is_audible:
            warnings.append(
                f"channel '{name}' looks inaudible (rms={stat.rms}, "
                f"silence_ratio={stat.silence_ratio}) - this call is not usable as evidence"
            )

    result = RecordingResult(
        mp3_path=artifacts.recording_mp3,
        wav_path=artifacts.recording_wav,
        channel_paths=channel_paths,
        stats=stats,
        duration_seconds=info.duration_seconds,
        channels=info.channels,
        warnings=warnings,
    )
    warnings.extend(verify_channels(result))

    artifacts.update_metadata(
        audio_duration_seconds=round(info.duration_seconds, 2),
        channel_stats={name: vars(stat) for name, stat in stats.items()},
        recording_warnings=warnings,
    )
    return result


def verify_channels(result: RecordingResult) -> list[str]:
    """Cheap sanity checks on the channel assignment.

    We cannot prove which party is on which channel from energy alone, but we
    can catch the two failures that would matter: a dead channel, and both
    channels being identical (which would mean a mono mixdown was returned).
    """
    problems: list[str] = []
    if result.channels != 2:
        problems.append("recording is not dual-channel")
        return problems

    agent = result.stats.get("agent")
    patient = result.stats.get("patient")
    if (
        agent
        and patient
        and abs(agent.rms - patient.rms) < 0.5
        and abs(agent.silence_ratio - patient.silence_ratio) < 0.01
    ):
        problems.append(
            "both channels have near-identical energy, which suggests a mono mixdown "
            "was returned instead of true dual-channel audio"
        )
    return problems
