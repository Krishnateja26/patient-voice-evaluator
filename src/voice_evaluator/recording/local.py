"""Capture actual room audio to local, identity-separated WAVs and one MP3.

The receiver clock aligns channels approximately; it does not measure remote
PSTN audibility. No cloud recording service or storage account is used.
"""

import asyncio
import time
import wave
from pathlib import Path

import av
import numpy as np
from livekit import rtc

RATE = 16000


class TimedWave:
    def __init__(self, path: Path):
        self.path = path
        self.writer = wave.open(str(path), "wb")  # noqa: SIM115 - closed with the recorder lifetime
        self.writer.setnchannels(1)
        self.writer.setsampwidth(2)
        self.writer.setframerate(RATE)
        self.samples = 0

    def append(self, data: bytes, elapsed: float):
        count = len(data) // 2
        observed = max(0, round(elapsed * RATE) - count)
        # Correct actual gaps, while ignoring normal small network scheduling jitter.
        if observed - self.samples > RATE * 0.15:
            self.pad(observed)
        self.writer.writeframesraw(data)
        self.samples += count

    def pad(self, end):
        remaining = max(0, end - self.samples)
        while remaining:
            size = min(remaining, RATE)
            self.writer.writeframesraw(bytes(size * 2))
            self.samples += size
            remaining -= size

    def close(self):
        self.writer.close()


def encode_stereo(channels: Path, destination: Path):
    with (
        wave.open(str(channels / "patient.wav"), "rb") as left,
        wave.open(str(channels / "agent.wav"), "rb") as right,
        av.open(str(destination), "w") as output,
    ):
        stream = output.add_stream("libmp3lame", rate=RATE)
        stream.layout = "stereo"
        while True:
            a, b = left.readframes(4096), right.readframes(4096)
            if not a and not b:
                break
            count = max(len(a), len(b)) // 2
            data = (
                np.stack(
                    [
                        np.frombuffer(a.ljust(count * 2, b"\0"), dtype="<i2"),
                        np.frombuffer(b.ljust(count * 2, b"\0"), dtype="<i2"),
                    ]
                ).astype(np.float32)
                / 32768
            )
            frame = av.AudioFrame.from_ndarray(data, format="fltp", layout="stereo")
            frame.sample_rate = RATE
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode(None):
            output.mux(packet)


class LocalRecorder:
    def __init__(self, folder: Path, patient_identity: str, on_failure=None):
        self.folder = folder
        self.room = rtc.Room()
        self.identities = {patient_identity: "patient", "assessment-line": "agent"}
        self.channel_dir = folder / "channels"
        self.channel_dir.mkdir(exist_ok=True)
        self.writers = {
            speaker: TimedWave(self.channel_dir / f"{speaker}.wav")
            for speaker in ("patient", "agent")
        }
        self.tasks = []
        self.streams = []
        self.tracks = set()
        self.error = None
        self.on_failure = on_failure
        self.started_at = time.monotonic()
        self.closed = False

        @self.room.on("track_subscribed")
        def subscribed(track, publication, participant):
            if (
                track.kind != rtc.TrackKind.KIND_AUDIO
                or participant.identity not in self.identities
            ):
                return
            speaker = self.identities[participant.identity]
            if speaker in self.tracks:
                self._fail("Multiple audio tracks for one speaker; inspect recording")
                return
            self.tracks.add(speaker)
            stream = rtc.AudioStream(track, sample_rate=RATE, num_channels=1)
            self.streams.append(stream)
            self.tasks.append(asyncio.create_task(self._capture(stream, speaker)))

    def _fail(self, reason):
        self.error = reason
        if self.on_failure:
            self.on_failure()

    async def _capture(self, stream, speaker):
        try:
            async for event in stream:
                self.writers[speaker].append(
                    bytes(event.frame.data), time.monotonic() - self.started_at
                )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - stop the call and retain local partial evidence
            self._fail("Local audio capture failed")

    async def start(self, url, token):
        self.started_at = time.monotonic()
        await self.room.connect(url, token)

    async def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            for stream in self.streams:
                await stream.aclose()
            for task in self.tasks:
                task.cancel()
            await asyncio.gather(*self.tasks, return_exceptions=True)
        finally:
            try:
                await self.room.disconnect()
            finally:
                end = max(w.samples for w in self.writers.values())
                for writer in self.writers.values():
                    writer.pad(end)
                    writer.close()

    def finalize(self):
        if self.error:
            raise ValueError(self.error)
        if self.tracks != {"patient", "agent"} or not all(w.samples for w in self.writers.values()):
            raise ValueError("Both speaker tracks were not captured")
        destination = self.folder / "recording.mp3"
        encode_stereo(self.channel_dir, destination)
        return destination
