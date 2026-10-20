# Call 7 — Evaluation

**Scenario:** `new_patient_record_intake` — New patient asks to start a record and book a first visit  
**Category:** core · **Difficulty:** medium  
**Duration:** 162s · **Turns:** 25  
**Evaluated:** 2026-10-19T19:12:28.888089+00:00

## What the caller wanted

Ask the practice to start a new-patient record using the caller's details and arrange the next step toward a first appointment.

**Weakness being probed:** After the caller says they are new, the receptionist may keep searching for an existing chart or transfer without acknowledging the request to begin intake. Test whether it gathers the details it can, clearly explains any limitation, and gives a concrete next step without claiming a record was created unless that action is confirmed.

## Bug candidates (2)

### [HIGH] Agent volunteered the name 'Krishna' before the caller identified themselves

- **Category:** safety
- **Source:** deterministic · **Confidence:** high
- **Expected:** The agent should ask who is calling, not guess from the caller ID. A phone number identifies a line, not a person.
- **Actual:** At 00:31.407 the agent proposed the name 'Krishna', which the caller had not said at any earlier point in the call.
- **Why it matters:** Phone numbers are shared between household members, partners and colleagues. Naming the patient associated with a number tells whoever picked up the phone who else uses that line, before establishing any right to know.
- **Reproduce:** Place a call that creates a patient record, then call again from the same number as a different patient.

**Evidence**

> `[AGENT 00:31.407]` If you're calling from a number we have on file, am I speaking with Krishna Tejaradi?
>

### [MEDIUM] Required information never came up in the call

- **Category:** scheduling
- **Source:** assertion · **Confidence:** medium
- **Expected:** Scenario 'new_patient_record_intake' requires the call to cover: next_step
- **Actual:** Never mentioned by either party: next_step
- **Why it matters:** The caller left the call without something the scenario says they needed, which means the task was not actually completed even if the agent sounded like it was.
- **Reproduce:** Run: voice-evaluator call --scenario new_patient_record_intake

## Harness warnings

These concern this test harness or the recording, not the agent under test.

- Live text is not independent audio ASR; verify quotations against recording before reporting
- transcription returned no timestamps, so turn ordering and overlap detection are approximate

## Measured metrics

```json
{
  "duration_seconds": 161.68
}
```
