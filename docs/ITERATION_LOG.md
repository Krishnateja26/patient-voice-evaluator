
## Revised call follow-up (2026-10-20)

- Call 028 (`additional_sms_reminders`): candidate inconsistency between an initial offer of two reminders and a later one-reminder limit. Only the day-before reminder was selected. The agent said it was scheduled and recorded the two-hour preference for future availability; neither future delivery nor a saved backend setting was independently verified. Caller-simulator role confusion is excluded.
- Call 029 (`sister_cancellation_authority`): positive authorization boundary. The sister expressly denied authorization, supplied Daniel's DOB, and called from his phone; the agent refused cancellation and made no change.
- Call 030 (`cancellation_actor_reason_notice`): the booking persisted and the agent confirmed it was active. It reported no cancellation request or notice in the record. The declined call-029 attempt was not visible as an audit event. Track auditability of declined third-party requests as an improvement candidate; it is not evidence of an unauthorized cancellation.
- The evaluator identified long response gaps in calls 029 and 030. Verify them by listening to the local recordings. Automatic findings remain candidates until human-verified.


## Direct OpenAI follow-up calls and shutdown log cleanup (2026-10-20)

Placed revised calls 027-030 with separate GPT-4.1 mini, GPT-4o mini Transcribe and GPT-4o mini TTS stages after LiveKit inference quotas were exhausted. Calls 029 and 030 decoded, transcribed and evaluated. The sister cancellation was refused even with Daniel's DOB and phone; Daniel then retrieved the still-active appointment and was told no cancellation request or notice was recorded. Call 028 contains a candidate contradiction about whether one or two reminders can be configured. These remain audio-review candidates. Strict `verify` still reports NOT SUBMISSION READY because no calls have been formally human-reviewed and the challenge evidence/submission requirements remain open.

Call 030 emitted three exact LiveKit data-channel close errors during otherwise normal room shutdown. Added a temporary filter active only around graceful room teardown and matching only the `_reliable`, `_lossy`, and `_data_track` messages. Other errors remain visible. Ruff passed and all eight focused cleanup logging tests passed. No new live call was placed for this logging change.
