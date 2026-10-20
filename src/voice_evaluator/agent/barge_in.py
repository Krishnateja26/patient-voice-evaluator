"""One deliberate, authored overlap attempt; timing is verified from audio later."""

import asyncio


class BargeInScheduler:
    def __init__(self, session, behavior, timeline):
        self.session = session
        self.behavior = behavior
        self.timeline = timeline
        self.completed_target_turns = 0
        self.attempted = False
        self.task = None
        self.target_speaking = False

    def on_item(self, event):
        if getattr(event.item, "role", None) == "user":
            self.completed_target_turns += 1

    def on_state(self, event):
        self.target_speaking = event.new_state == "speaking"
        if not self.target_speaking and self.task and not self.attempted:
            self.task.cancel()
        if (
            self.target_speaking
            and not self.attempted
            and self.behavior.interruption_utterance
            and self.completed_target_turns >= self.behavior.interruption_after_turns
            and (self.task is None or self.task.done())
        ):
            self.task = asyncio.create_task(self._attempt())

    async def _attempt(self):
        await asyncio.sleep(self.behavior.interruption_after_seconds)
        if not self.target_speaking or getattr(self.session, "agent_state", None) == "speaking":
            return
        self.attempted = True
        self.timeline.record(
            "patient_barge_in_attempt",
            utterance=self.behavior.interruption_utterance,
            target_turns=self.completed_target_turns,
            audio_verified=False,
        )
        try:
            handle = self.session.say(
                self.behavior.interruption_utterance, allow_interruptions=True
            )
            await handle.wait_for_playout()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 - observable failure, never claim successful barge-in
            self.timeline.record("patient_barge_in_failed", audio_verified=False)

    async def aclose(self):
        if self.task:
            self.task.cancel()
            await asyncio.gather(self.task, return_exceptions=True)
