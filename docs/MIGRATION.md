# Current Version 2 status

Version 1 remains read-only. Its scenario/evaluation logic was reused without copying old secrets, calls, bug claims or submission links as new evidence.

## Simple execution

`voice-evaluator call --execute` now connects a local LiveKit AgentSession, starts a receive-only local recorder, places the fixed-destination SIP call, saves both speaker channels and MP3, exports a transcript and writes an evaluation. There is no separate worker terminal, deployed agent, S3 account, Egress request, storage bucket or manual recording download. The cloud-storage dependency and policy template were removed.

The local recorder captures published audio from explicitly identified patient and target participants. Its reception-clock alignment is approximate, so timing-related bugs require listening. Optional OpenAI credentials enable independent post-call audio ASR and semantic analysis; without them, saved live text is clearly labeled for audio verification.

## Scenario scope

All 30 previous scenarios are preserved. Twelve new creative cases bring the library to 42. The goal of 10–14 strong submitted recordings is a selection budget, never a scenario-library cap. See CALL_PLAN.md for failure mechanisms and SCENARIOS.md for the complete list.

## Local verification

164 tests passed, including the local subscriber-to-MP3 route, speaker separation, missing/corrupted audio rejection, recording-before-dial safety, caller identity pinning, evidence hashes and the one-command workflow. These checks are synthetic/mocked. No Version 2 real calls have been made.

Next: fill the five account/phone fields in .env using SERVICE_SETUP.md, record one pilot, listen and improve the caller before selecting the remaining campaign. Complete private-repository, video and submission requirements after producing real evidence.
