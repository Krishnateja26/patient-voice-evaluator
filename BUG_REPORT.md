# Bug report and user-reviewed observations

These findings combine the user's listening feedback with saved transcripts. The formal local audit still reports zero qualified findings because its human-verification records are incomplete. Treat the items below as user-reviewed candidates and improvements; verify the cited audio before making stronger claims about exact wording, timing, clinic policy, or backend actions.

## Candidate: repeated appointment availability

**Evidence:** [Submission Call 5 recording](artifacts/submission_calls/call-05/recording.mp3), [transcript](artifacts/submission_calls/call-05/transcript.txt), and [user notes](artifacts/submission_calls/call-05/user_observations.md), about 01:27–02:14.

The receptionist gave Thursday availability, then repeated substantially the same date/time options without a new request. The user listened and identified the repeat as unnecessary. This is the clearest conversational-quality candidate in the selected set. The previously intended same-week constraint was not stated aloud, so a wrong-week defect is not established. The proposed Friday/any-provider variant was not run again.

## Candidate: contradictory medication case reference

**Evidence:** [Submission Call 13 recording](artifacts/submission_calls/call-13/recording.mp3), [transcript](artifacts/submission_calls/call-13/transcript.txt), and [transcript review](artifacts/submission_calls/call-13/transcript_review.md), approximately 01:55–02:14.

The receptionist gave a specific case ID and said staff could use it to find the request. After the caller asked whether to use the ID or their name, the receptionist said no case ID was on file. The user listened and corroborated the contradiction. A caller could rely on an unusable reference and lose confidence in the stated follow-up status. The local audit still lacks a completed formal review record, and this exchange does not prove whether a staff request was created.

## Candidate: provider-name grounding

**Evidence:** [Submission Call 15 recording](artifacts/submission_calls/call-15/recording.mp3), [transcript](artifacts/submission_calls/call-15/transcript.txt), and [user notes](artifacts/submission_calls/call-15/user_observations.md).

The caller firmly requested Dr Jennifer, whom the user says is not a doctor in the intended test roster. The receptionist did not clearly establish whether a Jennifer-named provider was listed or guide the caller through a focused verification and alternatives. The user also found the caller too repetitive. The roster was not independently checked, and this call used the temporary direct-OpenAI patient simulator; its voice and latency differ from earlier calls. Treat it as a provider-grounding and caller-script improvement candidate, not a confirmed roster defect.

## Other user-reviewed observations

- **New-patient intake:** Submission Calls 1 and 2 provide a baseline and a clearer new-patient acknowledgement/setup comparison. The clinic's actual intake workflow is unknown, so the conversation does not establish that the receptionist should create a record or book directly.
- **Identity/contact mismatch:** Submission Call 3 suggests the receptionist could clarify which number to use when caller ID and a supplied number differ. It was not a controlled phone-change test and does not prove an unauthorized disclosure or successful number update.
- **Booking notifications:** Submission Call 4 has no explicit SMS promise in the transcript. The user reported no booking text for that call, while an explicitly requested confirmation text arrived in Call 8. This is inconsistent user-reported delivery, not a verified failure.
- **Cancellation security and visibility:** In Submission Call 17 the receptionist refused the sister's cancellation request despite the same phone and correct DOB. Call 18 showed the booking still active and no cancellation request or notice recorded. These are positive privacy/state results; an alert or audit record for a declined change request remains an improvement idea. No unknown successful cancellation was tested.
- **DOB confirmation:** Submission Call 9 contains the user's concern about conflicting birth years and asking the caller to validate a year. The user requested a retest, but it was not completed.
- **Refill follow-up:** Submission Call 7 contains a useful staff-review explanation. Spoken documentation does not independently verify a ticket, tool call, or notification.

## Verified target bugs

None are marked formally verified in the current compliance audit. See [compliance review](COMPLIANCE_REVIEW.md) and [selected call index](docs/SUBMISSION_CALLS.md). Do not count the excluded short call or duplicate first-time-patient recordings as additional findings.
