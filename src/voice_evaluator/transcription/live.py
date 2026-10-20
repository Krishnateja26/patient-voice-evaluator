"""Export call-associated live text without pretending it is offline ASR."""

from voice_evaluator.recording.audio import sha256
from voice_evaluator.transcription.merge import MergedTranscript, Turn, render_text


def export_live_transcript(call):
    items = call.read_json(call.dir / "live_transcript.json") or []
    turns = []
    previous = 0.0
    for item in items:
        text = (item.get("text") or "").strip()
        if not text or item.get("role") not in {"user", "assistant"}:
            continue
        end = max(previous, float(item.get("elapsed_seconds", previous)))
        turns.append(
            Turn(
                index=len(turns),
                speaker="patient" if item["role"] == "assistant" else "agent",
                start=previous,
                end=end,
                text=text,
            )
        )
        previous = end
    transcript = MergedTranscript(turns=turns, timestamps_available=False)
    data = transcript.to_dict()
    data.update(
        recording_sha256=sha256(call.recording_path),
        transcript_source="live_observations",
        timing_source="SDK observation order, not acoustic speech boundaries",
        speaker_attribution_source="LiveKit participant identity / session role",
        requires_audio_review=True,
    )
    call.write_json(call.transcript_json, data)
    display_name = call.read_metadata().get("call_name", call.call_id)
    call.transcript_txt.write_text(
        render_text(
            transcript,
            header=f"{display_name} - LIVE TRANSCRIPT: check every finding against recording; times are observation estimates",
        ),
        encoding="utf-8",
    )
    call.update_metadata(
        transcript_recording_sha256=data["recording_sha256"], transcript_turn_count=len(turns)
    )
    return transcript
