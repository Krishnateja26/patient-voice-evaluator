"""Append-only observations. SDK events are not remote PSTN playout proof."""

import json
import math
import statistics
import time
from collections import Counter
from pathlib import Path

LATENCIES = ("end_of_turn_delay", "llm_node_ttft", "tts_node_ttfb", "e2e_latency")


class Timeline:
    def __init__(self, folder: Path):
        self.path = folder / "timeline.jsonl"
        self.start = time.monotonic()
        self.events = []

    def record(self, kind: str, **payload):
        event = {
            "sequence": len(self.events),
            "kind": kind,
            "observed_at": time.time(),
            "elapsed_seconds": time.monotonic() - self.start,
            "payload": payload,
        }
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, default=str, allow_nan=False) + "\n")
        self.events.append(event)

    def summary(self):
        measurements = {key: [] for key in LATENCIES}
        for event in self.events:
            if event["kind"] != "conversation_item_added":
                continue
            for key in LATENCIES:
                value = (event["payload"].get("metrics") or {}).get(key)
                if (
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and math.isfinite(value)
                    and value >= 0
                ):
                    measurements[key].append(float(value))
        result = {}
        for key, values in measurements.items():
            ordered = sorted(values)
            result[key] = {
                "count": len(values),
                "p50_seconds": statistics.median(values) if values else None,
                "p95_seconds": ordered[max(0, math.ceil(len(values) * 0.95) - 1)]
                if values
                else None,
            }
        return {
            "event_counts": dict(Counter(e["kind"] for e in self.events)),
            "sdk_latency": result,
            "timing_source": "LiveKit SDK; remote PSTN first-audible and cancellation times unmeasured",
            "human_verified": False,
        }

    def save_summary(self):
        self.path.with_name("timing_summary.json").write_text(
            json.dumps(self.summary(), indent=2), encoding="utf-8"
        )

    def subscribe(self, session, on_fatal=None):
        for kind in (
            "user_state_changed",
            "agent_state_changed",
            "user_input_transcribed",
            "agent_false_interruption",
            "overlapping_speech",
            "error",
        ):

            def register(name):
                @session.on(name)
                def callback(event):
                    fields = (
                        "created_at",
                        "old_state",
                        "new_state",
                        "is_final",
                        "item_id",
                        "transcript",
                        "resumed",
                        "is_interruption",
                        "agent_ended",
                        "detected_at",
                        "overlap_started_at",
                        "detection_delay",
                        "probability",
                        "source",
                        "recoverable",
                    )
                    payload = {key: getattr(event, key) for key in fields if hasattr(event, key)}
                    if name == "error":
                        error = getattr(event, "error", None)
                        payload["error_type"] = type(error).__name__
                        payload["recoverable"] = getattr(error, "recoverable", False)
                        # Avoid serializing opaque provider/source objects or exception
                        # messages which may contain request credentials.
                        payload.pop("source", None)
                    self.record(name, **payload)
                    if name == "error" and not payload.get("recoverable") and on_fatal:
                        on_fatal()

            register(kind)

        @session.on("speech_created")
        def speech_created(event):
            handle = event.speech_handle
            self.record("speech_created", speech_id=handle.id, source=event.source)

            def completed(speech):
                self.record(
                    "speech_completed",
                    speech_id=speech.id,
                    interrupted=speech.interrupted,
                    delivery_status="interrupted" if speech.interrupted else "sdk_completed",
                    remote_audibility_verified=False,
                )

            handle.add_done_callback(completed)
