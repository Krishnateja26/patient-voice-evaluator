"""Versioned patient state and conservative literal disclosure checks.

These checks are not a general semantic entailment verifier. Unknown paraphrases
need human review. LLM output never changes the hidden scenario values.
"""

import json
import random
import re
from dataclasses import asdict, dataclass
from typing import Literal

from voice_evaluator.scenarios.control import SimulationControl


def contains(text, phrase):
    return (
        re.search(r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)", text.casefold())
        is not None
    )


@dataclass(frozen=True)
class StateEvent:
    version: int
    turn: int
    operation: Literal["SET", "CORRECT", "DISCLOSE"]
    key: str
    value: str
    source: str


class PatientState:
    def __init__(self, control: SimulationControl, seed: int):
        self.control = control
        self.seed = seed
        self.rng = random.Random(seed)
        self.turn = 0
        self.preferences = dict(control.initial_preferences)
        self.available = {
            key for key, fact in control.facts.items() if fact.disclosure == "upfront"
        }
        self.disclosed = set()
        self.events = []
        self.behavior_events = []
        self.change_index = 0
        self.pending = None
        for key, value in self.preferences.items():
            self._event("SET", key, value, "scenario")

    def _event(self, op, key, value, source):
        self.events.append(StateEvent(len(self.events) + 1, self.turn, op, key, value, source))

    def target_turn(self, text):
        self.turn += 1
        request = "?" in text or text.casefold().strip().startswith(
            ("what", "which", "can ", "could ", "would ", "please ", "tell me", "may i", "give me")
        )
        for key, fact in self.control.facts.items():
            # Phrase matching is deliberately narrow: scenario authors must define request cues.
            if (
                request
                and fact.disclosure == "on_request"
                and any(contains(text, p) for p in fact.request_phrases)
            ):
                self.available.add(key)
        if self.pending is None and self.change_index < len(self.control.changes):
            change = self.control.changes[self.change_index]
            if any(contains(text, p) for p in change.target_mentions):
                self.pending = change
        hesitation = self.rng.random() < self.control.hesitation_probability
        self.behavior_events.append({"turn": self.turn, "hesitate": hesitation})
        return hesitation

    def renderer_context(self):
        data = {
            "goal": self.control.goal,
            "opening": self.control.opening if not self.turn else None,
            "allowed_facts": {key: self.control.facts[key].value for key in sorted(self.available)},
            "current_preferences": dict(self.preferences),
            "pending_correction": self.pending.utterance if self.pending else None,
            "behavior": self.behavior_events[-1] if self.behavior_events else {"hesitate": False},
        }
        return json.dumps(data, ensure_ascii=False, sort_keys=True)

    def verify_literal_output(self, text):
        violations = []
        for key, fact in self.control.facts.items():
            if key not in self.available and contains(text, fact.value):
                violations.append("withheld_fact:" + key)
        # A pending correction intentionally supersedes the current value, but must not
        # introduce an undeclared value. Paraphrased contradictions need semantic review.
        for key, current in self.preferences.items():
            allowed = self.pending.value if self.pending and self.pending.slot == key else current
            values = {c.value for c in self.control.changes if c.slot == key}
            values.add(self.control.initial_preferences[key])
            for stale in values - {allowed}:
                if contains(text, stale) and not contains(text, allowed):
                    violations.append("stale_preference:" + key)
        return violations

    def observe_patient_item(self, text, interrupted):
        # An interrupted item is not enough evidence that the listener heard a correction.
        if interrupted:
            return
        for key in sorted(self.available - self.disclosed):
            if contains(text, self.control.facts[key].value):
                self.disclosed.add(key)
                self._event("DISCLOSE", key, self.control.facts[key].value, "sdk_completed_item")
        if self.pending and contains(text, self.pending.delivery_marker):
            change = self.pending
            self.preferences[change.slot] = change.value
            self._event("CORRECT", change.slot, change.value, "sdk_completed_item")
            self.change_index += 1
            self.pending = None

    def snapshot(self):
        return {
            "seed": self.seed,
            "turn": self.turn,
            "preferences": self.preferences,
            "available_fact_ids": sorted(self.available),
            "disclosed_fact_ids": sorted(self.disclosed),
            "events": [asdict(e) for e in self.events],
            "behavior_events": self.behavior_events,
            "agenda_position": self.change_index,
            "pending_correction": self.pending.model_dump() if self.pending else None,
            "delivery_source": "SDK completed conversation item; remote hearing requires audio review",
        }
