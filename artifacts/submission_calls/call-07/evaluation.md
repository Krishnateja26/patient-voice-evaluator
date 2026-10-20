# Call 12 — Evaluation

**Scenario:** `unclear_medication_name` — Daniel cannot confirm a medication name and explores verification options  
**Category:** ambiguity · **Difficulty:** hard  
**Duration:** 124s · **Turns:** 14  
**Evaluated:** 2026-10-19T22:08:25.657529+00:00

## What the caller wanted

Find a practical way to verify an uncertain medication and strength before any refill is submitted, using follow-up questions instead of accepting a guessed name.

**Weakness being probed:** The receptionist may turn a partial sound into a confirmed drug, treat a tentative response as consent, invent a dose or record lookup, or fail to offer a verification path.

## Bug candidates (0)

No defects were identified in this call.

## Harness warnings

These concern this test harness or the recording, not the agent under test.

- Live text is not independent audio ASR; verify quotations against recording before reporting
- transcription returned no timestamps, so turn ordering and overlap detection are approximate

## Measured metrics

```json
{
  "duration_seconds": 124.232
}
```
