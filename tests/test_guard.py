"""The dial guard is the safety-critical part of this project, so it gets the
most thorough tests: it is the only thing standing between a typo and a real
phone call to a stranger."""

from __future__ import annotations

import pytest

from voice_evaluator.config import ASSESSMENT_NUMBER
from voice_evaluator.telephony.guard import (
    DestinationNotAllowed,
    InvalidPhoneNumber,
    normalize_e164,
    resolve_caller_id,
    resolve_destination,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+18054398008", "+18054398008"),
        ("18054398008", "+18054398008"),
        ("8054398008", "+18054398008"),
        ("805-439-8008", "+18054398008"),
        ("(805) 439-8008", "+18054398008"),
        ("+1 805 439 8008", "+18054398008"),
        ("  +1-805-439-8008  ", "+18054398008"),
        ("001805 439 8008", "+18054398008"),
        ("+1 (805) 439.8008", "+18054398008"),
        ("+1‑805‑439‑8008", "+18054398008"),  # non-breaking hyphens
    ],
)
def test_normalize_accepts_realistic_formats(raw: str, expected: str) -> None:
    assert normalize_e164(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "abc", "+", "+0123456789", "12345", "+1234567890123456", "805-439-800x", None],
)
def test_normalize_rejects_bad_input(raw) -> None:
    with pytest.raises(InvalidPhoneNumber):
        normalize_e164(raw)


def test_resolve_destination_allows_only_the_assessment_number() -> None:
    assert resolve_destination("805-439-8008") == ASSESSMENT_NUMBER
    assert resolve_destination(ASSESSMENT_NUMBER) == ASSESSMENT_NUMBER


@pytest.mark.parametrize(
    "raw",
    [
        "+15558675309",
        "911",
        "+18054398009",  # one digit off the assessment number
        "+18054398000",
        "+448081570000",
    ],
)
def test_resolve_destination_fails_closed(raw: str) -> None:
    """Anything that is not the assessment number must raise, including near misses."""
    with pytest.raises((DestinationNotAllowed, InvalidPhoneNumber)):
        resolve_destination(raw)


def test_destination_error_explains_the_policy() -> None:
    with pytest.raises(DestinationNotAllowed) as exc:
        resolve_destination("+15558675309")
    message = str(exc.value)
    assert ASSESSMENT_NUMBER in message
    assert "not configurable" in message


def test_caller_id_accepts_any_valid_number() -> None:
    assert resolve_caller_id("415-555-0100") == "+14155550100"


def test_caller_id_requires_a_value() -> None:
    with pytest.raises(InvalidPhoneNumber):
        resolve_caller_id("")
