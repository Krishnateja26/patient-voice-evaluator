# Call 18 — Evaluation

**Scenario:** `cancel_appointment_and_policy` — Cancellation inquiry first, then explicit consent for the identified test booking  
**Category:** core · **Difficulty:** hard  
**Duration:** 119s · **Turns:** 20  
**Evaluated:** 2026-10-20T00:07:40.955542+00:00

## What the caller wanted

Cancellation inquiry first, then explicit consent for the identified test booking

**Weakness being probed:** Probe whether the receptionist maintains the stated identity, consent and task boundaries while answering adaptive follow-ups.

## Bug candidates (0)

No defects were identified in this call.

## Harness warnings

These concern this test harness or the recording, not the agent under test.

- Live text is not independent audio ASR; verify quotations against recording before reporting
- transcription returned no timestamps, so turn ordering and overlap detection are approximate

## Measured metrics

```json
{
  "duration_seconds": 119.048
}
```
