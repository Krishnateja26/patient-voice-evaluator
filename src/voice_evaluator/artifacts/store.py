"""Per-call artifact directories.

Every call gets one directory containing all of its evidence. The layout is
fixed so that documentation, tests and the submission checklist can all refer to
the same paths:

    artifacts/calls/call-007_unsupported_insurance_probe/
        metadata.json     call ids, scenario, timings, metrics, outcome
        scenario.yaml     the exact scenario as run (calls are reproducible)
        events.jsonl      structured event log from the bridge
        recording.mp3     dual-channel telephone audio (submission artifact)
        recording.wav     dual-channel PCM, used for per-channel transcription
        transcript.json   speaker-attributed, timestamped
        transcript.txt    human-readable
        evaluation.json   deterministic + assertion + judge results
        evaluation.md     human-readable evaluation
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from voice_evaluator.config import get_settings
from voice_evaluator.scenarios.models import Scenario

CALL_DIR_RE = re.compile(r"^(call-(?:[0-9]{3,8}|[a-f0-9]{32}))(?:_([a-z0-9][a-z0-9_-]*))?$")
CALL_ID_RE = re.compile(r"^call-([0-9]{3,8})$")


def calls_root(artifacts_dir: Path | None = None) -> Path:
    root = (artifacts_dir or get_settings().artifacts_dir) / "calls"
    root.mkdir(parents=True, exist_ok=True)
    return root


def existing_call_ids(artifacts_dir: Path | None = None) -> list[str]:
    root = calls_root(artifacts_dir)
    ids = []
    for path in root.iterdir():
        if not path.is_dir():
            continue
        match = CALL_DIR_RE.match(path.name)
        if match:
            ids.append(match.group(1))
    return sorted(ids)


def allocate_call_id(artifacts_dir: Path | None = None) -> str:
    """Next sequential call id, e.g. ``call-011``."""
    highest = 0
    root = calls_root(artifacts_dir)
    for path in root.iterdir():
        if not path.is_dir():
            continue
        match = CALL_ID_RE.match(path.name.split("_", 1)[0])
        if match:
            highest = max(highest, int(match.group(1)))
        metadata = path / "metadata.json"
        if metadata.is_file():
            try:
                label = json.loads(metadata.read_text(encoding="utf-8")).get("call_name", "")
            except (OSError, json.JSONDecodeError):
                continue
            label_match = re.fullmatch(r"Call (\d+)", label)
            if label_match:
                highest = max(highest, int(label_match.group(1)))
    return f"call-{highest + 1:03d}"


def call_dir_name(call_id: str, scenario_id: str | None = None) -> str:
    """Readable artifact folder name, preserving the stable call id prefix."""
    if not scenario_id:
        return call_id
    return f"{call_id}_{_slugify(scenario_id)}"


def resolve_call_dir(call_id: str, artifacts_dir: Path | None = None) -> Path | None:
    """Find the artifact directory for ``call-007`` or ``call-007_<scenario>``."""
    if not CALL_DIR_RE.fullmatch(call_id):
        raise ValueError("Invalid call identifier")
    root = calls_root(artifacts_dir)
    exact = root / call_id
    if exact.is_dir():
        return exact
    matches = sorted(
        path
        for path in root.iterdir()
        if path.is_dir() and path.name.startswith(f"{call_id}_") and CALL_DIR_RE.match(path.name)
    )
    return matches[0] if matches else None


class CallArtifacts:
    """Handle to one call's directory."""

    def __init__(
        self,
        call_id: str,
        artifacts_dir: Path | None = None,
        *,
        scenario_id: str | None = None,
        existing_dir: Path | None = None,
    ) -> None:
        if not CALL_DIR_RE.fullmatch(call_id):
            raise ValueError("Invalid call identifier")
        self.call_id = call_id
        campaign_root = calls_root(artifacts_dir).resolve()
        self.dir = (existing_dir or campaign_root / call_dir_name(call_id, scenario_id)).resolve()
        if not self.dir.is_relative_to(campaign_root):
            raise ValueError("Artifact path escapes the campaign folder")
        self.dir.mkdir(parents=True, exist_ok=True)

    # --- paths -----------------------------------------------------------
    @property
    def metadata_path(self) -> Path:
        return self.dir / "metadata.json"

    @property
    def scenario_path(self) -> Path:
        return self.dir / "scenario.yaml"

    @property
    def events_path(self) -> Path:
        return self.dir / "events.jsonl"

    @property
    def recording_mp3(self) -> Path:
        return self.dir / "recording.mp3"

    @property
    def recording_ogg(self) -> Path:
        return self.dir / "recording.ogg"

    @property
    def recording_path(self) -> Path | None:
        return next(
            (
                f
                for f in (self.recording_mp3, self.recording_ogg)
                if f.is_file() and f.stat().st_size > 0
            ),
            None,
        )

    @property
    def recording_wav(self) -> Path:
        return self.dir / "recording.wav"

    @property
    def transcript_json(self) -> Path:
        return self.dir / "transcript.json"

    @property
    def transcript_txt(self) -> Path:
        return self.dir / "transcript.txt"

    @property
    def evaluation_json(self) -> Path:
        return self.dir / "evaluation.json"

    @property
    def evaluation_md(self) -> Path:
        return self.dir / "evaluation.md"

    # --- io --------------------------------------------------------------
    def write_scenario(self, scenario: Scenario) -> None:
        self.scenario_path.write_text(
            yaml.safe_dump(
                json.loads(scenario.model_dump_json()),
                sort_keys=False,
                allow_unicode=True,
                width=100,
            ),
            encoding="utf-8",
        )

    def read_metadata(self) -> dict[str, Any]:
        if not self.metadata_path.exists():
            return {}
        return json.loads(self.metadata_path.read_text(encoding="utf-8"))

    def write_metadata(self, data: dict[str, Any]) -> None:
        self.metadata_path.write_text(
            json.dumps(_jsonable(data), indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )

    def update_metadata(self, **fields: Any) -> dict[str, Any]:
        data = self.read_metadata()
        data.update(_jsonable(fields))
        data["updated_at"] = datetime.now(UTC).isoformat()
        self.write_metadata(data)
        return data

    def write_json(self, path: Path, data: Any) -> None:
        path.write_text(
            json.dumps(_jsonable(data), indent=2, ensure_ascii=False, default=str) + "\n",
            encoding="utf-8",
        )

    def read_json(self, path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def has_recording(self) -> bool:
        return self.recording_path is not None

    def has_transcript(self) -> bool:
        return self.transcript_json.exists()

    def has_evaluation(self) -> bool:
        return self.evaluation_json.exists()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<CallArtifacts {self.call_id} at {self.dir}>"



def next_display_name(artifacts_dir: Path | None = None) -> str:
    """Return the next human-friendly label after completed calls."""
    highest = 0
    root = calls_root(artifacts_dir)
    for path in root.iterdir():
        meta_path = path / "metadata.json"
        if not meta_path.is_file():
            continue
        try:
            label = json.loads(meta_path.read_text(encoding="utf-8")).get("call_name", "")
        except (OSError, json.JSONDecodeError):
            continue
        match = re.fullmatch(r"Call (\d+)", label)
        if match:
            highest = max(highest, int(match.group(1)))
    return f"Call {highest + 1}"

def load_all_calls(artifacts_dir: Path | None = None) -> list[CallArtifacts]:
    root = calls_root(artifacts_dir)
    calls = []
    for path in sorted(root.iterdir(), key=lambda p: p.name):
        if not path.is_dir():
            continue
        match = CALL_DIR_RE.match(path.name)
        if match:
            calls.append(CallArtifacts(match.group(1), artifacts_dir, existing_dir=path))
    return calls


def _jsonable(value: Any) -> Any:
    """Convert dataclasses, pydantic models, Paths and sets into JSON-safe values."""
    if is_dataclass(value) and not isinstance(value, type):
        return _jsonable(asdict(value))
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_jsonable(v) for v in value]
    if isinstance(value, set | frozenset):
        return sorted(_jsonable(v) for v in value)
    if isinstance(value, Path):
        return str(value)
    return value


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9_-]+", "_", value.lower()).strip("_")
    return slug or "scenario"
