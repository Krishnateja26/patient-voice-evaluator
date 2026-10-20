"""Structured event logging.

Every interesting thing that happens during a call is appended to a JSONL file
inside the call's artifact directory. Post-call analysis reads that file rather
than scraping stdout, which keeps the console readable and the analysis exact.

Secrets never reach this file: only the fields explicitly passed in are written.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("voice_evaluator")


class EventLog:
    """Append-only JSONL event sink for one call.

    Thread-safe and cheap: a call produces a few hundred events at most, so we
    flush on every write to survive a crashed process without losing evidence.
    """

    def __init__(self, path: Path, call_id: str, run_id: str, scenario_id: str) -> None:
        self.path = path
        self.call_id = call_id
        self.run_id = run_id
        self.scenario_id = scenario_id
        self._lock = threading.Lock()
        self._t0 = time.monotonic()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def emit(self, event: str, **fields: Any) -> dict[str, Any]:
        """Write one event. Returns the record for convenience."""
        record = {
            "t": round(time.monotonic() - self._t0, 3),
            "ts": time.time(),
            "run_id": self.run_id,
            "call_id": self.call_id,
            "scenario_id": self.scenario_id,
            "event": event,
            **fields,
        }
        line = json.dumps(record, ensure_ascii=False, default=str)
        with self._lock:
            if self._fh.closed:
                log.debug("dropping event after log close: %s", event)
                return record
            self._fh.write(line + "\n")
            self._fh.flush()
        return record

    def close(self) -> None:
        with self._lock:
            if not self._fh.closed:
                self._fh.close()

    def __enter__(self) -> EventLog:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def read_events(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL event log, skipping any truncated trailing line."""
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            log.warning("skipping malformed event line in %s", path)
    return events
