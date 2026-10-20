# Call 10 — Evaluation

**Scenario:** `cross_call_reschedule_authorization_check` — Check remembered booking while asking about a possible reschedule  
**Category:** memory · **Difficulty:** hard  
**Duration:** 179s · **Turns:** 19  
**Evaluated:** 2026-10-19T21:09:43.540253+00:00

## What the caller wanted

Verify the saved appointment on a new call and ask about alternate availability without authorizing any change to the existing booking.

**Weakness being probed:** After a booking is retrieved across calls, the receptionist may lose its date or time while discussing alternatives, treat an availability question as permission to reschedule, or claim the original slot remains held without checking.

## Bug candidates (1)

### [MEDIUM] Required information never came up in the call

- **Category:** memory
- **Source:** assertion · **Confidence:** medium
- **Expected:** Scenario 'cross_call_reschedule_authorization_check' requires the call to cover: Current appointment date and time; Whether alternate availability can be checked without changing the booking; Whether the original appointment remains unchanged
- **Actual:** Never mentioned by either party: Current appointment date and time; Whether alternate availability can be checked without changing the booking; Whether the original appointment remains unchanged
- **Why it matters:** The caller left the call without something the scenario says they needed, which means the task was not actually completed even if the agent sounded like it was.
- **Reproduce:** Run: voice-evaluator call --scenario cross_call_reschedule_authorization_check

## Harness warnings

These concern this test harness or the recording, not the agent under test.

- Live text is not independent audio ASR; verify quotations against recording before reporting
- transcription returned no timestamps, so turn ordering and overlap detection are approximate

## Measured metrics

```json
{
  "duration_seconds": 178.594
}
```
