"""Local recording validation, outside the live audio loop."""

import hashlib
import shutil
import wave
from datetime import UTC, datetime
from pathlib import Path

from voice_evaluator.recording.wav_tools import channel_stats


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest_recording(artifacts, source: Path):
    """Decode known mapped stereo audio. File presence alone is never enough."""
    import av

    source = Path(source)
    metadata = artifacts.read_metadata()
    if (
        metadata.get("recording_channel_mapping") != ["patient", "agent"]
        or metadata.get("recording_source") != "local_rtc_subscriber"
    ):
        raise ValueError("Recording needs documented local participant-to-channel provenance")
    if source.suffix.lower() not in {".mp3", ".ogg"}:
        raise ValueError("Accepted submission audio formats are MP3 and OGG")
    destination = (
        artifacts.recording_mp3 if source.suffix.lower() == ".mp3" else artifacts.recording_ogg
    )
    # Changes invalidate old human review even if a later decode fails.
    artifacts.update_metadata(audio_validated=False, call_completed=False, call_review=None)
    channel_dir = artifacts.dir / "channels"
    channel_dir.mkdir(exist_ok=True)
    frames = 0
    with av.open(str(source)) as media:
        if not media.streams.audio:
            raise ValueError("Recording contains no audio stream")
        stream = media.streams.audio[0]
        if stream.codec_context.channels != 2:
            raise ValueError("Expected stereo speaker routing; mono cannot establish both speakers")
        resampler = av.AudioResampler(format="s16p", layout="stereo", rate=16000)
        with (
            wave.open(str(channel_dir / "patient.wav"), "wb") as left,
            wave.open(str(channel_dir / "agent.wav"), "wb") as right,
        ):
            for output in (left, right):
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
            for frame in media.decode(stream):
                for converted in resampler.resample(frame):
                    samples = converted.to_ndarray()
                    left.writeframes(samples[0].tobytes())
                    right.writeframes(samples[1].tobytes())
                    frames += converted.samples
            for converted in resampler.resample(None):
                samples = converted.to_ndarray()
                left.writeframes(samples[0].tobytes())
                right.writeframes(samples[1].tobytes())
                frames += converted.samples
    if frames == 0:
        raise ValueError("Recording has no decoded audio samples")
    stats = {
        speaker: channel_stats(channel_dir / f"{speaker}.wav") for speaker in ("patient", "agent")
    }
    if not all(stat.is_audible for stat in stats.values()):
        raise ValueError(
            "One or both routed channels have insufficient audio; human inspection required"
        )
    # Identical channels indicate a duplicated mix rather than reliable speaker separation.
    if sha256(channel_dir / "patient.wav") == sha256(channel_dir / "agent.wav"):
        raise ValueError("Identical channels cannot prove separate speaker attribution")
    if source.resolve() != destination.resolve():
        shutil.copyfile(source, destination)
    audio_hash = sha256(destination)
    artifacts.update_metadata(
        audio_validated=True,
        audio_duration_seconds=frames / 16000,
        recording_filename=destination.name,
        recording_sha256=audio_hash,
        recording_channels=2,
        channel_sha256={
            speaker: sha256(channel_dir / f"{speaker}.wav") for speaker in ("patient", "agent")
        },
        recording_status="decoded_and_energy_checked_not_human_verified",
        recording_ingested_at=datetime.now(UTC).isoformat(),
    )
    return destination
