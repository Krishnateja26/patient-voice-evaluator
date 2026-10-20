"""Scenario schema.

A scenario is the complete specification of one test call: who the patient is,
what they want, what they are allowed to reveal and when, what a correct agent
response looks like, and what would count as a failure.

The schema is deliberately opinionated in two places, both driven by the
research in docs/RESEARCH.md:

1. ``information_disclosure`` exists because cooperative simulators that dump
   every fact in the first turn hide most agent failures (arXiv:2605.12894).
   Real patients answer the question they were asked.

2. ``behavior`` carries explicit realism dials because LLM-simulated users
   default to unnatural politeness and over-questioning (arXiv:2601.17087).
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from voice_evaluator.scenarios.control import SimulationControl


class Category(str, Enum):
    CORE = "core"
    TEMPORAL = "temporal"
    MEMORY = "memory"
    AMBIGUITY = "ambiguity"
    BARGE_IN = "barge_in"
    ROBUSTNESS = "robustness"
    SAFETY = "safety"
    GROUNDING = "grounding"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Temperament(str, Enum):
    """Caller disposition. Drives pacing, patience and cooperativeness."""

    CALM = "calm"
    RUSHED = "rushed"
    CONFUSED = "confused"
    ANXIOUS = "anxious"
    CHATTY = "chatty"
    TERSE = "terse"
    IRRITATED = "irritated"
    ELDERLY_DELIBERATE = "elderly_deliberate"


class Patient(BaseModel):
    """The fictional caller. All values must be invented, never real people."""

    name: str
    age: int = Field(ge=1, le=110)
    date_of_birth: str = Field(description="Fictional DOB, e.g. '1979-04-12'.")
    temperament: Temperament = Temperament.CALM
    speech_notes: str = Field(
        default="",
        description="How this person sounds: pace, filler words, accent notes, hesitations.",
    )


class DisclosurePolicy(BaseModel):
    """Controls how readily the patient volunteers information.

    ``on_request`` facts are the important ones: the patient knows them but only
    says them when asked. This is what makes memory and repeated-question bugs
    observable.
    """

    volunteer_upfront: list[str] = Field(
        default_factory=list,
        description="Facts stated unprompted in the opening turn.",
    )
    on_request: list[str] = Field(
        default_factory=list,
        description="Facts given only when the agent asks for them.",
    )
    never_volunteer: list[str] = Field(
        default_factory=list,
        description="Facts withheld unless the agent asks precisely for them.",
    )
    correct_if_misheard: list[str] = Field(
        default_factory=list,
        description="Facts the patient will actively re-state if the agent gets them wrong.",
    )


class Behavior(BaseModel):
    """Realism dials for the simulated caller."""

    politeness: Literal["low", "normal", "high"] = "normal"
    verbosity: Literal["terse", "normal", "talkative"] = "normal"
    patience: Literal["low", "normal", "high"] = "normal"
    cooperativeness: Literal["low", "normal", "high"] = "normal"
    interrupt_agent: bool = Field(
        default=False,
        description="If true the patient deliberately barges in mid-agent-response.",
    )
    interruption_utterance: str = ""
    interruption_after_seconds: float = Field(default=2.2, ge=0, le=10)
    interruption_after_turns: int = Field(default=2, ge=0, le=10)
    self_corrections: list[str] = Field(
        default_factory=list,
        description="Scripted mid-conversation corrections, e.g. 'actually make it Thursday'.",
    )
    hesitations: bool = Field(default=True, description="Allow natural filler and thinking pauses.")


class Assertions(BaseModel):
    """Layer-2 evaluation contract for this scenario."""

    expected_behaviors: list[str] = Field(
        default_factory=list,
        description="Things a correct agent should do. Judged with transcript evidence.",
    )
    forbidden_behaviors: list[str] = Field(
        default_factory=list,
        description="Things that are defects if observed.",
    )
    required_information: list[str] = Field(
        default_factory=list,
        description="Information the agent must collect or provide before ending.",
    )
    failure_signals: list[str] = Field(
        default_factory=list,
        description="Concrete phrases or events that indicate a failure.",
    )
    ground_truth_notes: str = Field(
        default="",
        description="Externally verifiable facts used to judge grounding claims.",
    )


class Scenario(BaseModel):
    """One complete test call specification."""

    id: str = Field(pattern=r"^[a-z0-9_]+$")
    category: Category
    title: str
    difficulty: Difficulty = Difficulty.MEDIUM
    tags: list[str] = Field(default_factory=list)

    objective: str = Field(description="What the patient is trying to achieve, in one sentence.")
    hypothesis: str = Field(
        default="",
        description="The suspected agent weakness this call is designed to expose.",
    )

    patient: Patient
    background: str = Field(default="", description="Situation the patient is calling from.")

    facts_patient_knows: dict[str, str] = Field(default_factory=dict)
    facts_patient_does_not_know: list[str] = Field(default_factory=list)

    opening_line: str = Field(
        description="Roughly what the patient says first. Delivered naturally, not read verbatim.",
    )
    conversation_strategy: list[str] = Field(
        default_factory=list,
        description="Ordered beats the patient steers the conversation through.",
    )
    information_disclosure: DisclosurePolicy = Field(default_factory=DisclosurePolicy)
    behavior: Behavior = Field(default_factory=Behavior)

    target_outcome: str = Field(description="The state that means the call succeeded.")
    end_call_when: list[str] = Field(
        default_factory=list,
        description="Conditions under which the patient should wrap up and hang up.",
    )

    simulation: SimulationControl | None = None

    assertions: Assertions = Field(default_factory=Assertions)

    max_duration_seconds: int = Field(default=180, ge=30, le=420)

    @field_validator("tags")
    @classmethod
    def _lower_tags(cls, v: list[str]) -> list[str]:
        return [t.strip().lower() for t in v if t.strip()]

    @model_validator(mode="after")
    def _require_evaluation_contract(self) -> Scenario:
        """A scenario with no assertions cannot produce a defensible bug finding."""
        a = self.assertions
        if not (a.expected_behaviors or a.forbidden_behaviors):
            raise ValueError(
                f"scenario '{self.id}' must define at least one expected_behavior or "
                f"forbidden_behavior, otherwise its result cannot be evaluated"
            )
        if not self.end_call_when:
            raise ValueError(
                f"scenario '{self.id}' must define end_call_when so the caller knows "
                f"when to hang up; without it calls run to the watchdog timeout"
            )
        return self

    @property
    def slug(self) -> str:
        return f"{self.category.value}/{self.id}"
