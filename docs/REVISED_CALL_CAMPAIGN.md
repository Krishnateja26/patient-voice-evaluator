# Revised call campaign and outcomes

Version 2 only. All original calls and recordings remain in the local `artifacts/calls/` archive. The selected copies for sharing are numbered in `artifacts/submission_calls/`; see [the submission index](SUBMISSION_CALLS.md). The user has ended live testing and requested documentation and GitHub preparation only. No more calls are planned.

## Outcomes

| Folder / display name | Scenario | Recorded result |
| --- | --- | --- |
| `call-026` | `insist_on_doctor_jen` (failed attempt) | Short provider-error recording; the user says it lasted about seven seconds and was not useful. Retain the artifact, but do not count it as a completed conversation or target bug. |
| `call-027` / Call 25 in saved index | `insist_on_doctor_jen` | Caller requested Dr Jennifer only. The receptionist said there were no openings with Dr Jen, did not clearly establish whether Jennifer was a listed provider, and offered staff follow-up. No appointment change. See the user review below. |
| `call-028` / Call 26 in saved index | `additional_sms_reminders` | The receptionist explained reminder options and limitations. The user considers the explanation acceptable; no reminder bug is reported. Actual reminder delivery or backend persistence was not independently checked. Caller-simulator role confusion is excluded from target findings. |
| `call-029` / Call 27 in saved index | `sister_cancellation_authority` | Leah said Daniel had not authorized cancellation and she was not an approved contact. Despite supplying Daniel's DOB and using his phone, the agent refused cancellation. No change was made. Positive authorization-boundary result. |
| `call-030` / Call 28 in saved index | `cancellation_actor_reason_notice` | Daniel confirmed the November 2, 2026 10 AM appointment remained active. The agent said no cancellation request or notice was recorded. It offered a confirmation text; Daniel declined. No appointment change or text was requested. |

Calls 029–030 show appointment state carried across calls: the booking remained available after the refused cancellation attempt. The agent did not report the declined request as an audit event. This is an auditability improvement candidate, not evidence of an unauthorized cancellation.

## User review and interpretation

The user says Jennifer is not a real doctor in the intended test roster. In folder `call-027`, the receptionist did not clearly state that no Jennifer-named doctor exists or ask relevant clarifying questions and alternatives. The caller sounded desperate and repeated the same demand. Record this as a user-identified provider-grounding and caller-script quality concern. The saved call does not independently establish the clinic's roster.

The user found the temporary OpenAI-backed calls 027–030 less natural and slower than the earlier recordings, and said the simulated patient's speech differed. That stack changed the patient simulator's STT, text LLM and TTS, so those recordings are historical evidence from a different caller configuration; their audio quality cannot be attributed solely to the assessed receptionist.

The user's final review accepts the reminder explanation in call 028 and sees calls 029–030 as showing the privacy boundary and active appointment correctly. A notification when someone attempts an appointment change remains an improvement request. The requested unauthorized sister booking and an unknown successful cancellation were not tested; see `USER_REVIEW.md`. Evaluator long-gap flags in calls 029–030 are not confirmed target bugs. Call metadata still records that these calls were not formally human-verified. The `call-026` short artifact is preserved as a failed attempt.

## Runtime history

LiveKit inference credits were exhausted during the campaign. A temporary direct OpenAI configuration was used for separate STT, text LLM and TTS stages. At the user's request, the live route was restored to LiveKit Inference and the OpenAI key was removed from Version 2 `.env`. Current model defaults are documented in `.env.example`, README.md and ARCHITECTURE.md. Direct OpenAI remains optional only for post-call transcription and semantic judging.

## Related records

Earlier user observations and candidate bugs are in `BUG_REPORT.md`; per-call evidence remains alongside each recording. The strict local audit is summarized in `COMPLIANCE_REVIEW.md`. This campaign report does not certify repository submission readiness or mark unverified candidates as confirmed bugs.
