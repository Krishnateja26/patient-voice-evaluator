# Call 5 — Evaluation

**Scenario:** `schedule_new_patient_knee` — New patient books a first appointment for knee pain  
**Category:** core · **Difficulty:** easy  
**Duration:** 117s · **Turns:** 21  
**Evaluated:** 2026-10-19T18:44:10.973597+00:00

## What the caller wanted

Book a first appointment for a knee that has been painful for about three weeks.

**Weakness being probed:** Baseline. Establishes what a clean, cooperative scheduling call looks like so that failures in harder scenarios can be attributed to the scenario rather than to the agent being broken generally.

## Bug candidates (0)

No defects were identified in this call.

## Harness warnings

These concern this test harness or the recording, not the agent under test.

- Live text is not independent audio ASR; verify quotations against recording before reporting
- transcription returned no timestamps, so turn ordering and overlap detection are approximate

## Measured metrics

```json
{
  "duration_seconds": 117.033
}
```
