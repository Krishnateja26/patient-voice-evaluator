# Eight-call campaign

User authorized eight sequential assessment calls. Fixed destination and configured caller guards remain active. No audio-reviewed or backend-verified findings are implied. C03/C04/C05/C13/C15: preserve separate scenario snapshots, recordings, transcripts and evidence limits.

1. `contradictory_statement` â€” prepared, not yet dialed
2. `third_party_identity_boundary` â€” prepared, not yet dialed
3. `nonexistent_doctor_request_daniel` â€” prepared, not yet dialed
4. `conflicting_day_and_date_daniel` â€” prepared, not yet dialed
5. `cancel_appointment_and_policy` â€” prepared, not yet dialed
6. `withdrawn_contact_change` â€” prepared, not yet dialed
7. `handoff_recovery_followup` â€” prepared, not yet dialed
8. `cancellation_persistence_check` â€” prepared, not yet dialed

## Harness correction after first call

The first caller ended without a spoken goodbye. Added a guard requiring the latest completed assistant utterance to contain a goodbye; a pending receptionist question or interrupted farewell does not permit hang-up. Four regression cases passed. The second call had already loaded its earlier code and nevertheless finished with a goodbye. Remaining calls use the guard. Transcript-based observations are provisional; no independent audio listening or backend access claimed.

## Saved recordings

The complete source folders remain in the local archive, excluded from Git. Selected copies are numbered in `artifacts/submission_calls/`; mapping is in [the submission call index](SUBMISSION_CALLS.md).

| Campaign | Source folder | Submission copy | Display | Seconds | Termination | Audio decoded |
| --- | --- | --- | --- | ---: | --- | --- |
| 1 | `call-015` | [Call 9](../artifacts/submission_calls/call-09/recording.mp3) | Call 14 | 88.6 | patient_end_call | True |
| 2 | `call-016` | Local archive only | Call 15 | 123.3 | patient_end_call | True |
| 3 | `call-017` | Local archive only; revised test is [Call 15](../artifacts/submission_calls/call-15/recording.mp3) | Call 16 | 205.4 | patient_end_call | True |
| 4 | `call-018` | [Call 10](../artifacts/submission_calls/call-10/recording.mp3) | Call 17 | 156.1 | patient_end_call | True |
| 5 | `call-019` | [Call 11](../artifacts/submission_calls/call-11/recording.mp3) | Call 18 | 119.0 | patient_end_call | True |
| 6 | `call-020` | [Call 12](../artifacts/submission_calls/call-12/recording.mp3) | Call 19 | 98.4 | patient_end_call | True |
| 7 | `call-021` | [Call 13](../artifacts/submission_calls/call-13/recording.mp3) | Call 20 | 171.9 | patient_end_call | True |
| 8 | `call-022` | [Call 14](../artifacts/submission_calls/call-14/recording.mp3) | Call 21 | 79.8 | patient_end_call | True |

All eight processes exited successfully and all recordings passed decode/energy checks. This is not human listening verification. Transcripts are saved live text, not independent offline ASR; timestamp estimates and quotations need audio confirmation. Do not count deterministic pattern matches as verified findings. The first call has limited contradiction timing and an abrupt simulator ending. Other greeting false starts and caller repetitions are harness observations, not target defects.

Account outcome: the identified Tuesday October 27 noon test appointment was cancelled with explicit consent in call-019; call-022 independently found no upcoming appointment and no original booking. No replacement appointment was created.

Validation: 22 scenario/prompt and end-call guard tests passed; Ruff passed for changed Python files. Formal submission audit remains a separate strict gate.
