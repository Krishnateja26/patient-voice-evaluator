"""Patient adapter: legacy prompt compatibility and opt-in controlled state."""

import re

from livekit.agents import Agent, RunContext, StopResponse, function_tool

from voice_evaluator.agent.prompt import build_patient_prompt
from voice_evaluator.agent.state import PatientState

CONTROLLED_PERSONA = """You are a fictional patient speaking to a medical receptionist on the phone.
You are the caller, not the receptionist. Speak naturally, one or two short sentences.
Use ONLY the allowed facts and preferences in the JSON below. Answer the question asked.
Never invent identifiers, medications, doses, appointment availability, or confirmations.
If an answer is unavailable, ask them to repeat or say you do not know.
A pending correction is your next conversational intention; state it naturally.
Otherwise pursue the goal using the current preferences. Past preferences are superseded.
Hesitation is an optional short filler, not a mandated duration. Do not read JSON labels.
If the receptionist finishes the conversation, say a natural goodbye before end_call.
Do not invent a new topic to prolong a finished call.
"""


class PatientAgent(Agent):
    def __init__(self, scenario, finish, *, seed=42, timeline=None, on_end_call=None):
        self.state = PatientState(scenario.simulation, seed) if scenario.simulation else None
        self.timeline = timeline
        self.rejected = []
        self.on_end_call = on_end_call
        super().__init__(instructions=self.render(scenario))
        self.finish = finish

    def render(self, scenario=None):
        if self.state:
            return CONTROLLED_PERSONA + "\n" + self.state.renderer_context()
        return build_patient_prompt(scenario)

    async def on_user_turn_completed(self, turn_ctx, new_message):
        if not self.state:
            return
        self.state.target_turn(new_message.text_content or "")
        # A rejected generated sentence must not become apparent shared history.
        turn_ctx.items[:] = [
            item
            for item in turn_ctx.items
            if not (
                getattr(item, "role", None) == "assistant"
                and getattr(item, "text_content", None) in self.rejected
            )
        ]
        await self.update_instructions(self.render())
        if self.timeline:
            self.timeline.record("patient_state_updated", **self.state.snapshot())

    async def tts_node(self, text, model_settings):
        if not self.state:
            async for frame in Agent.default.tts_node(self, text, model_settings):
                yield frame
            return
        # Deliberate tradeoff in controlled mode: verify the full utterance BEFORE
        # synthesis, so a split hidden value cannot leak across model chunks.
        parts = []
        async for part in text:
            parts.append(part)
        candidate = "".join(parts)
        violations = self.state.verify_literal_output(candidate)
        if violations:
            self.rejected.append(candidate)
            if self.timeline:
                self.timeline.record("patient_output_rejected", violation_codes=violations)
            raise StopResponse()

        async def approved():
            yield candidate

        async for frame in Agent.default.tts_node(self, approved(), model_settings):
            yield frame

    @function_tool()
    async def end_call(self, context: RunContext):
        """End silently after your immediately previous spoken sentence says goodbye out loud."""
        await context.wait_for_playout()
        messages = [
            item
            for item in context.session.history.items
            if getattr(item, "role", None) in {"assistant", "user"}
            and getattr(item, "text_content", None)
        ]
        last = messages[-1] if messages else None
        if (
            last is None
            or last.role != "assistant"
            or getattr(last, "interrupted", False)
            or not re.search(
                r"\b(goodbye|bye|have a (?:good|great|nice) day)\b", last.text_content, re.I
            )
        ):
            if self.timeline:
                self.timeline.record("premature_end_call_blocked")
            return "Call remains connected. Answer any pending receptionist question, then say a brief goodbye out loud before calling end_call again. Do not add a new topic."
        if self.on_end_call:
            self.on_end_call()
        else:
            self.finish.set()
        return "Call ending."
