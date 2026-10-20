# Call 21 — Evaluation

**Scenario:** `cancellation_persistence_check` — Check upcoming appointments in a new call after the cancellation attempt  
**Category:** memory · **Difficulty:** hard  
**Duration:** 80s · **Turns:** 14  
**Evaluated:** 2026-10-20T00:15:48.339387+00:00

## What the caller wanted

Check upcoming appointments in a new call after the cancellation attempt

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
  "duration_seconds": 79.806
}
```
