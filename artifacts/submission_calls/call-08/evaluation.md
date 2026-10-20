# Call 13 — Evaluation

**Scenario:** `reschedule_existing_appointment` — Daniel changes a reschedule condition before authorizing one replacement  
**Category:** core · **Difficulty:** hard  
**Duration:** 151s · **Turns:** 23  
**Evaluated:** 2026-10-19T23:35:15.847204+00:00

## What the caller wanted

Replace the existing appointment only after a slot meets Daniel's final time requirement, then check the active appointment state and ask about text confirmation.

**Weakness being probed:** The receptionist may act before consent, retain an obsolete time preference, fail to broaden the provider search, leave both appointments active, or promise a text without a clear action.

## Bug candidates (0)

No defects were identified in this call.

## Harness warnings

These concern this test harness or the recording, not the agent under test.

- Live text is not independent audio ASR; verify quotations against recording before reporting
- transcription returned no timestamps, so turn ordering and overlap detection are approximate

## Measured metrics

```json
{
  "duration_seconds": 150.921
}
```
