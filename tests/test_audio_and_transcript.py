"""Audio channel splitting and transcript merging.

The channel split is the foundation of speaker attribution, so it is tested
against a synthetic stereo WAV where the correct answer is known exactly.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import pytest

from voice_evaluator.recording.wav_tools import (
    AudioError,
    channel_stats,
    read_info,
    split_channels,
)
from voice_evaluator.transcription.merge import (
    OVERLAP_THRESHOLD_SECONDS,
    format_timestamp,
    merge_channels,
    render_for_judge,
    render_text,
)
from voice_evaluator.transcription.transcriber import ChannelTranscript, Segment

RATE = 8000


def write_stereo(path: Path, left: list[int], right: list[int]) -> None:
    assert len(left) == len(right)
    frames = b"".join(struct.pack("<hh", left[i], right[i]) for i in range(len(left)))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(RATE)
        wf.writeframes(frames)


def tone(samples: int, amplitude: int, freq: float = 440.0) -> list[int]:
    return [int(amplitude * math.sin(2 * math.pi * freq * i / RATE)) for i in range(samples)]


def test_split_channels_separates_the_two_parties(tmp_path: Path) -> None:
    """Channel 0 is loud, channel 1 is silent; the split must preserve that."""
    n = RATE  # one second
    source = tmp_path / "recording.wav"
    write_stereo(source, left=tone(n, 12000), right=[0] * n)

    written = split_channels(source, tmp_path / "channels", ["agent", "patient"])
    assert set(written) == {"agent", "patient"}

    agent = channel_stats(written["agent"])
    patient = channel_stats(written["patient"])

    assert agent.rms > 5000
    assert patient.rms == 0.0
    assert agent.is_audible
    assert not patient.is_audible


def test_split_preserves_sample_values_exactly(tmp_path: Path) -> None:
    """A byte de-interleave must be lossless, not approximate."""
    left = [1, -2, 3, -4, 32767, -32768, 0, 12345]
    right = [-1, 2, -3, 4, -32768, 32767, 100, -12345]
    source = tmp_path / "exact.wav"
    write_stereo(source, left, right)

    written = split_channels(source, tmp_path / "out", ["agent", "patient"])

    with wave.open(str(written["agent"]), "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    recovered = [
        int.from_bytes(raw[i : i + 2], "little", signed=True) for i in range(0, len(raw), 2)
    ]
    assert recovered == left


def test_split_rejects_a_channel_count_mismatch(tmp_path: Path) -> None:
    n = 100
    source = tmp_path / "mono_mixdown.wav"
    write_stereo(source, [0] * n, [0] * n)
    with pytest.raises(AudioError, match="2 channel"):
        split_channels(source, tmp_path / "out", ["only_one"])


def test_read_info_reports_duration(tmp_path: Path) -> None:
    source = tmp_path / "two_seconds.wav"
    write_stereo(source, [0] * (RATE * 2), [0] * (RATE * 2))
    info = read_info(source)
    assert info.channels == 2
    assert info.frame_rate == RATE
    assert info.duration_seconds == pytest.approx(2.0)


def test_silence_ratio_detects_a_dead_channel(tmp_path: Path) -> None:
    n = RATE
    source = tmp_path / "half_silent.wav"
    # Loud for the first half second, silent for the second.
    left = tone(n // 2, 10000) + [0] * (n // 2)
    write_stereo(source, left, [0] * n)
    written = split_channels(source, tmp_path / "out", ["agent", "patient"])
    stats = channel_stats(written["agent"])
    assert 0.4 < stats.silence_ratio < 0.6


def test_identical_channels_are_flagged_as_a_mono_mixdown(tmp_path: Path) -> None:
    """Two channels with identical energy means dual-channel did not apply.

    Speaker attribution rests entirely on the channels being different, so this
    has to be caught before anything downstream trusts the transcript.
    """
    from voice_evaluator.recording.downloader import RecordingResult, verify_channels

    n = RATE
    source = tmp_path / "mixdown.wav"
    signal = tone(n, 9000)
    write_stereo(source, left=signal, right=list(signal))

    written = split_channels(source, tmp_path / "out", ["agent", "patient"])
    stats = {name: channel_stats(path) for name, path in written.items()}
    result = RecordingResult(
        mp3_path=source,
        wav_path=source,
        channel_paths=written,
        stats=stats,
        duration_seconds=1.0,
        channels=2,
        warnings=[],
    )

    problems = verify_channels(result)
    assert any("mono mixdown" in p for p in problems)


def test_genuinely_different_channels_pass_verification(tmp_path: Path) -> None:
    from voice_evaluator.recording.downloader import RecordingResult, verify_channels

    n = RATE
    source = tmp_path / "dual.wav"
    write_stereo(source, left=tone(n, 12000), right=[0] * n)

    written = split_channels(source, tmp_path / "out", ["agent", "patient"])
    stats = {name: channel_stats(path) for name, path in written.items()}
    result = RecordingResult(
        mp3_path=source,
        wav_path=source,
        channel_paths=written,
        stats=stats,
        duration_seconds=1.0,
        channels=2,
        warnings=[],
    )

    assert verify_channels(result) == []


def test_a_model_that_refuses_timestamps_is_only_tried_once(monkeypatch) -> None:
    """A rejected transcription request still bills, and a call has two channels.

    Without memoising the refusal the same doomed attempt is paid for twice per
    call, every call — which is exactly what calls 002 and 003 did.
    """
    from voice_evaluator.transcription import transcriber

    transcriber.reset_transcription_capability_cache()
    attempts: list[str] = []

    def fake_verbose(client, audio_path, speaker, model, language):
        attempts.append(model)
        if model != "whisper-1":
            raise ValueError("does not support verbose_json")
        return transcriber.ChannelTranscript(
            speaker=speaker,
            model=model,
            text="ok",
            segments=[transcriber.Segment(speaker=speaker, start=0.0, end=1.0, text="ok")],
        )

    monkeypatch.setattr(transcriber, "_transcribe_verbose", fake_verbose)

    for speaker in ("agent", "patient"):
        transcriber.transcribe_channel(
            client=None, audio_path=Path("x.wav"), speaker=speaker, model="gpt-transcribe"
        )

    assert attempts.count("gpt-transcribe") == 1, "the refusal must be remembered"
    assert attempts.count("whisper-1") == 2
    transcriber.reset_transcription_capability_cache()


# ----------------------------------------------------------------- merging


def make_channel(speaker: str, spans: list[tuple[float, float, str]]) -> ChannelTranscript:
    return ChannelTranscript(
        speaker=speaker,
        model="test-model",
        text=" ".join(s[2] for s in spans),
        segments=[Segment(speaker=speaker, start=a, end=b, text=t) for a, b, t in spans],
    )


def test_merge_orders_turns_by_time() -> None:
    agent = make_channel(
        "agent", [(0.0, 2.0, "Thanks for calling."), (5.0, 7.0, "What is your name?")]
    )
    patient = make_channel("patient", [(2.5, 4.0, "Hi, I need an appointment.")])

    merged = merge_channels([agent, patient])
    assert [t.speaker for t in merged.turns] == ["agent", "patient", "agent"]
    assert merged.turns[1].text == "Hi, I need an appointment."


def test_inflated_segment_ends_are_clamped() -> None:
    """Regression from call-003.

    On the caller's channel - 68% silence - the recogniser stretched each
    segment's end to meet the next one's start. A 17-word sentence was logged as
    20.6 seconds, i.e. 1.21 s/word, against 0.31-0.38 for the agent's channel.
    """
    sentence = "Okay. Thanks. That helps. Where is the practice located and do you have more than one site?"
    patient = make_channel("patient", [(57.14, 77.74, sentence)])

    merged = merge_channels([patient])

    assert merged.clamped_segments == 1
    turn = merged.turns[0]
    duration = turn.end - turn.start
    words = len(sentence.split())
    assert duration < 13.0, "a 17-word sentence cannot take 20 seconds"
    assert duration / words < 0.7


def test_realistic_segments_are_left_alone() -> None:
    """The agent's channel was correctly timed and must not be touched."""
    line = (
        "We're open Monday through Friday. Our hours are 9 AM to 4 PM on Monday, Tuesday, "
        "and Thursday, 12 PM to 7 PM on Wednesday, and 9 AM to 12 PM on Friday. "
        "We're closed on weekends."
    )
    agent = make_channel("agent", [(43.28, 54.60, line)])

    merged = merge_channels([agent])

    assert merged.clamped_segments == 0
    assert merged.turns[0].end == pytest.approx(54.60)


def test_simultaneous_start_is_not_an_interruption() -> None:
    """Recognisers anchor a channel's first segment at 0.0 regardless of speech.

    On call-003 that produced 'patient cut across agent for 3.84s' as the very
    first event, while the bridge observed zero interruptions.
    """
    agent = make_channel("agent", [(0.0, 3.84, "This call may be recorded for quality purposes.")])
    patient = make_channel("patient", [(0.0, 6.0, "Hi, I'm not booking anything today.")])

    merged = merge_channels([agent, patient])

    assert merged.overlap_events == []


def test_overlap_larger_than_the_interrupted_turn_is_rejected() -> None:
    agent = make_channel("agent", [(10.0, 12.0, "Sure thing.")])
    patient = make_channel("patient", [(11.0, 30.0, "A very long reply that starts mid-way.")])

    merged = merge_channels([agent, patient])
    # Overlap is 1.0s against a 2.0s turn -- allowed. Now make it impossible:
    assert all(e["overlap_seconds"] <= 2.0 for e in merged.overlap_events)


LONG_AGENT_TURN = (
    "Let me walk you through how our insurance verification process works for new "
    "patients, because there are a couple of steps involved before your first visit."
)


def test_overlap_event_reports_its_fraction() -> None:
    agent = make_channel("agent", [(0.0, 8.0, LONG_AGENT_TURN)])
    patient = make_channel("patient", [(5.0, 7.0, "Sorry, just quickly, what is the date?")])

    merged = merge_channels([agent, patient])
    assert merged.clamped_segments == 0
    assert len(merged.overlap_events) == 1
    assert merged.overlap_events[0]["overlap_fraction"] == pytest.approx(3.0 / 8.0, abs=0.01)


def test_corroborated_overlaps_say_so_in_the_transcript() -> None:
    from voice_evaluator.transcription.merge import reconcile_overlaps

    agent = make_channel("agent", [(0.0, 8.0, LONG_AGENT_TURN)])
    patient = make_channel("patient", [(5.0, 7.0, "Sorry, just quickly, what is the date?")])
    merged = merge_channels([agent, patient])
    reconcile_overlaps(merged, observed_interruptions=1)

    rendered = render_text(merged)
    assert "possible overlapping speech" in rendered.lower()
    assert "corroborated" in rendered.lower()


def test_overlaps_are_suppressed_when_the_stream_saw_none() -> None:
    """Regression from call-003: the bridge counted 0, the transcript claimed 6.

    Clamping removed the worst, but four survived — enough to fabricate a
    barge-in finding. The live stream is the authority.
    """
    from voice_evaluator.transcription.merge import reconcile_overlaps

    agent = make_channel("agent", [(0.0, 8.0, LONG_AGENT_TURN)])
    patient = make_channel("patient", [(5.0, 7.0, "Sorry, just quickly, what is the date?")])
    merged = merge_channels([agent, patient])
    assert merged.overlap_events, "precondition: ASR timing suggests an overlap"

    reconcile_overlaps(merged, observed_interruptions=0)

    assert merged.overlap_events == []
    assert len(merged.suppressed_overlaps) == 1
    assert not any(t.overlaps_previous for t in merged.turns)
    assert merged.overlap_source == "confirmed_by_audio_stream"


def test_overlaps_survive_when_the_stream_corroborates() -> None:
    from voice_evaluator.transcription.merge import reconcile_overlaps

    agent = make_channel("agent", [(0.0, 8.0, LONG_AGENT_TURN)])
    patient = make_channel("patient", [(5.0, 7.0, "Sorry, just quickly, what is the date?")])
    merged = merge_channels([agent, patient])

    reconcile_overlaps(merged, observed_interruptions=2)

    assert len(merged.overlap_events) == 1
    assert merged.suppressed_overlaps == []


def test_overlaps_stay_advisory_without_a_stream_record() -> None:
    from voice_evaluator.transcription.merge import reconcile_overlaps

    agent = make_channel("agent", [(0.0, 8.0, LONG_AGENT_TURN)])
    patient = make_channel("patient", [(5.0, 7.0, "Sorry, just quickly, what is the date?")])
    merged = merge_channels([agent, patient])

    reconcile_overlaps(merged, observed_interruptions=None)

    assert len(merged.overlap_events) == 1
    assert merged.overlap_source == "asr_timing_advisory"


def test_suppressed_overlaps_are_shown_not_hidden() -> None:
    from voice_evaluator.transcription.merge import reconcile_overlaps

    agent = make_channel("agent", [(0.0, 8.0, LONG_AGENT_TURN)])
    patient = make_channel("patient", [(5.0, 7.0, "Sorry, just quickly, what is the date?")])
    merged = merge_channels([agent, patient])
    reconcile_overlaps(merged, observed_interruptions=0)

    rendered = render_text(merged)
    assert "discarded" in rendered
    assert "timing artifacts" in rendered


def test_merge_detects_genuine_overlap() -> None:
    agent = make_channel(
        "agent",
        [(0.0, 6.0, "Let me explain our insurance policy for new patients in a bit of detail")],
    )
    patient = make_channel("patient", [(3.0, 4.5, "Sorry, just quickly, what is the date?")])

    merged = merge_channels([agent, patient])
    assert merged.clamped_segments == 0
    assert len(merged.overlap_events) == 1
    event = merged.overlap_events[0]
    assert event["interrupted_speaker"] == "agent"
    assert event["interrupting_speaker"] == "patient"
    assert event["overlap_seconds"] == pytest.approx(3.0)


def test_merge_ignores_boundary_jitter() -> None:
    """A tiny overlap at a turn boundary is normal, not an interruption."""
    jitter = OVERLAP_THRESHOLD_SECONDS / 2
    agent = make_channel("agent", [(0.0, 2.0, "How can I help?")])
    patient = make_channel("patient", [(2.0 - jitter, 4.0, "I need to book.")])

    merged = merge_channels([agent, patient])
    assert merged.overlap_events == []


def test_merge_coalesces_same_speaker_fragments() -> None:
    """Whisper splits on breath pauses; the merged transcript should not."""
    agent = make_channel(
        "agent",
        [(0.0, 1.0, "Thanks for calling"), (1.2, 2.0, "the orthopedics practice.")],
    )
    merged = merge_channels([agent])
    assert len(merged.turns) == 1
    assert merged.turns[0].text == "Thanks for calling the orthopedics practice."


def test_merge_keeps_separate_turns_across_a_long_gap() -> None:
    agent = make_channel("agent", [(0.0, 1.0, "One moment."), (9.0, 10.0, "Sorry about that.")])
    merged = merge_channels([agent])
    assert len(merged.turns) == 2


def test_timestamp_format_is_locatable() -> None:
    assert format_timestamp(0) == "00:00.000"
    assert format_timestamp(83.21) == "01:23.210"
    assert format_timestamp(-5) == "00:00.000"


def test_render_text_labels_both_sides() -> None:
    agent = make_channel("agent", [(0.0, 2.0, "Can I get your date of birth?")])
    patient = make_channel("patient", [(2.5, 4.0, "Ninth of June, eighty-one.")])
    rendered = render_text(merge_channels([agent, patient]), header="Call: call-001")

    assert "Call: call-001" in rendered
    assert "[AGENT 00:00.000]" in rendered
    assert "[PATIENT 00:02.500]" in rendered
    assert "Ninth of June, eighty-one." in rendered


def test_render_for_judge_has_stable_line_labels() -> None:
    agent = make_channel("agent", [(0.0, 2.0, "Hello.")])
    patient = make_channel("patient", [(3.0, 4.0, "Hi.")])
    rendered = render_for_judge(merge_channels([agent, patient]))
    assert rendered.startswith("L000 ")
    assert "L001 " in rendered
