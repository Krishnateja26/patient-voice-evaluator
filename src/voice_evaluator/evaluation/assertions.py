"""Layer 2: the scenario's own contract.

Layer 1 knows about phone calls in general. This layer knows about *this* call:
the facts the caller supplied, the phrases that would prove a failure, and the
information the agent was supposed to end up with.

Only the mechanically checkable parts of the contract are handled here —
``failure_signals`` and ``required_information``. The natural-language
``expected_behaviors`` and ``forbidden_behaviors`` are ruled on by the judge,
which reports a verdict per item rather than a single opaque score.
"""

from __future__ import annotations

import re

from voice_evaluator.evaluation.schema import (
    BugCategory,
    Evidence,
    Finding,
    Severity,
    Source,
)
from voice_evaluator.scenarios.models import Category, Scenario
from voice_evaluator.transcription.merge import MergedTranscript, format_timestamp

# Which bug category a failed scenario maps onto, so findings are grouped
# usefully in the final report.
CATEGORY_MAP: dict[Category, BugCategory] = {
    Category.CORE: BugCategory.SCHEDULING,
    Category.TEMPORAL: BugCategory.SCHEDULING,
    Category.MEMORY: BugCategory.MEMORY,
    Category.AMBIGUITY: BugCategory.CONVERSATION,
    Category.BARGE_IN: BugCategory.BARGE_IN,
    Category.ROBUSTNESS: BugCategory.CONVERSATION,
    Category.SAFETY: BugCategory.SAFETY,
    Category.GROUNDING: BugCategory.GROUNDING,
}


def run_all(scenario: Scenario, transcript: MergedTranscript, *, call_id: str) -> list[Finding]:
    findings = check_failure_signals(scenario, transcript, call_id)
    findings += check_required_information(scenario, transcript, call_id)
    return findings


def check_failure_signals(
    scenario: Scenario, transcript: MergedTranscript, call_id: str
) -> list[Finding]:
    """Scenario-declared phrases that, if the agent says them, prove a defect."""
    findings: list[Finding] = []
    category = CATEGORY_MAP.get(scenario.category, BugCategory.CONVERSATION)

    for index, signal in enumerate(scenario.assertions.failure_signals):
        pattern = _phrase_pattern(signal)
        for turn in transcript.turns:
            if turn.speaker != "agent" or not pattern.search(turn.text):
                continue
            findings.append(
                Finding(
                    id=f"{call_id}-assert-signal-{index + 1:02d}",
                    title=f"Scenario failure signal observed: {signal}",
                    severity=Severity.HIGH,
                    category=category,
                    confidence="high",
                    source=Source.ASSERTION,
                    expected=(
                        f"Scenario '{scenario.id}' declares this as a failure signal, so a "
                        f"correct agent never produces it."
                    ),
                    actual=(
                        f'The agent said "{turn.text}" at {format_timestamp(turn.start)}, '
                        f"which matches the declared signal."
                    ),
                    why_it_matters=scenario.hypothesis
                    or "This is the specific failure the scenario was written to detect.",
                    evidence=[
                        Evidence(
                            turn_index=turn.index,
                            timestamp=format_timestamp(turn.start),
                            speaker=turn.speaker,
                            quote=turn.text,
                            quote_verified=True,
                        )
                    ],
                    reproduction=f"Run: voice-evaluator call --scenario {scenario.id}",
                )
            )
            break  # one hit per signal

    return findings


def check_required_information(
    scenario: Scenario, transcript: MergedTranscript, call_id: str
) -> list[Finding]:
    """Information the agent had to collect or provide before the call ended.

    Each requirement is a short keyword phrase. This is intentionally a coarse
    check: it can only prove the topic was *never raised*, which is a strong,
    low-false-positive signal. Whether it was handled *correctly* is the judge's
    job.
    """
    if not scenario.assertions.required_information:
        return []

    conversation = " \n ".join(t.text for t in transcript.turns)
    missing = [
        requirement
        for requirement in scenario.assertions.required_information
        if not _phrase_pattern(requirement).search(conversation)
    ]
    if not missing:
        return []

    return [
        Finding(
            id=f"{call_id}-assert-missing-info",
            title="Required information never came up in the call",
            severity=Severity.MEDIUM,
            category=CATEGORY_MAP.get(scenario.category, BugCategory.CONVERSATION),
            confidence="medium",
            source=Source.ASSERTION,
            expected=(
                "Scenario "
                f"'{scenario.id}' requires the call to cover: "
                + "; ".join(scenario.assertions.required_information)
            ),
            actual="Never mentioned by either party: " + "; ".join(missing),
            why_it_matters=(
                "The caller left the call without something the scenario says they needed, "
                "which means the task was not actually completed even if the agent sounded "
                "like it was."
            ),
            evidence=[],
            reproduction=f"Run: voice-evaluator call --scenario {scenario.id}",
        )
    ]


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    """Build a tolerant matcher for a scenario-declared phrase.

    Whitespace is flexible so a phrase written across a YAML line break still
    matches, and matching is case-insensitive. Everything else is literal, which
    keeps scenario authors out of regex debugging.
    """
    escaped = re.escape(phrase.strip())
    flexible = re.sub(r"(?:\\\s)+", r"\\s+", escaped)
    return re.compile(flexible, re.IGNORECASE)
