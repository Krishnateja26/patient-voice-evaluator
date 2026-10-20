"""Fail-closed guard around outbound dialling.

This module is the only sanctioned way to turn a user-supplied string into a
number the harness will dial. It exists because an automated caller that can be
pointed at an arbitrary phone number is a liability: a typo in an environment
variable should produce an exception, never a real call to a stranger.

Design rules:
  * The allowlist is a compile-time constant, not configuration.
  * Normalisation never *widens* what is accepted -- it only removes formatting.
  * Anything that is not exactly an allowlisted E.164 string raises.
"""

from __future__ import annotations

import re

from voice_evaluator.config import ALLOWED_DESTINATIONS

E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")

# Characters humans put in phone numbers that carry no digits of their own.
_FORMATTING = str.maketrans("", "", " -(). ‐‑‒–—")


class DestinationNotAllowed(ValueError):
    """Raised when a dial target is not the authorised assessment number."""


class InvalidPhoneNumber(ValueError):
    """Raised when a string cannot be interpreted as an E.164 number."""


def normalize_e164(raw: str, *, default_country_code: str = "1") -> str:
    """Normalise a human-written phone number into strict E.164.

    Handles the shapes that actually turn up in .env files and documents:
    ``+1-805-439-8008``, ``(805) 439-8008``, ``18054398008``, ``001805...``.

    Raises InvalidPhoneNumber if the result is not valid E.164. This function
    deliberately does not attempt clever parsing of international formats; the
    harness only ever needs one destination.
    """
    if raw is None:
        raise InvalidPhoneNumber("phone number is None")

    candidate = str(raw).strip().translate(_FORMATTING)
    if not candidate:
        raise InvalidPhoneNumber("phone number is empty")

    # International access prefix, e.g. 001805... or 011805...
    if candidate.startswith("00"):
        candidate = "+" + candidate[2:]
    elif candidate.startswith("011") and len(candidate) > 11:
        candidate = "+" + candidate[3:]

    if not candidate.startswith("+"):
        digits = candidate
        if not digits.isdigit():
            raise InvalidPhoneNumber(f"phone number contains non-digits: {raw!r}")
        # A bare NANP number: 10 digits gets the country code, 11 starting with
        # 1 is already country-coded.
        needs_country_code = len(digits) == 10
        candidate = f"+{default_country_code}{digits}" if needs_country_code else f"+{digits}"

    if not E164_RE.match(candidate):
        raise InvalidPhoneNumber(f"not valid E.164 after normalisation: {raw!r} -> {candidate!r}")
    return candidate


def resolve_destination(raw: str) -> str:
    """Normalise *raw* and assert it is the authorised assessment number.

    This is the single choke point before any Twilio call is created.
    """
    number = normalize_e164(raw)
    if number not in ALLOWED_DESTINATIONS:
        allowed = ", ".join(sorted(ALLOWED_DESTINATIONS))
        raise DestinationNotAllowed(
            f"refusing to dial {number}: this harness may only call the Pretty Good AI "
            f"assessment line ({allowed}). The allowlist is a source-code constant and is "
            f"intentionally not configurable."
        )
    return number


def resolve_caller_id(raw: str) -> str:
    """Normalise the caller ID. Any valid E.164 number is acceptable here.

    The challenge requires that a single caller number be used for every test
    call; that number is reported in the submission and recorded in
    docs/SUBMISSION_CHECKLIST.md.
    """
    if not raw:
        raise InvalidPhoneNumber("CALLER_NUMBER is not set")
    return normalize_e164(raw)


def pin_caller_number(raw: str, artifacts_dir) -> str:
    """Persist the first caller ID and refuse changes before any network call."""
    import json
    from pathlib import Path

    number = resolve_caller_id(raw)
    root = Path(artifacts_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / "caller_identity.json"
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump({"caller_number": number}, stream)
    except FileExistsError:
        try:
            previous = json.loads(path.read_text(encoding="utf-8"))["caller_number"]
        except (ValueError, KeyError) as exc:
            raise InvalidPhoneNumber(
                "Caller identity file is invalid; investigate before dialing"
            ) from exc
        if previous != number:
            raise InvalidPhoneNumber(
                "Caller number differs from the campaign identity; refusing to dial"
            ) from None
    return number
