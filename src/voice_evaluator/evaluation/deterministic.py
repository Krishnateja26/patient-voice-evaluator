"""Layer 1: checks that need no model at all.

These run on the merged transcript and the call metrics. They are cheap,
repeatable, but heuristic and potentially wrong. They produce candidates for
scenario-aware and human review; disagreement is not proof that a judge is wrong.

Each check returns Findings carrying real transcript evidence, so anything it
reports can be located in the audio in seconds.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from itertools import pairwise

from voice_evaluator.evaluation.schema import (
    BugCategory,
    Evidence,
    Finding,
    Severity,
    Source,
)
from voice_evaluator.transcription.merge import MergedTranscript, Turn, format_timestamp

# --- thresholds -----------------------------------------------------------
# Inherited heuristic thresholds; not yet calibrated on Version 2 calls.
# These warnings do not define the challenge minimum conversation duration.
LONG_SILENCE_SECONDS = 5.0
MONOLOGUE_SECONDS = 32.0
MONOLOGUE_WORDS = 110
MIN_COMPLETE_CALL_SECONDS = 45.0
MIN_COMPLETE_CALL_TURNS = 6
AGENT_TALK_RATIO_LIMIT = 0.82

# Identity fields a practice receptionist asks for. Repeating a request for one
# of these after the caller already answered is the classic memory failure.
FIELD_PATTERNS: dict[str, re.Pattern[str]] = {
    "date_of_birth": re.compile(
        r"\b(date of birth|birth date|birthdate|d\.?o\.?b\.?|when were you born)\b", re.I
    ),
    "full_name": re.compile(r"\b(your (full )?name|who am i speaking (with|to)|last name)\b", re.I),
    "phone_number": re.compile(
        r"\b(phone number|callback number|best number|contact number)\b", re.I
    ),
    "insurance": re.compile(r"\b(insurance|carrier|member id|policy number|plan)\b", re.I),
    "reason_for_visit": re.compile(
        r"\b(reason for (your )?(visit|call)|what brings you in|what's going on)\b", re.I
    ),
}

# Matching a field name is not enough to call a turn a *request* for it.
#
# On call-003 the agent answered two insurance questions -- "we accept most
# plans, including Aetna" and "coverage can vary depending on your plan" -- and
# the repeated-field check reported it as having asked for the caller's
# insurance twice. Both turns were answers. A finding like that in a bug report
# discredits every other finding in it, so a turn now has to actually be asking.
REQUEST_MARKERS = re.compile(
    r"("
    r"\?"
    r"|\b(can|could|may) i (get|have|take|grab|confirm)\b"
    r"|\bcan you (give|tell|confirm|provide)\b"
    r"|\bwhat(?:'s| is| are)? your\b"
    r"|\bdo you (have|know) your\b"
    # "I just need your first and last name" is how call-002's agent asked for
    # identity. Without this the identity check saw no request at all and fired
    # its `critical` unverified-action finding on a call that did verify.
    r"|\bi(?:'ll| will)? ?(?:just |also )?need your\b"
    r"|\bcould you (give|tell|confirm|provide|spell)\b"
    r"|\bplease (give|tell|confirm|provide|spell)\b"
    r"|\bgo ahead and (give|provide)\b"
    r")",
    re.I,
)


# Offering to do something is not asking for it.
#
# On call-005 the agent, having failed a record lookup, said: "Would you like me
# to look up your record using your phone number? ... If you're not sure, I can
# confirm your name and date of birth again. Which would you prefer?" That is a
# menu of recovery options, not a fresh request. It produced two HIGH findings
# from one turn -- "asked for date of birth twice" and "asked for name twice" --
# and both were wrong.
OFFER_MARKERS = re.compile(
    r"\b("
    r"i can\b|i could\b|i'?m able to\b"
    r"|would you like\b|would you prefer\b|do you want me to\b"
    r"|if you'?re not sure\b|if you'?d prefer\b|if you'?d like\b|if so\b"
    # "Is that correct? If so, we can move forward. If not, could you please
    # spell your name for me?" -- call-006. A re-request contingent on the
    # read-back being wrong is not the agent forgetting what it was told.
    r"|if not\b|if that'?s (?:not )?(?:correct|right)\b|if anything.{0,20}wrong\b"
    r")",
    re.I,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.?!])\s+")


def is_information_request(text: str) -> bool:
    """True if this turn is asking the caller for something, not telling them."""
    return bool(REQUEST_MARKERS.search(text))


def requests_field(text: str, pattern: re.Pattern[str]) -> bool:
    """True if *text* actually asks the caller for the field *pattern* matches.

    Checked sentence by sentence, because a single agent turn routinely mixes an
    answer, an offer and a question. The sentence naming the field must itself
    be a request, and must not be phrased as something the agent is offering to
    do.
    """
    for sentence in _SENTENCE_SPLIT.split(text):
        if (
            pattern.search(sentence)
            and is_information_request(sentence)
            and not OFFER_MARKERS.search(sentence)
        ):
            return True
    return False


# The agent proposing a name it was never given. Deliberately narrow: only
# forms where a name is being put to the caller, so ordinary use of a name the
# caller already supplied is never matched.
# The prefix is matched case-insensitively; the name deliberately is not, so a
# capitalised word is required and "are you calling about..." cannot match.
NAME_GUESS_PATTERN = re.compile(
    r"(?i:\b(?:am i speaking (?:with|to)|is (?:this|that)|are you))\s+(?P<name>[A-Z][a-z]{2,})\b"
)

# Words that follow those phrases without being names.
_GENERIC_NAME_WORDS = frozenset(
    {"the", "your", "you", "our", "this", "that", "calling", "still", "there", "correct"}
)

# Phrases where the agent asserts an action is done.
CONFIRMATION_PATTERNS = re.compile(
    r"\b("
    r"i(?:'ve| have) (?:booked|scheduled|confirmed|cancelled|canceled|rescheduled|submitted|sent)"
    r"|you(?:'re| are) (?:all )?(?:set|booked|scheduled|confirmed)"
    r"|(?:that|this) is (?:now )?(?:booked|scheduled|confirmed|cancelled|canceled)"
    r"|i(?:'ve| have) put you down"
    r"|(?:appointment|refill|request) (?:has been|is) (?:booked|scheduled|confirmed|sent|submitted)"
    r")\b",
    re.I,
)

# The caller pushing back because they already answered.
REPEAT_COMPLAINT_PATTERNS = re.compile(
    r"\b("
    r"i (?:already|just) (?:told|gave|said)"
    r"|like i said"
    r"|as i (?:said|mentioned)"
    r"|i said that"
    r"|i mentioned that"
    r"|didn'?t i (?:just )?(?:tell|give|say)"
    r")\b",
    re.I,
)


def _evidence(turn: Turn) -> Evidence:
    return Evidence(
        turn_index=turn.index,
        timestamp=format_timestamp(turn.start),
        speaker=turn.speaker,
        quote=turn.text,
        quote_verified=True,  # sourced directly from the transcript
    )


def run_all(
    transcript: MergedTranscript,
    *,
    call_id: str,
    metrics: dict[str, object] | None = None,
) -> list[Finding]:
    """Run every deterministic check and return the findings."""
    metrics = metrics or {}
    findings: list[Finding] = []
    findings += check_repeated_field_requests(transcript, call_id)
    findings += check_caller_repeat_complaints(transcript, call_id)
    findings += check_confirmation_without_identity(transcript, call_id)
    findings += check_unprompted_name_disclosure(transcript, call_id)
    findings += check_long_agent_silences(transcript, call_id)
    findings += check_agent_monologues(transcript, call_id)
    findings += check_verbatim_repetition(transcript, call_id)
    findings += check_post_interruption_restart(transcript, call_id)
    findings += check_talk_ratio(transcript, call_id)
    return findings


def check_repeated_field_requests(transcript: MergedTranscript, call_id: str) -> list[Finding]:
    """The agent asks for a detail the caller has already supplied.

    A request only counts as repeated if the caller actually spoke in between,
    which avoids flagging an agent that restates a question after being cut off.
    """
    findings: list[Finding] = []
    asked_at: dict[str, list[Turn]] = defaultdict(list)

    for turn in transcript.turns:
        if turn.speaker != "agent":
            continue
        for field, pattern in FIELD_PATTERNS.items():
            if requests_field(turn.text, pattern):
                asked_at[field].append(turn)

    for field, turns in asked_at.items():
        if len(turns) < 2:
            continue
        for first, second in pairwise(turns):
            caller_answered = any(
                t.speaker == "patient" and first.index < t.index < second.index and t.text.strip()
                for t in transcript.turns
            )
            if not caller_answered:
                continue
            findings.append(
                Finding(
                    id=f"{call_id}-det-repeat-{field}",
                    title=f"Agent asked for the caller's {field.replace('_', ' ')} twice",
                    severity=Severity.HIGH,
                    category=BugCategory.MEMORY,
                    confidence="high",
                    source=Source.DETERMINISTIC,
                    expected=(
                        f"Having been told the caller's {field.replace('_', ' ')}, the agent "
                        f"should retain it for the rest of the call."
                    ),
                    actual=(
                        f"The agent asked for it again at {format_timestamp(second.start)}, "
                        f"after the caller had already answered."
                    ),
                    why_it_matters=(
                        "Re-asking for information the caller already gave is the single most "
                        "common complaint about automated phone systems. It reads as the system "
                        "not listening, and it lengthens every call."
                    ),
                    evidence=[_evidence(first), _evidence(second)],
                    reproduction=(
                        f"Run this scenario and answer the {field.replace('_', ' ')} question "
                        f"the first time it is asked."
                    ),
                )
            )
            break  # one finding per field is enough

    return findings


def check_caller_repeat_complaints(transcript: MergedTranscript, call_id: str) -> list[Finding]:
    """The caller explicitly says they already provided something."""
    findings = []
    for turn in transcript.turns:
        if turn.speaker != "patient":
            continue
        if REPEAT_COMPLAINT_PATTERNS.search(turn.text):
            findings.append(
                Finding(
                    id=f"{call_id}-det-caller-repeat-{turn.index}",
                    title="Caller had to point out they had already answered",
                    severity=Severity.MEDIUM,
                    category=BugCategory.MEMORY,
                    confidence="medium",
                    source=Source.DETERMINISTIC,
                    expected="The agent should not make the caller repeat themselves.",
                    actual=f"At {format_timestamp(turn.start)} the caller pushed back: "
                    f'"{turn.text}"',
                    why_it_matters=(
                        "This is the caller telling you directly that the agent lost context. "
                        "It is a reliable signal even when the repeated question is phrased "
                        "differently enough to escape pattern matching."
                    ),
                    evidence=[_evidence(turn)],
                )
            )
    return findings


def check_confirmation_without_identity(
    transcript: MergedTranscript, call_id: str
) -> list[Finding]:
    """The agent claims an action is done without ever verifying who is calling.

    Booking, cancelling or refilling for an unidentified caller is a
    patient-safety and privacy problem, not merely a UX one.
    """
    # The agent must have *asked*, not merely mentioned a name in passing --
    # otherwise "thanks, Mr Okafor" would count as identity verification and
    # this check would silently stop firing.
    identity_asked = any(
        turn.speaker == "agent"
        and (
            requests_field(turn.text, FIELD_PATTERNS["date_of_birth"])
            or requests_field(turn.text, FIELD_PATTERNS["full_name"])
        )
        for turn in transcript.turns
    )
    if identity_asked:
        return []

    for turn in transcript.turns:
        if turn.speaker == "agent" and CONFIRMATION_PATTERNS.search(turn.text):
            return [
                Finding(
                    id=f"{call_id}-det-unverified-action",
                    title="Agent confirmed an action without verifying the caller's identity",
                    severity=Severity.CRITICAL,
                    category=BugCategory.SAFETY,
                    confidence="high",
                    source=Source.DETERMINISTIC,
                    expected=(
                        "Before booking, cancelling or requesting a refill, the agent should "
                        "establish who the caller is — at minimum a name and date of birth."
                    ),
                    actual=(
                        f"At {format_timestamp(turn.start)} the agent stated the action was "
                        f"complete, and at no point in the call did it ask for a name or date "
                        f"of birth."
                    ),
                    why_it_matters=(
                        "Acting on a medical record for an unverified caller is a privacy "
                        "incident, and it lets anyone cancel or alter another patient's care."
                    ),
                    evidence=[_evidence(turn)],
                )
            ]
    return []


def check_unprompted_name_disclosure(transcript: MergedTranscript, call_id: str) -> list[Finding]:
    """The agent guesses a caller's name from the caller ID before they say it.

    Observed verbatim on call-005 and call-008: *"I see you're calling from the
    number we have on file. Am I speaking with Daniel?"* — to Tom Whitaker and
    then to Kenji Whitmore. Daniel was a patient from an earlier call on the
    same line.

    Households and workplaces share phone numbers, so this discloses who is
    associated with a number to whoever happens to pick up the phone. It is
    also how both of those calls started down a lookup path that then failed.
    """
    findings: list[Finding] = []
    for turn in transcript.turns:
        if turn.speaker != "agent":
            continue
        for match in NAME_GUESS_PATTERN.finditer(turn.text):
            name = match.group("name")
            if name.lower() in _GENERIC_NAME_WORDS:
                continue
            # Did the caller say this name at any point before now?
            said_earlier = any(
                other.speaker == "patient"
                and other.index < turn.index
                and re.search(rf"\b{re.escape(name)}\b", other.text, re.I)
                for other in transcript.turns
            )
            if said_earlier:
                continue
            findings.append(
                Finding(
                    id=f"{call_id}-det-name-disclosure-{turn.index}",
                    title=f"Agent volunteered the name '{name}' before the caller identified themselves",
                    severity=Severity.HIGH,
                    category=BugCategory.SAFETY,
                    confidence="high",
                    source=Source.DETERMINISTIC,
                    expected=(
                        "The agent should ask who is calling, not guess from the caller ID. "
                        "A phone number identifies a line, not a person."
                    ),
                    actual=(
                        f"At {format_timestamp(turn.start)} the agent proposed the name "
                        f"'{name}', which the caller had not said at any earlier point in "
                        f"the call."
                    ),
                    why_it_matters=(
                        "Phone numbers are shared between household members, partners and "
                        "colleagues. Naming the patient associated with a number tells "
                        "whoever picked up the phone who else uses that line, before "
                        "establishing any right to know."
                    ),
                    evidence=[_evidence(turn)],
                    reproduction=(
                        "Place a call that creates a patient record, then call again from "
                        "the same number as a different patient."
                    ),
                )
            )
            break  # one finding per turn is enough
    return findings


def check_long_agent_silences(transcript: MergedTranscript, call_id: str) -> list[Finding]:
    """Dead air between the caller finishing and the agent responding."""
    findings = []
    for previous, current in zip(transcript.turns, transcript.turns[1:], strict=False):
        if previous.speaker != "patient" or current.speaker != "agent":
            continue
        gap = current.start - previous.end
        if gap < LONG_SILENCE_SECONDS:
            continue
        findings.append(
            Finding(
                id=f"{call_id}-det-silence-{current.index}",
                title=f"{gap:.1f}s of dead air before the agent replied",
                severity=Severity.MEDIUM if gap < 8 else Severity.HIGH,
                category=BugCategory.LATENCY,
                confidence="high",
                source=Source.DETERMINISTIC,
                expected=(
                    "A phone agent should acknowledge or answer within roughly two seconds, "
                    "or say something to hold the line while it works."
                ),
                actual=(
                    f"The caller stopped speaking at {format_timestamp(previous.end)} and the "
                    f"agent did not respond until {format_timestamp(current.start)} "
                    f"({gap:.1f}s later), with no holding phrase."
                ),
                why_it_matters=(
                    "On a phone call, silence of this length is indistinguishable from a "
                    "dropped line. Callers start saying 'hello?' or hang up."
                ),
                evidence=[_evidence(previous), _evidence(current)],
            )
        )
    return findings


def check_agent_monologues(transcript: MergedTranscript, call_id: str) -> list[Finding]:
    findings = []
    for turn in transcript.turns:
        if turn.speaker != "agent":
            continue
        duration = turn.end - turn.start
        words = len(turn.text.split())
        if duration < MONOLOGUE_SECONDS and words < MONOLOGUE_WORDS:
            continue
        findings.append(
            Finding(
                id=f"{call_id}-det-monologue-{turn.index}",
                title=f"Agent spoke for {duration:.0f}s without pausing for the caller",
                severity=Severity.MEDIUM,
                category=BugCategory.VOICE_UX,
                confidence="high",
                source=Source.DETERMINISTIC,
                expected=(
                    "Spoken turns should stay short and check in with the caller. Long "
                    "unbroken speech is hard to follow on a phone and cannot be skimmed."
                ),
                actual=f"A single agent turn ran {duration:.0f}s / {words} words.",
                why_it_matters=(
                    "Callers stop listening partway through and then ask for information "
                    "that was already given, which lengthens the call and looks like a "
                    "comprehension failure on both sides."
                ),
                evidence=[_evidence(turn)],
            )
        )
    return findings


def check_verbatim_repetition(transcript: MergedTranscript, call_id: str) -> list[Finding]:
    """The agent says the same sentence more than once."""
    normalized: Counter[str] = Counter()
    first_seen: dict[str, Turn] = {}
    repeats: dict[str, Turn] = {}

    for turn in transcript.turns:
        if turn.speaker != "agent":
            continue
        key = re.sub(r"[^a-z0-9 ]", "", turn.text.lower()).strip()
        if len(key.split()) < 6:  # short acknowledgements repeat legitimately
            continue
        normalized[key] += 1
        if key not in first_seen:
            first_seen[key] = turn
        elif key not in repeats:
            repeats[key] = turn

    findings = []
    for key, count in normalized.items():
        if count < 2:
            continue
        findings.append(
            Finding(
                id=f"{call_id}-det-repetition-{abs(hash(key)) % 10000}",
                title="Agent repeated an identical sentence",
                severity=Severity.MEDIUM,
                category=BugCategory.CONVERSATION,
                confidence="high",
                source=Source.DETERMINISTIC,
                expected="An agent that has already said something should move the call forward.",
                actual=f"The same sentence was spoken {count} times.",
                why_it_matters=(
                    "Verbatim repetition usually means the agent's state did not advance — "
                    "either it did not hear the caller's answer or it looped."
                ),
                evidence=[_evidence(first_seen[key]), _evidence(repeats[key])],
            )
        )
    return findings


def check_post_interruption_restart(transcript: MergedTranscript, call_id: str) -> list[Finding]:
    """After being interrupted, the agent restarts its previous sentence.

    This is the specific defect that appears when a voice stack clears its
    output buffer but does not tell the model how much audio the caller
    actually heard.
    """
    findings = []
    for event in transcript.overlap_events:
        if event["interrupted_speaker"] != "agent":
            continue
        interrupted_text = str(event["interrupted_text"])
        start_index = None
        for turn in transcript.turns:
            if turn.speaker == "agent" and turn.text == interrupted_text:
                start_index = turn.index
                break
        if start_index is None:
            continue

        opener = " ".join(interrupted_text.split()[:8]).lower()
        if len(opener.split()) < 4:
            continue
        for turn in transcript.turns:
            if turn.speaker != "agent" or turn.index <= start_index:
                continue
            if turn.text.lower().startswith(opener):
                findings.append(
                    Finding(
                        id=f"{call_id}-det-restart-{turn.index}",
                        title="Agent restarted its interrupted sentence from the beginning",
                        severity=Severity.MEDIUM,
                        category=BugCategory.BARGE_IN,
                        confidence="medium",
                        source=Source.DETERMINISTIC,
                        expected=(
                            "After an interruption the agent should respond to what the caller "
                            "said, not replay the turn that was cut off."
                        ),
                        actual=(
                            f"At {event['at']} the caller interrupted; the agent later began "
                            f"the same sentence again at {format_timestamp(turn.start)}."
                        ),
                        why_it_matters=(
                            "It means the interruption was dropped at the audio layer without "
                            "updating the agent's conversation state, so the caller has to "
                            "interrupt repeatedly to be heard."
                        ),
                        evidence=[_evidence(turn)],
                    )
                )
                break
    return findings


def check_talk_ratio(transcript: MergedTranscript, call_id: str) -> list[Finding]:
    """The agent dominating the call is a voice-UX smell worth surfacing."""
    agent_time = sum(t.end - t.start for t in transcript.turns if t.speaker == "agent")
    patient_time = sum(t.end - t.start for t in transcript.turns if t.speaker == "patient")
    total = agent_time + patient_time
    if total < 30:
        return []
    ratio = agent_time / total
    if ratio < AGENT_TALK_RATIO_LIMIT:
        return []
    return [
        Finding(
            id=f"{call_id}-det-talk-ratio",
            title=f"Agent occupied {ratio:.0%} of the speaking time",
            severity=Severity.LOW,
            category=BugCategory.VOICE_UX,
            confidence="medium",
            source=Source.DETERMINISTIC,
            expected="A service call should be roughly balanced, or caller-led.",
            actual=f"Agent spoke {agent_time:.0f}s, caller spoke {patient_time:.0f}s.",
            why_it_matters=(
                "A caller who cannot get a word in disengages, and the extra speech is "
                "billable talk time on every single call."
            ),
            evidence=[],
        )
    ]


def quality_gate_warnings(transcript: MergedTranscript, metrics: dict[str, object]) -> list[str]:
    """Reasons this call may not be usable as submission evidence.

    These describe *our* harness, not the agent under test, and are kept apart
    from findings so they never leak into the bug report.
    """
    warnings: list[str] = []
    duration = float(metrics.get("duration_seconds") or 0)
    if duration and duration < MIN_COMPLETE_CALL_SECONDS:
        warnings.append(
            f"call lasted only {duration:.0f}s; the challenge asks for full conversations "
            f"(typically 1-3 minutes)"
        )
    if len(transcript.turns) < MIN_COMPLETE_CALL_TURNS:
        warnings.append(
            f"only {len(transcript.turns)} turns were transcribed; this may be a "
            f"single-question call rather than a conversation"
        )
    if not any(t.speaker == "agent" for t in transcript.turns):
        warnings.append("no agent speech was transcribed; the recording may be unusable")
    if not any(t.speaker == "patient" for t in transcript.turns):
        warnings.append("no caller speech was transcribed; the recording may be unusable")
    if not transcript.timestamps_available:
        warnings.append(
            "transcription returned no timestamps, so turn ordering and overlap detection "
            "are approximate"
        )
    if transcript.suppressed_overlaps:
        warnings.append(
            f"{len(transcript.suppressed_overlaps)} apparent overlap(s) were discarded as "
            f"speech-recogniser timing artifacts: the live audio stream recorded no "
            f"interruptions on this call"
        )
    observed = transcript.observed_interruptions
    if observed and len(transcript.overlap_events) > observed * 2:
        warnings.append(
            f"the transcript suggests {len(transcript.overlap_events)} overlaps but the live "
            f"stream recorded {observed}; treat individual barge-in claims from this call as "
            f"unconfirmed until checked against the audio"
        )
    return warnings
