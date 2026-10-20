"""Result types shared by the three evaluation layers.

A "finding" is a *bug candidate*, not a bug. Nothing in this package is allowed
to promote a candidate into BUG_REPORT.md on its own: every entry in the final
report carries a human-verified flag that a person sets after listening to the
audio. The reasoning is in docs/RESEARCH.md — LLM judges hallucinate
justifications, so the pipeline is built to make that failure mode visible
rather than to pretend it does not exist.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def rank(self) -> int:
        return {"critical": 0, "high": 1, "medium": 2, "low": 3}[self.value]


class BugCategory(str, Enum):
    SCHEDULING = "scheduling"
    GROUNDING = "grounding"
    HALLUCINATION = "hallucination"
    MEMORY = "memory"
    CONVERSATION = "conversation"
    VOICE_UX = "voice_ux"
    LATENCY = "latency"
    BARGE_IN = "barge_in"
    SAFETY = "safety"
    TOOL_EXECUTION = "tool_execution"
    POLICY = "policy"
    TRANSCRIPTION = "transcription"


class Source(str, Enum):
    DETERMINISTIC = "deterministic"
    ASSERTION = "assertion"
    JUDGE = "judge"


class Evidence(BaseModel):
    """A pointer into the transcript. Quotes are verified against the source."""

    turn_index: int | None = None
    timestamp: str = ""
    speaker: str = ""
    quote: str = ""
    verification_errors: list[str] = Field(default_factory=list)
    quote_verified: bool = Field(
        default=False,
        description="True if this quote was found verbatim in the transcript.",
    )


class Finding(BaseModel):
    """One bug candidate."""

    id: str
    title: str
    severity: Severity
    category: BugCategory
    confidence: Literal["high", "medium", "low"] = "medium"
    source: Source
    expected: str
    actual: str
    why_it_matters: str
    evidence: list[Evidence] = Field(default_factory=list)
    reproduction: str = ""
    adjudication_verdict: Literal["not_run", "supported", "not_supported", "unclear"] = "not_run"
    adjudication_reason: str = ""
    human_verified: bool = Field(
        default=False,
        description="Set to true only after a person checked the audio and transcript.",
    )

    @property
    def has_verified_evidence(self) -> bool:
        return bool(self.evidence) and all(e.quote_verified for e in self.evidence)


class DimensionScore(BaseModel):
    score: int = Field(ge=1, le=5)
    justification: str
    evidence_lines: list[int] = Field(default_factory=list)


class BehaviorVerdict(BaseModel):
    behavior: str
    verdict: Literal["met", "not_met", "unclear"]
    justification: str
    evidence_lines: list[int] = Field(default_factory=list)


class JudgeResult(BaseModel):
    """Structured output contract for the LLM evaluation layer."""

    task_success: Literal["success", "partial", "failure"]
    task_success_justification: str
    dimensions: dict[str, DimensionScore] = Field(default_factory=dict)
    expected_behavior_verdicts: list[BehaviorVerdict] = Field(default_factory=list)
    forbidden_behavior_verdicts: list[BehaviorVerdict] = Field(default_factory=list)
    bug_candidates: list[Finding] = Field(default_factory=list)
    conversation_summary: str = ""
    notes: str = ""


class CallEvaluation(BaseModel):
    """The complete evaluation record written to evaluation.json."""

    call_id: str
    scenario_id: str
    evaluated_at: str
    judge_model: str | None = None
    transcript_sha256: str | None = None

    call_completed: bool = False
    duration_seconds: float = 0.0
    turn_count: int = 0

    deterministic_findings: list[Finding] = Field(default_factory=list)
    assertion_findings: list[Finding] = Field(default_factory=list)
    judge: JudgeResult | None = None

    quality_gate_warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, object] = Field(default_factory=dict)

    @property
    def all_findings(self) -> list[Finding]:
        combined = list(self.deterministic_findings) + list(self.assertion_findings)
        if self.judge:
            combined += list(self.judge.bug_candidates)
        return sorted(combined, key=lambda f: (f.severity.rank, f.category.value))

    def findings_with_evidence(self) -> list[Finding]:
        """Candidates that survive the quote-verification step."""
        return [
            f
            for f in self.all_findings
            if f.source != Source.JUDGE
            or (f.has_verified_evidence and f.adjudication_verdict in {"not_run", "supported"})
        ]
