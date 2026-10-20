"""Keep the correct identity answer out of the mismatch caller prompt."""

from pathlib import Path

from voice_evaluator.agent.prompt import build_patient_prompt
from voice_evaluator.scenarios.loader import load_one


def test_wrong_dob_caller_cannot_supply_registered_answer():
    scenario = load_one(
        "dob_mismatch_without_answer_hint", Path(__file__).resolve().parents[1] / "scenarios"
    )
    prompt = build_patient_prompt(scenario)
    assert "1982" in prompt
    assert "1981" not in prompt
    assert "eighty-one" not in prompt.lower()
    assert "1981" in scenario.assertions.ground_truth_notes
