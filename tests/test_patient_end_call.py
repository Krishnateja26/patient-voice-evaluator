"""Prevent silent or interrupted simulator hang-ups."""

import asyncio
from types import SimpleNamespace

import pytest

from voice_evaluator.agent.patient import PatientAgent


@pytest.mark.parametrize(
    "role,text,interrupted,ends",
    [
        ("user", "Would you like a text?", False, False),
        ("assistant", "Yes, please.", False, False),
        ("assistant", "Thanks, goodbye.", True, False),
        ("assistant", "Thanks, goodbye.", False, True),
    ],
)
def test_end_call_requires_completed_spoken_goodbye(role, text, interrupted, ends):
    finished = []

    async def wait():
        pass

    context = SimpleNamespace(
        wait_for_playout=wait,
        session=SimpleNamespace(
            history=SimpleNamespace(
                items=[SimpleNamespace(role=role, text_content=text, interrupted=interrupted)]
            )
        ),
    )
    patient = SimpleNamespace(timeline=None, on_end_call=lambda: finished.append(True))
    asyncio.run(PatientAgent.end_call(patient, context))
    assert bool(finished) is ends
