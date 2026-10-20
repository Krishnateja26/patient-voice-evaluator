"""Scenario schema, suite integrity, and patient prompt construction."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from voice_evaluator.agent.prompt import build_patient_prompt
from voice_evaluator.scenarios.loader import ScenarioError, load_all, load_one, parse_scenario
from voice_evaluator.scenarios.models import Scenario

REPO_ROOT = Path(__file__).resolve().parent.parent
SCENARIOS_DIR = REPO_ROOT / "scenarios"
PROMPTS_DIR = REPO_ROOT / "prompts"


@pytest.fixture(scope="module")
def suite() -> list[Scenario]:
    return load_all(SCENARIOS_DIR)


def test_every_scenario_file_parses(suite: list[Scenario]) -> None:
    assert len(suite) >= 20, "the suite should comfortably exceed the 10-call minimum"


def test_scenario_ids_are_unique(suite: list[Scenario]) -> None:
    ids = [s.id for s in suite]
    assert len(ids) == len(set(ids))


def test_suite_covers_every_category(suite: list[Scenario]) -> None:
    categories = {s.category.value for s in suite}
    expected = {
        "core",
        "temporal",
        "memory",
        "ambiguity",
        "barge_in",
        "robustness",
        "safety",
        "grounding",
    }
    assert expected <= categories


def test_scenario_directory_matches_category(suite: list[Scenario]) -> None:
    """A scenario in scenarios/safety/ must declare category: safety."""
    for path in SCENARIOS_DIR.rglob("*.yaml"):
        scenario = parse_scenario(path)
        assert path.parent.name == scenario.category.value, (
            f"{path.name} lives in {path.parent.name}/ but declares "
            f"category {scenario.category.value}"
        )


def test_every_scenario_has_an_evaluation_contract(suite: list[Scenario]) -> None:
    for scenario in suite:
        assert scenario.assertions.expected_behaviors or scenario.assertions.forbidden_behaviors
        assert scenario.end_call_when
        assert scenario.target_outcome


def test_calls_stay_within_a_sensible_duration(suite: list[Scenario]) -> None:
    """The challenge asks for 1-3 minute conversations."""
    for scenario in suite:
        assert 120 <= scenario.max_duration_seconds <= 240, scenario.id


def test_patient_identities_are_fictional(suite: list[Scenario]) -> None:
    """Every phone number in a scenario must be in the 555-01xx reserved block."""
    for scenario in suite:
        for value in scenario.facts_patient_knows.values():
            if "555" in value:
                assert "555 01" in value or "555-01" in value, (
                    f"{scenario.id} uses a phone number outside the reserved "
                    f"555-01xx fictional range: {value}"
                )


def test_load_one_reports_near_misses() -> None:
    with pytest.raises(ScenarioError) as exc:
        load_one("schedule_new_patient", SCENARIOS_DIR)
    assert "Did you mean" in str(exc.value)


def test_scenario_without_assertions_is_rejected(tmp_path: Path) -> None:
    bad = {
        "id": "broken",
        "category": "core",
        "title": "no assertions",
        "objective": "x",
        "opening_line": "hi",
        "target_outcome": "y",
        "end_call_when": ["done"],
        "patient": {"name": "A", "age": 30, "date_of_birth": "1995-01-01"},
    }
    path = tmp_path / "broken.yaml"
    path.write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(ScenarioError, match="expected_behavior"):
        parse_scenario(path)


def test_scenario_without_end_condition_is_rejected(tmp_path: Path) -> None:
    bad = {
        "id": "broken2",
        "category": "core",
        "title": "no end condition",
        "objective": "x",
        "opening_line": "hi",
        "target_outcome": "y",
        "patient": {"name": "A", "age": 30, "date_of_birth": "1995-01-01"},
        "assertions": {"expected_behaviors": ["does a thing"]},
    }
    path = tmp_path / "broken2.yaml"
    path.write_text(yaml.safe_dump(bad), encoding="utf-8")
    with pytest.raises(ScenarioError, match="end_call_when"):
        parse_scenario(path)


# ------------------------------------------------------------------ prompt


def test_prompt_contains_the_scenario_essentials(suite: list[Scenario]) -> None:
    scenario = load_one("schedule_new_patient_knee", SCENARIOS_DIR)
    prompt = build_patient_prompt(scenario, PROMPTS_DIR)
    assert scenario.patient.name in prompt
    assert scenario.patient.date_of_birth in prompt
    assert scenario.objective in prompt
    assert scenario.opening_line.strip()[:30] in prompt
    assert "end_call" in prompt


def test_prompt_requires_spoken_goodbye_before_end_call() -> None:
    scenario = load_one("hours_location_insurance_questions", SCENARIOS_DIR)
    prompt = build_patient_prompt(scenario, PROMPTS_DIR)

    assert "`end_call` is silent" in prompt
    assert "immediately previous spoken sentence" in prompt
    assert "If you have not just said bye out loud" in prompt


def test_prompt_waits_through_normal_lookup_pauses() -> None:
    scenario = load_one("registered_patient_first_appointment", SCENARIOS_DIR)
    prompt = build_patient_prompt(scenario, PROMPTS_DIR)

    assert 'If the receptionist says "one moment,"' in prompt
    assert "Only check whether the receptionist is still there after at least eight seconds" in prompt
    assert "Never\n  answer your own check-in" in prompt


def test_prompt_never_leaks_that_this_is_a_test(suite: list[Scenario]) -> None:
    """The caller must not be told it is running a scenario or being evaluated.

    The base persona explicitly forbids revealing it; this checks that the
    generated half does not smuggle the framing back in through field labels.
    """
    banned = ["scenario objective", "test case", "evaluation criteria", "hypothesis"]
    for scenario in suite:
        prompt = build_patient_prompt(scenario, PROMPTS_DIR).lower()
        for phrase in banned:
            assert phrase not in prompt, f"{scenario.id} prompt leaks '{phrase}'"


def test_prompt_excludes_the_evaluation_contract(suite: list[Scenario]) -> None:
    """Expected and forbidden behaviours must never reach the caller.

    If the simulated patient knew what the agent is supposed to do, it would
    steer toward that outcome and the test would grade itself.
    """
    for scenario in suite:
        prompt = build_patient_prompt(scenario, PROMPTS_DIR)
        for behavior in scenario.assertions.expected_behaviors:
            assert behavior not in prompt, f"{scenario.id} leaks an expected behaviour"
        for behavior in scenario.assertions.forbidden_behaviors:
            assert behavior not in prompt, f"{scenario.id} leaks a forbidden behaviour"
        for signal in scenario.assertions.failure_signals:
            assert signal not in prompt, f"{scenario.id} leaks a failure signal"


def test_barge_in_scenarios_instruct_interruption() -> None:
    scenario = load_one("interrupt_long_explanation", SCENARIOS_DIR)
    prompt = build_patient_prompt(scenario, PROMPTS_DIR)
    assert "cut in" in prompt.lower()
    assert scenario.behavior.interrupt_agent is True


def test_non_barge_in_scenarios_instruct_patience() -> None:
    scenario = load_one("schedule_new_patient_knee", SCENARIOS_DIR)
    prompt = build_patient_prompt(scenario, PROMPTS_DIR)
    assert "Do not interrupt" in prompt


def test_self_corrections_reach_the_prompt() -> None:
    scenario = load_one("changing_day_preference", SCENARIOS_DIR)
    prompt = build_patient_prompt(scenario, PROMPTS_DIR)
    for correction in scenario.behavior.self_corrections:
        assert correction in prompt
