"""Evaluation layers 1 and 2, plus the judge's evidence verification.

Each deterministic check is driven by a purpose-built transcript so that a
failure points at exactly one rule.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from voice_evaluator.evaluation import assertions, deterministic
from voice_evaluator.evaluation.judge import _verify_quote
from voice_evaluator.evaluation.schema import (
    BugCategory,
    CallEvaluation,
    Evidence,
    Finding,
    Severity,
    Source,
)
from voice_evaluator.scenarios.loader import load_one
from voice_evaluator.transcription.merge import merge_channels
from voice_evaluator.transcription.transcriber import ChannelTranscript, Segment

SCENARIOS_DIR = Path(__file__).resolve().parent.parent / "scenarios"


def transcript(*spans: tuple[str, float, float, str]):
    """Build a merged transcript from (speaker, start, end, text) tuples."""
    by_speaker: dict[str, list[Segment]] = {}
    for speaker, start, end, text in spans:
        by_speaker.setdefault(speaker, []).append(
            Segment(speaker=speaker, start=start, end=end, text=text)
        )
    channels = [
        ChannelTranscript(speaker=speaker, model="test", text="", segments=segments)
        for speaker, segments in by_speaker.items()
    ]
    return merge_channels(channels)


def titles(findings: list[Finding]) -> str:
    return " | ".join(f.title for f in findings)


# ---------------------------------------------------------------- layer 1


def test_repeated_field_request_is_flagged() -> None:
    merged = transcript(
        ("agent", 0, 3, "Can I take your date of birth please?"),
        ("patient", 4, 6, "Ninth of June, nineteen eighty-one."),
        ("agent", 7, 9, "Thank you. And what is your date of birth?"),
    )
    findings = deterministic.check_repeated_field_requests(merged, "call-001")
    assert len(findings) == 1
    assert findings[0].category is BugCategory.MEMORY
    assert findings[0].severity is Severity.HIGH
    assert len(findings[0].evidence) == 2
    assert all(e.quote_verified for e in findings[0].evidence)


def test_answering_about_a_field_twice_is_not_a_repeated_request() -> None:
    """Regression from call-003.

    The agent answered two insurance questions and the check reported it as
    having *asked* for the caller's insurance twice. Both turns are answers.
    The quotes below are verbatim from artifacts/calls/call-003_hours_location_insurance_questions/transcript.txt.
    """
    merged = transcript(
        ("patient", 0, 5, "Do you accept Aetna insurance? It's through my employer."),
        (
            "agent",
            6,
            14,
            "Yes, Pivot Point Orthopedics accepts most insurance plans, including Aetna. "
            "If you decide to schedule, we can confirm your coverage and update your "
            "insurance details when you book.",
        ),
        ("patient", 15, 22, "When you say you accept Aetna, does that include all Aetna plans?"),
        (
            "agent",
            23,
            32,
            "We accept most Aetna plans, but coverage can vary depending on your specific "
            "plan. If you want to be sure, you can share your plan details when you're "
            "ready, and we'll confirm your coverage for you.",
        ),
    )
    assert deterministic.check_repeated_field_requests(merged, "call-003") == []


def test_offering_to_reconfirm_is_not_a_second_request() -> None:
    """Regression from call-005.

    After a failed record lookup the agent offered a menu of recovery options.
    That one turn produced two HIGH findings — "asked for date of birth twice"
    and "asked for name twice" — and both were wrong. Quotes are verbatim from
    artifacts/calls/call-005_weekend_appointment_request/transcript.txt.
    """
    merged = transcript(
        ("agent", 0, 4, "Please provide your date of birth, Tom."),
        ("patient", 5, 8, "September 14th, 1973."),
        (
            "agent",
            9,
            14,
            "Just to confirm, could you please spell your first and last name for me?",
        ),
        ("patient", 15, 19, "Sure. Tom is T-O-N, and Whitaker is W-H-I-T-A-K-E-R."),
        (
            "agent",
            20,
            32,
            "Would you like me to look up your record using your phone number? If so, "
            "please tell me the number you have on file with us. If you're not sure, I "
            "can confirm your name and date of birth again. Which would you prefer?",
        ),
    )
    assert deterministic.check_repeated_field_requests(merged, "call-005") == []


@pytest.mark.parametrize(
    "text",
    [
        "If you're not sure, I can confirm your name and date of birth again.",
        "I can take your date of birth again if that helps.",
        "Would you like me to confirm your date of birth?",
        "If not, could you please spell your date of birth for me?",
    ],
)
def test_offers_are_not_treated_as_requests(text: str) -> None:
    assert not deterministic.requests_field(text, deterministic.FIELD_PATTERNS["date_of_birth"])


@pytest.mark.parametrize(
    ("text", "field"),
    [
        ("I just need your first and last name.", "full_name"),
        ("I'll need your date of birth.", "date_of_birth"),
        ("Please provide your date of birth, Tom.", "date_of_birth"),
        ("Just to confirm, could you please spell your first and last name for me?", "full_name"),
        ("What is your date of birth?", "date_of_birth"),
    ],
)
def test_real_identity_requests_are_recognised(text: str, field: str) -> None:
    """Verbatim phrasings observed on calls 002 and 005.

    A miss here is worse than a false positive: the identity check would see no
    request at all and fire its `critical` unverified-action finding on a call
    that did verify.
    """
    assert deterministic.requests_field(text, deterministic.FIELD_PATTERNS[field])


def test_identity_check_passes_when_the_agent_did_ask() -> None:
    """call-002's phrasing must not trigger the critical unverified-action finding."""
    merged = transcript(
        (
            "agent",
            0,
            8,
            "To get started, would you like to create a demo patient profile? "
            "I just need your first and last name.",
        ),
        ("patient", 9, 12, "It's Daniel Okafor."),
        ("agent", 13, 18, "Thanks. I've booked you for Friday at 9.45 a.m."),
    )
    assert deterministic.check_confirmation_without_identity(merged, "call-002") == []


def test_a_request_buried_among_offers_still_counts() -> None:
    """An offer elsewhere in the turn must not mask a genuine request."""
    text = (
        "I can look that up for you. What is your date of birth? "
        "Would you like me to check availability afterwards?"
    )
    assert deterministic.requests_field(text, deterministic.FIELD_PATTERNS["date_of_birth"])


def test_genuine_repeated_request_still_fires_after_the_fix() -> None:
    merged = transcript(
        ("agent", 0, 3, "Could I get your insurance carrier?"),
        ("patient", 4, 6, "Aetna, through my employer."),
        ("agent", 7, 10, "Thanks. And what is your insurance carrier?"),
    )
    findings = deterministic.check_repeated_field_requests(merged, "call-x")
    assert len(findings) == 1
    assert findings[0].category is BugCategory.MEMORY


@pytest.mark.parametrize(
    "text",
    [
        "Can I take your date of birth?",
        "And what is your name?",
        "Could you confirm your phone number",
        "I'll need your insurance carrier",
        "May I have your date of birth please",
    ],
)
def test_requests_are_recognised(text: str) -> None:
    assert deterministic.is_information_request(text)


@pytest.mark.parametrize(
    "text",
    [
        "We accept most insurance plans, including Aetna.",
        "Your appointment is on Thursday at ten.",
        "Thanks, Mr Okafor, I have that on file.",
        "We're open Monday through Friday.",
    ],
)
def test_statements_are_not_requests(text: str) -> None:
    assert not deterministic.is_information_request(text)


def test_identity_check_needs_a_request_not_a_mention() -> None:
    """Saying the caller's name is not the same as verifying who they are."""
    merged = transcript(
        ("patient", 0, 3, "Hi, it's about my knee."),
        ("agent", 4, 7, "Of course, Mr Okafor, happy to help with your name on file."),
        ("agent", 8, 12, "I've scheduled you for Thursday at ten."),
    )
    findings = deterministic.check_confirmation_without_identity(merged, "call-y")
    assert len(findings) == 1
    assert findings[0].severity is Severity.CRITICAL


def test_repeated_request_ignored_when_caller_never_answered() -> None:
    """An agent repeating itself after silence is not a memory failure."""
    merged = transcript(
        ("agent", 0, 3, "Can I take your date of birth please?"),
        ("agent", 7, 9, "Sorry, could I take your date of birth?"),
    )
    assert deterministic.check_repeated_field_requests(merged, "call-001") == []


def test_caller_complaint_about_repeating_is_flagged() -> None:
    merged = transcript(
        ("agent", 0, 2, "And your name?"),
        ("patient", 3, 5, "I already told you, it's Aisha Rahman."),
    )
    findings = deterministic.check_caller_repeat_complaints(merged, "call-002")
    assert len(findings) == 1
    assert findings[0].category is BugCategory.MEMORY


def test_confirmation_without_identity_is_critical() -> None:
    merged = transcript(
        ("patient", 0, 3, "Can I come in Thursday at ten?"),
        ("agent", 4, 7, "Absolutely, I've scheduled you for Thursday at ten."),
    )
    findings = deterministic.check_confirmation_without_identity(merged, "call-003")
    assert len(findings) == 1
    assert findings[0].severity is Severity.CRITICAL
    assert findings[0].category is BugCategory.SAFETY


def test_confirmation_after_identity_check_is_clean() -> None:
    merged = transcript(
        ("agent", 0, 3, "Could I take your full name and date of birth?"),
        ("patient", 4, 7, "Daniel Okafor, ninth of June eighty-one."),
        ("agent", 8, 11, "Thank you. I've scheduled you for Thursday at ten."),
    )
    assert deterministic.check_confirmation_without_identity(merged, "call-004") == []


def test_agent_guessing_a_name_from_caller_id_is_flagged() -> None:
    """Verbatim from call-005 and call-008, where it was said to two different callers."""
    merged = transcript(
        ("patient", 0, 4, "Hi, I need to sort out an appointment."),
        (
            "agent",
            5,
            10,
            "I see you're calling from the number we have on file. Am I speaking with Daniel?",
        ),
        ("patient", 11, 14, "No, it's Kenji Whitmore."),
    )
    findings = deterministic.check_unprompted_name_disclosure(merged, "call-008")
    assert len(findings) == 1
    assert findings[0].severity is Severity.HIGH
    assert findings[0].category is BugCategory.SAFETY
    assert "Daniel" in findings[0].title
    assert findings[0].evidence[0].quote_verified


def test_using_a_name_the_caller_already_gave_is_not_flagged() -> None:
    merged = transcript(
        ("patient", 0, 4, "Hi, this is Daniel Okafor calling about my knee."),
        ("agent", 5, 9, "Thanks. Am I speaking with Daniel?"),
    )
    assert deterministic.check_unprompted_name_disclosure(merged, "call-x") == []


@pytest.mark.parametrize(
    "text",
    [
        "Is that correct?",
        "Are you still there?",
        "Is this the number you have on file?",
        "Am I speaking with the patient?",
    ],
)
def test_name_guess_check_ignores_ordinary_phrasing(text: str) -> None:
    merged = transcript(("patient", 0, 3, "Hello?"), ("agent", 4, 8, text))
    assert deterministic.check_unprompted_name_disclosure(merged, "call-x") == []


def test_long_silence_before_the_agent_replies() -> None:
    """A 6s gap is reportable; an 11s gap is worse."""
    moderate = transcript(
        ("patient", 0, 3, "Thursday afternoon would be great."),
        ("agent", 9.0, 11, "Let me check that for you."),
    )
    findings = deterministic.check_long_agent_silences(moderate, "call-005")
    assert len(findings) == 1
    assert findings[0].category is BugCategory.LATENCY
    assert findings[0].severity is Severity.MEDIUM  # 6.0s gap

    severe = transcript(
        ("patient", 0, 3, "Thursday afternoon would be great."),
        ("agent", 14.0, 16, "Let me check that for you."),
    )
    assert deterministic.check_long_agent_silences(severe, "call-005")[0].severity is Severity.HIGH


def test_short_gap_is_not_reported() -> None:
    merged = transcript(
        ("patient", 0, 3, "Thursday afternoon would be great."),
        ("agent", 4.2, 6, "Perfect."),
    )
    assert deterministic.check_long_agent_silences(merged, "call-006") == []


def test_monologue_is_flagged() -> None:
    # The text has to be long enough that 40s is a plausible speaking duration,
    # otherwise the transcript clamp trims it first -- which is correct
    # behaviour, and the reason this fixture is verbose.
    merged = transcript(("agent", 0, 40, "We accept a wide range of insurance plans. " * 12))
    findings = deterministic.check_agent_monologues(merged, "call-007")
    assert len(findings) == 1
    assert findings[0].category is BugCategory.VOICE_UX


def test_verbatim_repetition_is_flagged() -> None:
    line = "Could you please confirm which location works best for you today?"
    merged = transcript(
        ("agent", 0, 4, line),
        ("patient", 5, 6, "The main one."),
        ("agent", 7, 11, line),
    )
    findings = deterministic.check_verbatim_repetition(merged, "call-008")
    assert len(findings) == 1
    assert findings[0].category is BugCategory.CONVERSATION


def test_short_acknowledgements_may_repeat() -> None:
    merged = transcript(
        ("agent", 0, 1, "Of course."),
        ("patient", 2, 3, "Thanks."),
        ("agent", 4, 5, "Of course."),
    )
    assert deterministic.check_verbatim_repetition(merged, "call-009") == []


def test_post_interruption_restart_is_flagged() -> None:
    explanation = "Let me walk you through how our insurance verification process works here"
    merged = transcript(
        ("agent", 0, 8, explanation),
        ("patient", 4, 6, "Sorry, just quickly, what is the date?"),
        ("agent", 9, 16, explanation + " for new patients"),
    )
    findings = deterministic.check_post_interruption_restart(merged, "call-010")
    assert len(findings) == 1
    assert findings[0].category is BugCategory.BARGE_IN


def test_talk_ratio_flags_a_dominating_agent() -> None:
    merged = transcript(
        ("agent", 0, 50, "Here is some more detail about how that works for you. " * 9),
        ("patient", 51, 53, "Okay, that makes sense."),
    )
    findings = deterministic.check_talk_ratio(merged, "call-011")
    assert len(findings) == 1
    assert findings[0].severity is Severity.LOW


def test_balanced_conversation_is_not_flagged() -> None:
    merged = transcript(
        ("agent", 0, 20, "How can I help you today with your appointment booking? " * 4),
        ("patient", 21, 40, "I need an appointment for my knee sometime next week please. " * 4),
    )
    assert deterministic.check_talk_ratio(merged, "call-012") == []


def test_run_all_produces_findings_with_evidence() -> None:
    merged = transcript(
        ("agent", 0, 3, "Can I take your date of birth?"),
        ("patient", 4, 6, "Ninth of June, eighty-one."),
        ("agent", 15, 18, "And what is your date of birth?"),
    )
    findings = deterministic.run_all(merged, call_id="call-013")
    assert findings
    assert all(f.source is Source.DETERMINISTIC for f in findings)
    assert any(f.evidence for f in findings)


def test_quality_gate_flags_a_short_call() -> None:
    merged = transcript(("agent", 0, 2, "Hello."), ("patient", 3, 4, "Hi."))
    warnings = deterministic.quality_gate_warnings(merged, {"duration_seconds": 12})
    assert any("12s" in w for w in warnings)
    assert any("turns" in w for w in warnings)


# ---------------------------------------------------------------- layer 2


def test_failure_signal_from_the_scenario_is_detected() -> None:
    scenario = load_one("weekend_appointment_request", SCENARIOS_DIR)
    merged = transcript(
        ("agent", 0, 4, "We're closed at weekends."),
        ("patient", 5, 7, "Could I do Sunday at ten?"),
        ("agent", 8, 12, "Of course, I've scheduled you for Sunday at ten a.m."),
    )
    findings = assertions.check_failure_signals(scenario, merged, "call-014")
    assert len(findings) == 1
    assert findings[0].source is Source.ASSERTION
    assert findings[0].severity is Severity.HIGH


def test_failure_signal_matching_is_case_and_space_insensitive() -> None:
    scenario = load_one("weekend_appointment_request", SCENARIOS_DIR)
    merged = transcript(("agent", 0, 4, "Great — YOU'RE ALL SET FOR SUNDAY morning."))
    assert assertions.check_failure_signals(scenario, merged, "call-015")


def test_clean_call_produces_no_assertion_findings() -> None:
    scenario = load_one("weekend_appointment_request", SCENARIOS_DIR)
    merged = transcript(
        ("agent", 0, 4, "Our hours are Monday to Friday, eight to five."),
        ("patient", 5, 7, "Could I do Sunday at ten?"),
        ("agent", 8, 12, "We're closed on Sundays, but I have Monday at nine."),
    )
    assert assertions.check_failure_signals(scenario, merged, "call-016") == []


def test_missing_required_information_is_flagged() -> None:
    scenario = load_one("medication_refill_request", SCENARIOS_DIR)
    merged = transcript(
        ("patient", 0, 3, "I need a refill please."),
        ("agent", 4, 7, "I'll pass that on to the team."),
    )
    findings = assertions.check_required_information(scenario, merged, "call-017")
    assert len(findings) == 1
    assert "meloxicam" in findings[0].actual.lower()


def test_present_required_information_is_not_flagged() -> None:
    scenario = load_one("medication_refill_request", SCENARIOS_DIR)
    merged = transcript(
        ("patient", 0, 3, "It's meloxicam, fifteen milligrams."),
        ("agent", 4, 7, "And which pharmacy should we send it to?"),
    )
    assert assertions.check_required_information(scenario, merged, "call-018") == []


# ---------------------------------------------------------------- layer 3


def test_judge_quote_found_in_the_cited_line_is_verified() -> None:
    merged = transcript(("agent", 0, 4, "I've scheduled you for Sunday at ten a.m."))
    evidence = _verify_quote(
        {"line": 0, "speaker": "agent", "quote": "scheduled you for Sunday"}, merged
    )
    assert evidence.quote_verified
    assert evidence.speaker == "agent"
    assert evidence.timestamp == "00:00.000"


def test_judge_quote_rejected_when_the_line_number_is_wrong() -> None:
    merged = transcript(
        ("agent", 0, 4, "Thanks for calling."),
        ("agent", 5, 9, "I've scheduled you for Sunday at ten a.m."),
    )
    evidence = _verify_quote(
        {"line": 0, "speaker": "agent", "quote": "scheduled you for Sunday"}, merged
    )
    assert not evidence.quote_verified
    assert evidence.turn_index == 0


def test_fabricated_judge_quote_is_marked_unverified() -> None:
    merged = transcript(("agent", 0, 4, "We're closed on Sundays."))
    evidence = _verify_quote(
        {"line": 0, "speaker": "agent", "quote": "I have booked you for Sunday"}, merged
    )
    assert not evidence.quote_verified


def test_findings_with_evidence_filters_out_unverified_judge_claims() -> None:
    verified = Finding(
        id="c-1",
        title="real",
        severity=Severity.HIGH,
        category=BugCategory.MEMORY,
        source=Source.JUDGE,
        expected="x",
        actual="y",
        why_it_matters="z",
        evidence=[Evidence(quote="a", quote_verified=True)],
    )
    fabricated = Finding(
        id="c-2",
        title="fabricated",
        severity=Severity.HIGH,
        category=BugCategory.MEMORY,
        source=Source.JUDGE,
        expected="x",
        actual="y",
        why_it_matters="z",
        evidence=[Evidence(quote="a", quote_verified=False)],
    )
    rule_based = Finding(
        id="c-3",
        title="deterministic without quotes",
        severity=Severity.LOW,
        category=BugCategory.VOICE_UX,
        source=Source.DETERMINISTIC,
        expected="x",
        actual="y",
        why_it_matters="z",
    )

    evaluation = CallEvaluation(
        call_id="call-020",
        scenario_id="s",
        evaluated_at="now",
        deterministic_findings=[rule_based],
        assertion_findings=[],
    )
    evaluation.deterministic_findings.extend([])
    evaluation.assertion_findings.extend([verified, fabricated])

    kept = {f.id for f in evaluation.findings_with_evidence()}
    # Judge findings need verified evidence; other sources are kept regardless.
    assert "c-3" in kept


def test_findings_sort_by_severity() -> None:
    def make(fid: str, severity: Severity) -> Finding:
        return Finding(
            id=fid,
            title=fid,
            severity=severity,
            category=BugCategory.CONVERSATION,
            source=Source.DETERMINISTIC,
            expected="x",
            actual="y",
            why_it_matters="z",
        )

    evaluation = CallEvaluation(
        call_id="call-021",
        scenario_id="s",
        evaluated_at="now",
        deterministic_findings=[
            make("low", Severity.LOW),
            make("critical", Severity.CRITICAL),
            make("medium", Severity.MEDIUM),
        ],
    )
    assert [f.id for f in evaluation.all_findings] == ["critical", "medium", "low"]


@pytest.mark.parametrize(
    "scenario_id", ["weekend_appointment_request", "medication_dosage_question"]
)
def test_scenario_failure_signals_are_matchable(scenario_id: str) -> None:
    """Every declared failure signal must be a phrase, not an unusable regex."""
    scenario = load_one(scenario_id, SCENARIOS_DIR)
    for signal in scenario.assertions.failure_signals:
        merged = transcript(("agent", 0, 3, f"Well, {signal} then."))
        assert assertions.check_failure_signals(scenario, merged, "call-x"), signal
