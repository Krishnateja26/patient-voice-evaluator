# Selected submission calls

The submission bundle contains 18 numbered, separate call folders under
`artifacts/submission_calls/`. This curated set follows the user's selection:
keep one best representative of the repeated first-time-patient calls, retain
the requested distinct appointment, insurance, refill, identity, cancellation
and reminder cases, and keep both sides of the final cancellation follow-up.
The full 33-folder archive stays locally under `artifacts/calls/`; it is not
deleted or modified by this selection.

| Submission call | Source archive folder | Scenario / focus | Review note |
| --- | --- | --- | --- |
| Call 1 | `call-0dd03a48a3804eb9bb18758a1b8f37db` | New patient, first-time appointment | User selected the recording ending `37db` as the clearest of four near-duplicates. The calls ending `1477`, plus `call-004` and `call-007`, are not duplicated into this submission set. |
| Call 2 | `call-005` | New-patient setup | Clearer acknowledgement/setup comparison; not a confirmed defect. |
| Call 3 | `call-008` | New patient with caller/contact-number mismatch | Useful identity/contact clarification probe; not a controlled number-change test. |
| Call 4 | `call-009` | Registered patient, multiple booking dates | User rated the conversation well. No explicit SMS promise appears in the transcript. |
| Call 5 | `call-011` | Appointment availability and repetition | User-identified repeated Thursday availability; audio should support any final quoted wording. |
| Call 6 | `call-012` | Insurance questions | Positive example; no target bug established. |
| Call 7 | `call-013` | Medication refill and follow-up | Positive handling. A spoken staff follow-up does not independently prove ticket creation or staff notification. |
| Call 8 | `call-014` | Reschedule inquiry and requested text | User reports the explicitly requested confirmation text arrived. No successful reschedule was completed. |
| Call 9 | `call-015` | Contradictory DOB year | User raised an identity-verification concern. The planned retest was not made; retain as a limited observation. |
| Call 10 | `call-018` | Conflicting day/date while booking | Retained as a distinct calendar clarification case; do not claim a wrong-date booking from this inquiry. |
| Call 11 | `call-019` | Appointment cancellation and notification | User reports no cancellation text. Treat this as a notification improvement request, not proof cancellation failed. |
| Call 12 | `call-020` | Contact-number change | Retained at the user's request; the exchange was considered less useful and does not establish a successful number change. |
| Call 13 | `call-021` | Medication case reference | User corroborated that the receptionist gave a case ID, then said none existed. Backend request status remains unverified. |
| Call 14 | `call-022` | Appointment cancellation persistence | Original call retained; see Call 18 for the later read-only follow-up. |
| Call 15 | `call-027` | Firm request for Dr Jennifer | User says Jennifer is not a real doctor in the intended roster. The receptionist did not clearly establish whether Jennifer was listed. Historical direct-OpenAI patient simulator; user found this run less natural and slower. |
| Call 16 | `call-028` | Appointment reminder options | User found the explanation acceptable. Actual reminder scheduling or future delivery was not independently verified. Historical direct-OpenAI patient simulator. |
| Call 17 | `call-029` | Sister requests cancellation without authorization | Positive privacy boundary: the receptionist refused despite the same phone and correct DOB. This is a cancellation probe, not the originally planned sister-booking probe. Historical direct-OpenAI patient simulator. |
| Call 18 | `call-030` | Follow-up on appointment state and cancellation record | Kept with original Call 14 to show the later state check. The appointment remained active after Call 17's refusal; this does not test an unknown successful cancellation. Historical direct-OpenAI patient simulator. |

The user asked to omit the roughly 50-second `call-010`; it is not included.
Calls 027–030 were recorded during the temporary direct OpenAI STT/LLM/TTS
experiment and remain clearly identified as historical. The current code has
returned to LiveKit Inference. See [user review](USER_REVIEW.md),
[bug report](../BUG_REPORT.md), and [campaign notes](REVISED_CALL_CAMPAIGN.md)
for caveats. Do not treat user observations, transcripts, or automatic scores
as independent proof of clinic policy or backend actions.
