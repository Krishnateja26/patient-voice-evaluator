"""Interleaving per-channel transcripts into one conversation.

Two mono transcripts with timestamps become a single ordered timeline. Because
each side came from its own audio channel, overlapping segments are genuine
simultaneous speech, which is what an interruption looks like.

**Caveat learned from call-003.** Speech recognisers do not return speech
boundaries; they return a partition of the timeline. On a channel that is mostly
silence - which the caller's channel always is, since they speak for well under
half the call - each segment's ``end`` gets stretched to meet the next segment's
``start``, swallowing the silence in between. On call-003 the caller's segments
ran at 0.91-1.69 seconds *per word* while the agent's ran at 0.31-0.38, and a
seventeen-word sentence was logged as 20.6 seconds long. Every "overlap" that
produced was fabricated by that padding.

So segment ends are clamped against a plausible speaking rate before anything
downstream trusts them, and overlaps derived from ASR timing are treated as
advisory. The authoritative interruption count comes from the bridge's event
log, which observed the audio directly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from voice_evaluator.transcription.transcriber import ChannelTranscript, Segment

# Two segments must overlap by at least this long to count as talking over each
# other rather than ordinary turn-taking jitter at the boundary.
OVERLAP_THRESHOLD_SECONDS = 0.5

# Speaking-rate bound used to clamp inflated segment ends. Ordinary conversational
# speech sits near 0.3 s/word; 0.6 is deliberately generous so that a slow,
# deliberate speaker is never clipped. The slack absorbs a natural pause or two
# inside a single utterance.
MAX_SECONDS_PER_WORD = 0.6
DURATION_SLACK_SECONDS = 0.8


@dataclass
class Turn:
    """One utterance in the merged conversation."""

    index: int
    speaker: str
    start: float
    end: float
    text: str
    confidence: float | None = None
    overlaps_previous: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "speaker": self.speaker,
            "start": round(self.start, 3),
            "end": round(self.end, 3),
            "timestamp": format_timestamp(self.start),
            "text": self.text,
            "confidence": self.confidence,
            "overlaps_previous": self.overlaps_previous,
        }


@dataclass
class MergedTranscript:
    turns: list[Turn] = field(default_factory=list)
    overlap_events: list[dict[str, Any]] = field(default_factory=list)
    models_used: dict[str, str] = field(default_factory=dict)
    timestamps_available: bool = True
    clamped_segments: int = 0
    suppressed_overlaps: list[dict[str, Any]] = field(default_factory=list)
    observed_interruptions: int | None = None

    @property
    def overlap_source(self) -> str:
        if self.observed_interruptions is None:
            return "asr_timing_advisory"
        return "confirmed_by_audio_stream"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamps_available": self.timestamps_available,
            "models_used": self.models_used,
            "turn_count": len(self.turns),
            "overlap_count": len(self.overlap_events),
            "clamped_segments": self.clamped_segments,
            "overlap_source": self.overlap_source,
            "observed_interruptions": self.observed_interruptions,
            "suppressed_overlap_count": len(self.suppressed_overlaps),
            "suppressed_overlaps": self.suppressed_overlaps,
            "overlap_events": self.overlap_events,
            "turns": [t.to_dict() for t in self.turns],
        }


def format_timestamp(seconds: float) -> str:
    """``MM:SS.mmm`` — the format used in bug reports so evidence is locatable."""
    if seconds < 0:
        seconds = 0.0
    minutes = int(seconds // 60)
    remainder = seconds - minutes * 60
    return f"{minutes:02d}:{remainder:06.3f}"


def plausible_end(segment: Segment) -> float:
    """The latest time this segment could plausibly have finished being spoken."""
    words = len(segment.text.split())
    return segment.start + words * MAX_SECONDS_PER_WORD + DURATION_SLACK_SECONDS


def clamp_segment_durations(segments: list[Segment]) -> tuple[list[Segment], int]:
    """Trim segment ends that a human could not have spoken for that long.

    ASR partitions the timeline rather than detecting speech boundaries, so on a
    sparse channel a segment's end runs on to meet the next one. Left alone, that
    padding manufactures overlaps that never happened. Returns the corrected
    segments and how many were clamped.
    """
    clamped = 0
    corrected: list[Segment] = []
    for segment in segments:
        limit = plausible_end(segment)
        if segment.end > limit:
            clamped += 1
            corrected.append(
                Segment(
                    speaker=segment.speaker,
                    start=segment.start,
                    end=limit,
                    text=segment.text,
                    confidence=segment.confidence,
                )
            )
        else:
            corrected.append(segment)
    return corrected, clamped


def merge_channels(channels: list[ChannelTranscript]) -> MergedTranscript:
    """Merge per-channel transcripts into one time-ordered conversation."""
    all_segments: list[Segment] = []
    models_used: dict[str, str] = {}
    timestamps_available = True

    for channel in channels:
        models_used[channel.speaker] = channel.model
        timestamps_available = timestamps_available and channel.had_timestamps
        all_segments.extend(channel.segments)

    all_segments, clamped = clamp_segment_durations(all_segments)
    all_segments.sort(key=lambda s: (s.start, s.speaker))

    turns: list[Turn] = []
    overlaps: list[dict[str, Any]] = []

    for index, segment in enumerate(_coalesce(all_segments)):
        turn = Turn(
            index=index,
            speaker=segment.speaker,
            start=segment.start,
            end=segment.end,
            text=segment.text,
            confidence=segment.confidence,
        )
        if turns:
            event = _overlap_event(turns[-1], segment)
            if event:
                turn.overlaps_previous = True
                overlaps.append(event)
        turns.append(turn)

    return MergedTranscript(
        turns=turns,
        overlap_events=overlaps,
        models_used=models_used,
        timestamps_available=timestamps_available,
        clamped_segments=clamped,
    )


def reconcile_overlaps(
    transcript: MergedTranscript, *, observed_interruptions: int | None
) -> MergedTranscript:
    """Cross-check ASR-derived overlaps against what the bridge actually heard.

    The bridge watched the live audio stream and counted interruptions from
    speech-onset events; the transcript reconstructs them from recogniser
    timestamps on a channel that is mostly silence. When the two disagree the
    bridge wins, because it observed the thing directly.

    On call-003 the bridge recorded zero interruptions while the transcript
    claimed six, one of them 18.9 seconds long. Clamping segment durations
    removed the worst of those, but four survived — enough to fabricate a
    barge-in finding. So when the stream reports no interruptions at all, the
    remaining candidates are moved to ``suppressed_overlaps`` rather than
    deleted, keeping them visible for anyone who wants to check the call.

    Passing ``None`` means no stream observation exists; the candidates then
    stand as advisory.
    """
    transcript.observed_interruptions = observed_interruptions

    if observed_interruptions is None or observed_interruptions > 0:
        return transcript

    if transcript.overlap_events:
        transcript.suppressed_overlaps = transcript.overlap_events
        transcript.overlap_events = []
        for turn in transcript.turns:
            turn.overlaps_previous = False

    return transcript


def _overlap_event(previous: Turn, segment: Segment) -> dict[str, Any] | None:
    """Decide whether two adjacent turns represent genuine simultaneous speech.

    Three guards, each removing a class of ASR artifact seen on real calls:

    * different speakers, obviously;
    * the interrupter must have begun **after** the other party was already
      talking. If both segments start at the same instant that is an alignment
      artifact — recognisers routinely anchor a channel's first segment at 0.0
      regardless of when speech actually begins;
    * the overlap cannot exceed the interrupted turn itself.
    """
    if previous.speaker == segment.speaker:
        return None

    overlap = previous.end - segment.start
    if overlap < OVERLAP_THRESHOLD_SECONDS:
        return None
    if segment.start <= previous.start:
        return None

    previous_duration = previous.end - previous.start
    if previous_duration <= 0 or overlap > previous_duration:
        return None

    return {
        "at": format_timestamp(segment.start),
        "start": round(segment.start, 3),
        "overlap_seconds": round(overlap, 3),
        "overlap_fraction": round(overlap / previous_duration, 3),
        "interrupted_speaker": previous.speaker,
        "interrupting_speaker": segment.speaker,
        "interrupted_text": previous.text,
        "interrupting_text": segment.text,
    }


def _coalesce(segments: list[Segment], gap: float = 0.6) -> list[Segment]:
    """Join consecutive same-speaker segments separated by a short gap.

    Whisper splits on breath pauses, which turns one sentence into three rows
    and makes the transcript hard to read. Merging them back produces turns that
    look like what a person actually said.
    """
    if not segments:
        return []

    merged: list[Segment] = [
        Segment(
            speaker=segments[0].speaker,
            start=segments[0].start,
            end=segments[0].end,
            text=segments[0].text,
            confidence=segments[0].confidence,
        )
    ]

    for segment in segments[1:]:
        last = merged[-1]
        if segment.speaker == last.speaker and segment.start - last.end <= gap:
            last.end = max(last.end, segment.end)
            last.text = f"{last.text} {segment.text}".strip()
            if last.confidence is not None and segment.confidence is not None:
                last.confidence = round(min(last.confidence, segment.confidence), 3)
        else:
            merged.append(
                Segment(
                    speaker=segment.speaker,
                    start=segment.start,
                    end=segment.end,
                    text=segment.text,
                    confidence=segment.confidence,
                )
            )
    return merged


SPEAKER_LABELS = {"agent": "AGENT", "patient": "PATIENT", "mixed": "MIXED"}


def render_text(transcript: MergedTranscript, *, header: str = "") -> str:
    """Render the human-readable transcript.

    Format is deliberately grep-friendly so bug reports can cite
    ``transcript.txt`` at a timestamp and a reviewer can find it instantly.
    """
    lines: list[str] = []
    if header:
        lines.append(header.rstrip())
        lines.append("")

    for turn in transcript.turns:
        label = SPEAKER_LABELS.get(turn.speaker, turn.speaker.upper())
        marker = "  <-- possible overlapping speech" if turn.overlaps_previous else ""
        lines.append(f"[{label} {format_timestamp(turn.start)}]{marker}")
        lines.append(turn.text)
        lines.append("")

    if transcript.overlap_events:
        lines.append("-" * 60)
        lines.append("Overlapping speech:")
        for event in transcript.overlap_events:
            lines.append(
                f"  {event['at']}  {event['interrupting_speaker']} cut across "
                f"{event['interrupted_speaker']} for {event['overlap_seconds']}s"
            )
        if transcript.observed_interruptions:
            lines.append("")
            lines.append(
                f"  Corroborated: the audio stream recorded "
                f"{transcript.observed_interruptions} interruption(s) live."
            )
        lines.append("")

    if transcript.suppressed_overlaps:
        lines.append("-" * 60)
        lines.append(f"{len(transcript.suppressed_overlaps)} apparent overlap(s) were discarded.")
        lines.append("  The live audio stream recorded no interruptions on this call, so these are")
        lines.append("  speech-recogniser timing artifacts rather than real simultaneous speech.")
        lines.append("  Listed here only so the judgement can be checked:")
        for event in transcript.suppressed_overlaps:
            lines.append(
                f"    {event['at']}  apparent {event['interrupting_speaker']} over "
                f"{event['interrupted_speaker']}, {event['overlap_seconds']}s"
            )
        lines.append("")

    if transcript.clamped_segments:
        lines.append(
            f"Note: {transcript.clamped_segments} segment end time(s) were trimmed to a "
            f"plausible speaking rate."
        )
        lines.append("")

    return "\n".join(lines)


def render_for_judge(transcript: MergedTranscript) -> str:
    """Compact transcript for the LLM evaluator, with stable line references."""
    lines = []
    for turn in transcript.turns:
        label = SPEAKER_LABELS.get(turn.speaker, turn.speaker.upper())
        flag = " [OVERLAP]" if turn.overlaps_previous else ""
        lines.append(
            f"L{turn.index:03d} [{format_timestamp(turn.start)}] {label}{flag}: {turn.text}"
        )
    return "\n".join(lines)
