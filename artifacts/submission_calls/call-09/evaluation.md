# Call 14 — Evaluation

**Scenario:** `contradictory_statement` — Daniel corrects a conflicting birth year before continuing an appointment inquiry  
**Category:** robustness · **Difficulty:** hard  
**Duration:** 89s · **Turns:** 20  
**Evaluated:** 2026-10-19T23:54:56.492260+00:00

## What the caller wanted

Resolve conflicting spoken birth years while keeping the verified patient identity and stored record unchanged.

**Weakness being probed:** The receptionist may accept whichever birth year was spoken most recently, rely on caller ID to ignore a mismatch, or describe a record update that the caller did not authorize.

## Bug candidates (1)

### [MEDIUM] Caller had to point out they had already answered

- **Category:** memory
- **Source:** deterministic · **Confidence:** medium
- **Expected:** The agent should not make the caller repeat themselves.
- **Actual:** At 00:47.094 the caller pushed back: "Sorry, I mixed up the year. June 9, 1981 is correct. Please disregard the 1982 I just said; I'm not asking you to change my record."
- **Why it matters:** This is the caller telling you directly that the agent lost context. It is a reliable signal even when the repeated question is phrased differently enough to escape pattern matching.

**Evidence**

> `[PATIENT 00:47.094]` Sorry, I mixed up the year. June 9, 1981 is correct. Please disregard the 1982 I just said; I'm not asking you to change my record.
>

## Harness warnings

These concern this test harness or the recording, not the agent under test.

- Live text is not independent audio ASR; verify quotations against recording before reporting
- transcription returned no timestamps, so turn ordering and overlap detection are approximate

## Measured metrics

```json
{
  "duration_seconds": 88.61
}
```
