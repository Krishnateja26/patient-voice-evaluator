"""Opt-in controls: authored facts and triggers, never inferred clinical state."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ControlledFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: str = Field(min_length=1)
    disclosure: Literal["upfront", "on_request", "never"] = "on_request"
    request_phrases: list[str] = Field(default_factory=list)


class PreferenceChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slot: str = Field(min_length=1)
    value: str = Field(min_length=1)
    target_mentions: list[str] = Field(min_length=1)
    utterance: str = Field(min_length=1)
    delivery_marker: str = Field(min_length=1)


class SimulationControl(BaseModel):
    model_config = ConfigDict(extra="forbid")
    goal: str = Field(min_length=1)
    opening: str = Field(min_length=1)
    facts: dict[str, ControlledFact]
    initial_preferences: dict[str, str] = Field(default_factory=dict)
    changes: list[PreferenceChange] = Field(default_factory=list)
    hesitation_probability: float = Field(default=0, ge=0, le=1)

    @model_validator(mode="after")
    def validate_boundaries(self):
        # Authored instructions must not smuggle withheld literal values into the renderer.
        public = " ".join([self.goal, self.opening, *self.initial_preferences.values()]).casefold()
        for key, fact in self.facts.items():
            if fact.disclosure != "upfront" and fact.value.casefold() in public:
                raise ValueError(f"Withheld fact {key} appears in initial renderer context")
            if fact.disclosure == "on_request" and not fact.request_phrases:
                raise ValueError(f"Fact {key} needs explicit request phrases")
        for fact in self.facts.values():
            if any(not phrase.strip() for phrase in fact.request_phrases):
                raise ValueError("Empty disclosure request phrases are not allowed")
        for change in self.changes:
            pending_context = " ".join([change.utterance, change.value, change.slot]).casefold()
            for key, fact in self.facts.items():
                if fact.disclosure != "upfront" and fact.value.casefold() in pending_context:
                    raise ValueError(f"Correction exposes withheld fact {key}")
            if change.slot not in self.initial_preferences:
                raise ValueError("A change must refer to a declared preference")
            if change.delivery_marker.casefold() not in change.utterance.casefold():
                raise ValueError("Delivery marker must occur in the authored correction")
            if any(not phrase.strip() for phrase in change.target_mentions):
                raise ValueError("Empty correction triggers are not allowed")
        return self
