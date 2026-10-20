# Iteration log

Version 2 has completed live-call campaigns documented below. The entries distinguish user listening feedback, machine-generated evaluation and offline development; they do not claim independent review when none was completed.

## Evidence citation correction

- Problem: the inherited judge could accept a quote from another turn when its cited turn was wrong.
- Observation: source inspection and the inherited test explicitly allowed this repair.
- Change: require exact text on the cited stable turn ID, the correct speaker, valid timing and no invalid accompanying quote.
- Result: offline regression checks pass; useful real-call findings remain unverified.

## Artifact discovery and readiness correction

- Problem: Version 2 dispatch generated UUID call IDs while inherited loaders recognized only sequential IDs; an empty caller set passed the old single-caller check.
- Observation: live CLI ID construction and reporting loader expressions differed; old readiness used `len(caller_numbers) <= 1`.
- Change: recognize both ID forms, pin originating identity, and replace readiness with positive evidence qualification and explicit unresolved external requirements.
- Result: regression tests and audit results recorded in COMPLIANCE_REVIEW.md after verification. No new call count claimed.

## Recording/transcription integration

- Problem: private Egress storage was absent and the old transcription path assumed Twilio channel order.
- Observation: installed SDK and official docs support explicit storage and DUAL_CHANNEL_AGENT routing.
- Change: request private stereo MP3 Egress, retrieve its completed result, decode/validate, map left=patient and right=target, and hash-bind canonical transcripts.
- Result: synthetic audio and mocked service regression checks validate local behavior; actual SIP/Egress behavior still requires a pilot.

## Pilot entry to complete after a real call

Call ID:
Observation from listening:
Caller problem:
Change made:
Follow-up call ID:
Result from listening/metrics:
Remaining issue:

## Simplified local workflow and broader bug coverage

- Requirement: C11 (simple run), C13-C14 (local accepted recordings), C25 (creative scenario diversity), C33 (avoid unnecessary infrastructure), plus the user's explicit simplicity correction.
- Problem: S3/Egress added a storage account, credentials, manual downloads and a separate worker terminal; a recording-count target was incorrectly presented as narrowing the scenario scope.
- Change: replaced cloud recording with a local receive-only room subscriber, moved the complete call/evidence flow behind one command, removed S3 configuration/dependency and shortened the README/setup. Preserved all 30 prior scenarios and added 12 creative hypothesis cases.
- Alternative considered: manually downloading Cloud session recordings. Local subscription keeps automatic evidence generation in the same command and avoids a cloud-storage setup.
- Tradeoff: local receiver timing is approximate and must not be reported as remote PSTN timing. Audio and transcript findings still require listening.
- Result: 164 local regression tests pass. No live voice-quality gain or discovered bug is claimed before the pilot.


## Live pilot: standalone HTTP lifecycle fix (2026-10-18)

The first live pilot attempt exposed a missing shared HTTP session context in the standalone runner. LiveKit STT and adaptive interruption components raised a job-context error. The attempt was stopped and its room explicitly removed. The runner now wraps the entire call lifecycle in `http_context.open()`, including cleanup. A regression test verifies the HTTP session exists during a call and closes after failure. Three worker tests passed. A single pilot retry was then initiated; its phone leg became active and both roles produced transcript turns. Recording qualification and human audio review remain pending until the call is complete. No target-system bug is claimed from this runtime fix.

Pilot retry completed: call-41faece07bdc48ea976e189ee2bb1477. MP3 passed stereo decode/energy validation; transcript and heuristic evaluation saved. Target transferred the new-patient request to support; no confirmed bug or successful booking claimed. Human listening review remains required. LiveKit FFI destructor warnings appeared after saving and remain an unresolved shutdown issue.


### Test isolation incident and correction
Regression tests exposed import-time dotenv credential injection. The incomplete-configuration CLI test initiated unintended assessment calls: one stopped attempt and one completed weekend-request call (call-8c766a2cf11f48b88ce2922aa3da0fa1). These are not planned campaign evidence. Removed the redundant worker dotenv import and added an autouse fixture clearing credential environment variables and prohibiting real LiveKit API clients. The isolated full suite passed: 165 tests. Confirmed zero active local call rooms. FFI shutdown warnings remain unresolved. Both completed recordings need human review; strict audit remains NOT SUBMISSION READY, zero qualified calls. No further calls initiated.


### LiveKit Inference credential fix (2026-10-19)
The user's next-call attempt stopped while constructing the STT client: Settings had read credentials from `.env`, while LiveKit Inference looked for process environment variables. The failure occurred before SIP dialing. Updated STT, LLM, and TTS constructors to receive the existing LiveKit API key and secret directly. Ruff check passed. No call placed during this fix.


### Call 4 interruption detector warning (2026-10-19)
Call 4 (`call-004`) completed with an ended status, validated stereo MP3, and transcript. LiveKit logged that it could not create `AdaptiveInterruptionDetector`; SDK source shows the detector is created internally and reads LiveKit credentials from process environment. The STT/LLM/TTS credentials had been passed explicitly, but the detector did not receive them. The runner now exposes the saved credentials to LiveKit SDK components only for the duration of `run_call`, restoring previous process values afterward. Call 4 also logged slow Silero VAD warnings and late transcript-after-commit warnings; these may affect turn timing and should be checked during audio review. Shutdown data-channel and FFI destructor messages were emitted after the saved output. No further call initiated.


### Failed new-patient intake attempt (2026-10-19)

Attempt folder: `artifacts/calls/call-006` (`new_patient_record_intake`). LiveKit signaling and region discovery timed out; LiveKit Inference STT also timed out. The local recorder did not capture both speaker tracks, so no validated MP3 or completed transcript was produced (`audio_validated=false`, `call_completed=false`). This is an infrastructure/connectivity failure hypothesis, not evidence about the receptionist or the scenario. `preflight` only confirmed required settings were present; it did not test network connectivity. FFI handle assertions followed during shutdown. No retry initiated; retry only after LiveKit connectivity is stable.


### New-patient record intake follow-up (2026-10-19)

Completed recording: Call 6, internal folder `artifacts/calls/call-007`. The earlier `call-006` attempt had no valid recording and did not consume a campaign display number. The retry captured a validated stereo MP3 (128.547 seconds) and live transcript; human audio review is still pending and the scenario task is not marked complete. The transcript says the receptionist collected and read back Daniel's name, DOB and callback number, then offered a transfer to patient support to help him get started. As transfer began, the caller started to ask whether a new-patient record could be created; the test line then said goodbye. This needs audio review before judging whether the handoff adequately answered the request. The automatic evaluator raised one `next_step` candidate even though the transcript contains a patient-support transfer; treat it as an unverified evaluator candidate, not a confirmed target bug. FFI destructor warnings followed recording save.

Call-label correction: the recording was initially labeled Call 7 because the internal attempt folder ID included the failed `call-006`. Updated this recording's display label to Call 6 and changed future labeling to count validated completed recordings only. Added a regression test for failed-attempt numbering.


### Scenario clarification after Call 6 (2026-10-19)

The next `new_patient_record_intake` run now asks in the opening for the receptionist to create a new-patient record in the system. The simulated patient will not give the callback number as an existing-record lookup key; it will clarify that no number is on file and provide the number only if requested as a registration or intake contact. This isolates the record-creation question while retaining the same fictional identity and caller number. Scenario validation passed; no call was placed.


### Registered-patient follow-up scenario (2026-10-19)

Call 7's saved scenario snapshot used the older fictional callback number, while the user had registered Daniel Okafor with the current caller ID and DOB 1981-06-09. Added `registered_patient_first_appointment` to use the same configured caller ID, state that registration is complete, disclose DOB only if asked, and proceed directly to the first-appointment request. The scenario text does not repeat the personal phone number. Updated the library count and call plan. This is a proposed next test only; no call was placed and no recognition result is claimed.


### Call 8 caller-pacing correction (2026-10-19)

The user reviewed Call 8 and said the registered identity flow worked. At 02:04–02:09 the simulated patient asked “Hello? Are you still…” during the receptionist's announced appointment search, then answered “Yes, I'm here” and repeated the scheduling request. Timeline turns show an interruption and no clear question that called for that reply. Classified this as caller naturalness, not a receptionist defect. Updated the shared patient prompt and this scenario to wait through normal lookups, only check in after at least eight seconds of true silence, and never answer the caller's own check-in. Recorded the observation in the call folder and bug report. Scenario discovery passed, Ruff passed, and focused scenario/prompt tests passed (16); two temp-directory tests were deselected after the sandbox temp-folder restriction. No follow-up call placed.

The user then rated Call 8 as good overall: the receptionist handled varied requests, checked multiple appointment options and booked one. They did not receive a text notification and would have preferred one. The transcript shows a spoken booking confirmation but no SMS promise; there is no SMS delivery evidence in the call artifacts. Logged this as an unverified user expectation and a future question to ask after booking, not a confirmed bug. No message was sent and no call was placed.


### Cross-call appointment memory probe (2026-10-19)

The user wants to test whether the booking verbally confirmed on Call 8 is retrievable on a later call, separately from registration recognition. Added `registered_appointment_memory_check` as a read-only case: first ask for upcoming appointments without giving the date; only if none is found, provide the prior date once and ask for a recheck. It explicitly forbids canceling, rescheduling, or creating a duplicate appointment. A failed lookup is a persistence/lookup candidate, not proof until reviewed, because the prior transcript only proves what was said. The repo's public `PGAI-Test` was reviewed for cross-call persistence and multi-turn test ideas; reported findings were not independently verified, and its realtime patient architecture is not adopted. Scenario discovery passed, Ruff passed, and focused scenario/prompt tests passed (16); two temp-directory tests were deselected after the sandbox temp-folder restriction. No call placed.

### Cross-call reschedule authorization probe (2026-10-19)

The user reported that Call 9 retrieved the previously booked Tuesday, October 27, 2026 appointment at noon, confirming the booking persisted across calls. Added `cross_call_reschedule_authorization_check` as a harder follow-up: Daniel first asks what appointment is on file without supplying its date, then asks whether Thursday or Friday afternoon options can be checked while explicitly keeping the current booking. A tentative “that may work” must not count as consent. If the agent claims it changed the booking anyway, the caller immediately asks to restore Tuesday at noon or receives a concrete escalation step. This probes record recall, original-slot preservation, inquiry-versus-authorization, and correction recovery in one call. The scenario is a hypothesis, not a finding. No call placed.

### Call 10 review and next availability probe (2026-10-19)

The user listened to Call 10 and identified an unsolicited repeated Thursday-option list as a bug. The saved transcript contains nearly the same Thursday options at about 01:27–01:49 and 01:52–02:14. The user also wants the next caller to explicitly ask for Friday availability with any doctor; Call 10's caller did not make that provider-flexibility request, so the receptionist's doctor-specific Friday response is not a confirmed defect. The transcript records Thursday, October 22 for the requested week of the existing Tuesday, October 27 appointment, plus a broad October 23–November 23 Friday range; both are date-grounding candidates pending audio review. Added `cross_call_friday_any_provider_followup` to test date anchoring, repeated responses, and an explicit all-provider search while preserving the existing appointment. The user's report and evidence are documented in the Call 10 folder and `BUG_REPORT.md`. Scenario discovery passed, Ruff passed, and scenario/prompt tests passed (18). No follow-up call placed.

### Campaign diversity correction (2026-10-19)

The user rejected another near-duplicate appointment call and asked for broader hidden-bug coverage. Mapped this decision to C04/C25 (realistic scenarios and workflow diversity), C28 (useful evidence), and C35 (scenario steering). Deferred the Friday/any-provider reproduction without removing it or its recorded evidence. Updated the existing unused `urgent_change_during_refill` case to Daniel's registered name/DOB and the configured caller identity. It starts with a refill-process inquiry, introduces a current concerning symptom after the first administrative exchange, and checks whether the agent changes priority and explains escalation without fabricating medication or clinician actions. The next-call plan now rotates through this workflow, insurance timing, medication-name ambiguity, identity corrections, and interrupted intent. Later cases require identity alignment before execution. The library remains 47 scenarios; no new near-duplicate was added. Offline prompt generation succeeded and scenario/prompt tests passed (18). The required local audit remains NOT SUBMISSION READY because formal reviews and other submission evidence remain incomplete. No call placed.

### Correct the SDK shutdown-noise filter (2026-10-19)

The user supplied Call 10 output showing the repeated FfiHandle destructor AssertionError still printing after the recording was saved. The earlier filter incorrectly expected sys.unraisablehook.object to be a handle instance; Python actually supplies the FfiHandle.__del__ function. An offline test using the installed SDK destructor reproduced the failure before the change. Corrected the match to require that destructor function's module/qualified name, an empty AssertionError, the SDK dispose frame, and a false native dropped result. Filtering remains enabled only after the recording validates. The hook retains its matcher reference for process shutdown. Replaced the misleading instance-based tests with genuine SDK destructor capture and process-exit tests using a fake native drop result; no room, inference request, recording, or telephone call is created. All seven focused tests passed, covering quiet validated cleanup plus visible unvalidated cleanup, unexpected RuntimeError, a different native AssertionError and an unrelated destructor error. Ruff passed. Mapped to C11/C20/C31 (clear execution, readable code and fixing observed behavior); no stack or submission requirement changed. The local audit still reports NOT SUBMISSION READY due to outstanding formal evidence. No live call placed.

### Adaptive patient questions and different next workflow (2026-10-19)

The user asked for a different scenario whose patient explores natural alternatives rather than ending after the first narrow answer. Mapped the change to C04/C25/C28/C35. Updated the shared patient prompt to follow the actual answer, ask a relevant unresolved follow-up, and explore only scenario-permitted alternatives without inventing facts or repeating answered questions. An honest limitation with a practical next step remains a successful outcome. Reworked the existing insurance_effective_date_uncertainty case for Daniel's registered name/DOB and the same caller number. It starts with prospective Aetna PPO acceptance, then reveals an October 27 visit before the November 1 policy start; conditional follow-ups explore verified eligibility, self-pay/reimbursement, billing and any suggested later visit. At most two applicable unresolved follow-ups are used, rather than reading every branch. No policy update or appointment change is authorized. The next-call plan now selects insurance, with the refill-priority scenario retained for later. The library remains 47 cases. Offline prompt generation succeeded and all 18 scenario/prompt tests passed. The audit still reports NOT SUBMISSION READY due to outstanding formal evidence; no new result or target defect is claimed and no call was placed.

### Positive user review of the insurance conversation (2026-10-19)

The user described the latest recording as Call 12 (folder call-012; saved display label Call 11) and said it covered many questions, the patient asked very good questions, and the receptionist also answered well. Recorded this positive listening feedback in that call's user_observations.md. The transcript shows the patient probing acceptance versus verified eligibility, the effective-date mismatch, self-pay/reimbursement and the proper billing or insurer contact; the receptionist qualified its answers and distinguished those contacts. Preserve the adaptive follow-up approach when preparing different workflows. This is user-reported audio feedback, not an independent assistant listening review or a completed formal quality rubric. No new bug or backend verification is claimed. No call placed and no prompt change made from this positive feedback.

### Diverse recording shortlist and next medication case (2026-10-19)

The user requested a next call and useful bug recordings without repeated scenario types. Reviewed the validated-call transcripts and listening notes; created docs/RECORDING_SHORTLIST.md. Call 10/folder call-011 remains the strongest user-observed target issue (unsolicited repeated options). Call 7/folder call-008 is a distinct intake-friction candidate, not an established bug: it contains an explicit create-record request and repeated lookup, but transfer may be appropriate and caller/profile phone differences confound the number read-back. Similar intake recordings are grouped rather than counted as separate findings. Folder call-012 insurance and Call 8 booking are positive coverage examples, not extra bugs. The short weekend and memory recordings do not supply complete failure evidence.

Corrected an earlier overclaim: Call 10's same-week preference existed in private scenario text but was never spoken in the saved transcript. Offering October 22 therefore does not establish a wrong-week bug. Updated the bug report, call observations, future-week scenario notes and call plan; retained historical log entries with this explicit correction. Mapped the decision to C04/C25/C28/C35. Updated existing unclear_medication_name for Daniel's registered identity and same caller number, using uncertainty about a partial name, record-versus-suggestion clarification, and label/pharmacy/clinical alternatives. A tentative suggested name is not itself a bug, and the caller cannot falsely confirm it. Scenario library remains 47. Offline prompt export succeeded and all 18 scenario/prompt tests passed. The audit remains NOT SUBMISSION READY pending formal evidence. No live call placed.

### User campaign consolidation and conditional reschedule (2026-10-19)

The user rated folder call-013 positively and conditionally valued genuine ticket/staff notification. The transcript says the request was documented, not that a specific ticket tool or staff receipt was independently verified. Saved this feedback in call-013/user_observations.md and the final-report notes. Reworked the recording shortlist around the user's folder-based grouping: endings 1477 and 37db plus call-004 and call-007 are one first-time-intake scenario; call-005 is clearer new-patient setup acknowledgment; call-008 is identity/contact ambiguity with an explanation of the creation limit; call-009 explores and books dates; call-011 repeats availability; call-012 handles insurance; call-013 handles medication uncertainty. The phone-mismatch case was not a controlled changed-number experiment. The user now reports a booking text on an earlier occasion and no text for call-009, but an absent message without a promise is not yet a verified delivery bug. Preserved these distinctions in BUG_REPORT.md for final report drafting.

Mapped the next test to C04/C25/C28/C35. Updated existing reschedule_existing_appointment for Daniel's known original Tuesday, October 27 noon booking. The patient requests Wednesday, October 28 after 3 PM, then corrects the earliest time to 4:30 PM or later before consent, explores another appropriate doctor if needed, and authorizes only an exact qualifying replacement. It checks the old and new booking claims and asks about SMS. If no replacement qualifies or existing state is unresolved, retain the original. This is an actual reschedule if explicitly approved by the caller, not another availability-only query. A normal conversational correction is used; no timed overlap or successful interruption is claimed. Scenario library remains 47; offline prompt export succeeded and the calendar date was checked locally. Scenario/prompt tests passed (18); the local audit remains NOT SUBMISSION READY pending formal evidence. No live call placed.

### Call-014 requested text received and next priority-change test (2026-10-19)

The user rates folder call-014 positively and reports that the explicitly requested text confirmation arrived on the calling number, unlike an earlier booking occasion without a message. Its transcript shows no qualifying Wednesday replacement, including after a different-provider query. The caller retained Tuesday, October 27 at noon, asked for a text around 02:16 and was told one should arrive around 02:21. Recorded user-reported receipt in the call folder, bug report and selection notes. This is a successful fallback and requested-notification result, not a completed reschedule or proof that automatic SMS was required on the earlier booking. No independent inbox inspection is claimed.

Selected existing urgent_change_during_refill next for a different failure mechanism (C04/C25/C28/C35). The patient introduces a current concern after routine administration, asks one clarification only if a routine callback leaves the immediate next step unclear, and accepts a clear urgent route promptly without prolonging the call. No new medication, treatment or clinician action is invented. Updated the call plan and shortlist; library remains 47. Offline prompt export succeeded and all 18 scenario/prompt tests passed. The audit remains NOT SUBMISSION READY due to outstanding formal evidence. No call placed.

### Reference-guided diverse backlog and agreed identity case (2026-10-19)

The user accepted identity-conflict testing next and asked for additional useful situations from Version 1 and the GitHub examples. Read Version 1 BUG_REPORT.md and SCENARIO_CATALOG.md without modifying Version 1. Revisited the public Ndwoo10/PGAI-Test README and BUG_REPORT.md. Used their reported mechanisms as hypotheses only, not as verified Version 2 bugs or inherited severity/legal conclusions. Saved a backlog covering helper authorization using only the user's test profile, unsupported-doctor fallback, explicit weekday/date disagreement, cancellation inquiry versus consent, withdrawn contact preference, handoff/request recovery and explicitly authorized cancellation persistence. A demo transfer endpoint and a spoken ticket claim are not independent proof of failure or success.

Mapped to C04/C25/C28/C35. Updated existing contradictory_statement to Daniel's registered name/DOB and same calling number. It gives June 9, 1981, introduces 1982 once, then explicitly retracts it and says not to edit the record. Supported verification and a safe limitation are acceptable outcomes. The task is a read-only appointment inquiry, with no cancellation, reschedule or profile edit authorized. Updated the plan and shortlist to make this the next case and defer the refill opening. The library remains 47 scenarios. Offline prompt generation succeeded and all 18 scenario/prompt tests passed; the audit remains NOT SUBMISSION READY because formal evidence is incomplete. No live call placed.


### Eight authorized calls executed (2026-10-19)

Prepared the agreed eight cases, preserving the full library and adding three specific cases (50 total). Executed sequentially, same fixed destination and configured caller; saved call-015 through call-022 with MP3, transcripts and timelines. The known test appointment was cancelled only after explicit consent in call-019; read-only call-022 independently found no upcoming appointment and no original booking. Added a guarded end_call after call-015 ended without a spoken goodbye; four regression cases passed, 22 combined tests passed, Ruff passed. Calls 017-022 used the guard. No claim of listening verification. Strong new transcript candidate in call-021: specific case ID supplied then retracted as absent on file. Saved evidence and candidate in BUG_REPORT.md; no promotion to human verified, no assumption about actual staff/backend action. Full table and limitations in docs/EIGHT_CALL_CAMPAIGN.md.


### Revisions from user audio feedback

Preserved originals; recorded user feedback for call-015 through call-022. Added six purpose-driven scenarios (56 total) for five revised situations, including a linked cancellation attempt and audit. Initial call-023 DOB prompt let the caller leak the correct year; removed that year entirely from caller-visible prompt and retained it only in evaluator assertions. Clean call-024 failed lookup with wrong DOB despite known number and required verification. Call-025 sister with correct DOB and claimed verbal permission received booking announcement for Nov 2 at 10 AM despite no authorized-contact listing. LiveKit LLM quota exhausted and stopped the call; metadata provider_error, partial recording preserved. Four remaining calls prepared but not dialed; no duplicate booking retry. Calls 018/019/021 not repeated. User call-021 contradiction corroboration retained without pretending formal evidence review complete.


### Historical: temporary direct OpenAI live route

User supplied an existing key through V2 .env. Added explicit LLM_PROVIDER routing using LiveKit OpenAI plugin, preserving GPT-4.1 mini and the separate STT/TTS pipeline. Installed matching plugin 1.8.8, saved route openai, checked direct API access with a tiny text completion, and passed 26 focused plus 3 worker lifecycle tests. Provider/model now recorded in metadata. No secret printed. Strict verify still reports unfinished formal evidence, not submission readiness. Resuming the four prepared calls sequentially.

LLM-only recovery encountered a LiveKit STT 429 before a usable conversation in call-026; preserved as provider_error and audio invalid, not counted as a test. Switched separate STT/TTS to direct OpenAI with existing key, local Silero VAD, non-realtime transcription, and alloy voice. Tested both speech APIs with an in-memory synthetic sample; nine provider/worker tests passed. User informed of voice change before continuing. Retained caller number/destination and separate-model requirement. This route was later reverted at the user's request, as documented below.

### User-requested restoration and documentation (2026-10-20)

The user reported that the temporary OpenAI-backed patient simulator made calls 027–030 slower and less natural, and that the simulated caller sounded different from earlier recordings. The user also rated the Dr Jennifer test as weak: in the intended test roster Jennifer is not a doctor, yet the agent did not clearly explain that or guide the caller to relevant alternatives; the caller repeated the same demand. Recorded these as user observations and kept the recordings unchanged. The short failed `call-026` artifact remains preserved and is excluded from completed-call evidence.

Removed the direct OpenAI live routing and provider-selection settings from the application and restored LiveKit Inference STT, GPT-4.1 mini text LLM and Cartesia TTS defaults with LiveKit turn detection. Removed `OPENAI_API_KEY` from the local `.env`; the optional config field remains for post-call analysis only. Updated README, architecture, service setup, environment, call-campaign, shortlist and GitHub-readiness documentation. No calls were placed for this work. The user has said the campaign is complete and no more calls should be recorded.

Verification is local only: Ruff passes, and the restored LiveKit routing tests pass (4 tests). Broader worker/full-suite runs did not complete in this session, so no full-suite pass is claimed. `voice-evaluator verify` still reports NOT SUBMISSION READY with 0/10 qualified calls because formal audio reviews and required submission evidence are incomplete. The local Git repository is initialized with no remote, staged files, commit or upload.
