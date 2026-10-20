"""Discovery, parsing and validation of scenario YAML files."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from voice_evaluator.config import get_settings
from voice_evaluator.scenarios.models import Scenario


class ScenarioError(Exception):
    """Raised when a scenario file is missing or invalid."""


def scenario_files(root: Path | None = None) -> list[Path]:
    """Every scenario YAML under *root*, sorted for deterministic ordering."""
    root = root or get_settings().scenarios_dir
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.yaml") if p.is_file())


def parse_scenario(path: Path) -> Scenario:
    """Load and validate a single scenario file."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ScenarioError(f"{path.name}: invalid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ScenarioError(f"{path.name}: expected a mapping at the top level")
    try:
        return Scenario.model_validate(raw)
    except ValidationError as exc:
        raise ScenarioError(f"{path.name}: {exc}") from exc


def load_all(root: Path | None = None) -> list[Scenario]:
    """Load every scenario, raising on the first invalid file or duplicate id."""
    scenarios: list[Scenario] = []
    seen: dict[str, Path] = {}
    for path in scenario_files(root):
        scenario = parse_scenario(path)
        if scenario.id in seen:
            raise ScenarioError(
                f"duplicate scenario id '{scenario.id}' in {path.name} and {seen[scenario.id].name}"
            )
        seen[scenario.id] = path
        scenarios.append(scenario)
    return scenarios


def load_one(scenario_id: str, root: Path | None = None) -> Scenario:
    """Load a scenario by id, with a helpful error listing near matches."""
    scenarios = load_all(root)
    for scenario in scenarios:
        if scenario.id == scenario_id:
            return scenario
    near = [s.id for s in scenarios if scenario_id in s.id or s.id in scenario_id]
    hint = f" Did you mean: {', '.join(near)}?" if near else ""
    raise ScenarioError(f"no scenario with id '{scenario_id}'.{hint}")


def validate_all(root: Path | None = None) -> tuple[list[Scenario], list[str]]:
    """Validate every scenario, collecting errors instead of raising.

    Returns (valid_scenarios, error_messages).
    """
    scenarios: list[Scenario] = []
    errors: list[str] = []
    seen: dict[str, Path] = {}
    for path in scenario_files(root):
        try:
            scenario = parse_scenario(path)
        except ScenarioError as exc:
            errors.append(str(exc))
            continue
        if scenario.id in seen:
            errors.append(
                f"duplicate scenario id '{scenario.id}' in {path.name} and {seen[scenario.id].name}"
            )
            continue
        seen[scenario.id] = path
        scenarios.append(scenario)
    return scenarios, errors
