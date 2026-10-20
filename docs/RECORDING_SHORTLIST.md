# Recording selection and user review notes

The current GitHub bundle is curated separately in
[`SUBMISSION_CALLS.md`](SUBMISSION_CALLS.md): 18 numbered folders selected from
the complete local archive. This file preserves broader selection history and
review limits; the other local call folders remain on the workstation and are
excluded from Git.

Use folder IDs as stable references. The display counter is one lower after a failed attempt:
for example folder call-013 is display Call 12. The user's latest review refers to folder IDs.
These notes preserve user listening feedback and transcript evidence, not completed formal reviews.

| Recording/group | User assessment and distinct value | Reporting limit |
| --- | --- | --- |
| Folders ending 1477 and 37db, plus call-004 and call-007 | Four near-identical first-time/unregistered-patient flows. Select one representative for the baseline. | Count as one scenario, not four separate bugs or kinds of coverage. Choose the clearest complete audio after review. |
| call-005 | Explicitly identifies the caller as a new patient and offers help connecting to patient setup. | Useful improvement/comparison with the baseline intake group, not automatically a separate defect or a different workflow. |
| call-008 | Caller-ID/registered-name and different supplied-number case. User suggests asking which number to use; the receptionist eventually explains it cannot create the record. | It revealed a registered name before the caller identified themselves, but this is the user's test profile. The supplied number differed from actual caller ID; this was not a controlled number-change experiment. Report the observable identity/contact ambiguity, not a proven unauthorized disclosure or successful update. |
| call-009 | Explores multiple dates and books an appointment. User rates it positively overall. | User reports no booking text on this occasion but receiving one on another occasion. No SMS promise is in this saved transcript; missing delivery alone is not a verified notification bug. Caller check-in and post-booking cutoff remain recording-quality considerations. |
| call-011 | Strongest user-identified target issue: repeats the Thursday availability list without a request, about 01:27–02:14. | Do not count both repetitions as different bugs. The earlier wrong-week candidate is withdrawn because the intended same-week constraint was not spoken aloud. |
| call-012 | Insurance questions answered properly; adaptive patient follow-ups covered acceptance, effective date, reimbursement and the appropriate contact. | Positive capability/robustness evidence; no target bug established. |
| call-013 | Medication uncertainty handled consistently through multiple follow-ups. Receptionist says the request was documented for clinic review and no refill/change would occur until confirmation. User rates it positively. | A spoken documentation/follow-up claim does not prove a ticket, tool execution or staff notification. Verify through available staff/backend evidence before claiming successful action. No target bug established from the user review. |
| call-014 | Conditional reschedule inquiry: corrected earliest time, alternative-provider question, no suitable slot, original booking preserved. User reports the explicitly requested confirmation text arrived. | Positive fallback and user-reported SMS delivery, not a completed reschedule. The earlier absence of an automatic booking text is still not a verified notification bug. |

## Findings to retain for the final report

- Unsolicited availability repetition: user-identified issue in call-011.
- New-patient acknowledgment/intake friction: baseline improvement observation; call-005 shows clearer acknowledgment. Actual clinic intake limits remain unknown.
- Identity/contact mismatch in call-008: candidate for explicit number clarification. Do not treat fictional callback mismatch as proof the target chose the wrong real number.
- SMS consistency: the user reports a booking text on an earlier occasion and no text for call-009. A future explicit promise plus delivery check is needed to establish a notification defect.
- Medication action claims: document what was said in call-013, with ticket creation and staff notification unverified. The conditional success is valuable, but cannot yet be called verified tool use.

The short call-010 is excluded from selection at the user's request, irrespective of whether its
folder has been manually deleted. The short weekend call ends before a saved response to the
Sunday request and supplies no evidence of an out-of-hours booking defect. Failed attempts do
not add completed conversations. The retained library is broader than this selection.

## Eight-call campaign completed

Eight authorized calls were saved in call-015 through call-022; see EIGHT_CALL_CAMPAIGN.md. Prioritize call-021 for audio review of the specific-reference contradiction, call-019 plus call-022 as a cancellation/persistence pair, and call-016 for the helper authorization boundary. Call-018 is a calendar-clarification quality candidate, not evidence of a wrong-date booking. Call-015 has limited contradiction timing and an abrupt simulator ending; do not count it as a polished completed conversation without review. All eight recordings are preserved, but none has been newly marked human verified. No replacement appointment was booked after cancellation.


## User-directed revisions

Original call-015 through call-022 retained. Call-023 is a limited DOB attempt with caller drift; call-024 is the cleaner wrong-DOB verification example. Call-025 captures explicit non-listed sister booking acceptance but is interrupted by a provider quota error, so it is not a complete conversation for submission. The four revised attempts in folders call-027 through call-030 were completed using a temporary OpenAI-backed patient simulator. The user found this caller voice less natural and more latent than the earlier configuration. Keep those recordings as historical evidence, but assess them with that limitation in mind. Folder call-026 is a very short failed attempt and is not a completed conversation. The user has asked for no further calls. See REVISED_CALL_CAMPAIGN.md for outcomes and user review. Do not repeat the sister booking: the November 2 at 10 AM appointment was retrieved and remains active in call-030.
