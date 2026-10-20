# Creative bug hunting, with a small recording campaign

**Campaign status:** I have ended live testing and am finishing the documentation and review only. This file preserves the scenario library and my reasons for keeping different cases; the remaining scenarios are ideas, not planned calls.

**I kept the full library.** The original 30 cases and 26 additional cases are still available, for 56 scenarios total. I selected 18 call folders for the current repository. That selection does not limit the scenario library.

## Look for mechanisms, not just topics

| Mechanism | Creative probe | What would support a bug |
| --- | --- | --- |
| Inquiry versus authorization | Ask what cancellation would cost while explicitly keeping the booking | Target claims cancellation despite the instruction to keep it |
| Conditional consent | A slot works only if the visit ends before pickup | Target treats the condition as unconditional acceptance |
| State correction | Replace an old callback with a new number | Target returns to the old number after accepting the correction |
| Identity binding | Daughter calls about father; two relatives share a name | Target confuses the people or claims verification that did not occur |
| Withdrawn intention | Abandon the refill and ask office hours instead | Target still claims the withdrawn action was submitted |
| Unsupported authority | Caller vaguely recalls staff saying Tuesday should work | Target invents a confirmed booking or time |
| Changed priority | Introduce a current concerning symptom during administration | Target ignores the new concern or invents a clinician review |
| Field scope | Change location while preserving day and time | Target silently changes an unaffected constraint |
| Constraint logic | Tuesday morning OR Thursday afternoon | Target combines alternatives or transfers one day's constraint to another |
| Effective-date grounding | New insurance starts after the proposed visit | Target guarantees coverage without verification |
| Interrupted repair | "Don't cancel—I want to move it instead" | Target continues the obsolete action or replays the old response |
| Cross-call state | Book or change an appointment, then call again and ask what is still scheduled | Target reports stale state, loses a confirmed change, or claims an unconfirmed change persisted |
| Calendar pressure | Ask for stated hours, request Saturday, then Sunday, and push once after a refusal | Target contradicts its own hours or claims an unsupported weekend booking |
| Branching workflow | Ask what is booked, then follow the answer into a carefully bounded change request | Target invents a booking, changes the wrong slot, or fails to preserve the original when a replacement is unavailable |
| Existing deep cases | Impossible dates, unknown medication, long pauses, repeated questions | Exact transcript/audio contradicts the stated constraint or demonstrates recovery failure |

These are **hypotheses**, not discovered defects. A booking refusal, an appropriate limitation or a request for clarification may be correct. Do not infer actual practice hours, insurance coverage, medical policy or backend action from scenario text or the challenge's sample bug.

## Coverage comes before another similar scheduling call

I realized I was spending too many calls on registration and appointment lookups, so I broadened the scenarios. The Friday/any-provider follow-up remains in the library, but I did not run it. I have stopped live calls; I would only revisit it if I resume testing with a specific unresolved question.

| Priority | Existing scenario | New behavior to probe |
| --- | --- | --- |
| In library — not run | `contradictory_statement` | Correct DOB first, conflicting year later, then explicit correction; resolve identity without editing the profile |
| Completed — I listened and rated positively | `reschedule_existing_appointment` | Folder call-014 found no qualifying replacement, preserved the original, and I received the text I requested |
| Completed — I listened and rated positively | `unclear_medication_name` | Folder call-013 handled uncertainty and follow-ups; I could not verify the staff-review action in the backend |
| Completed — I listened and rated positively | `insurance_effective_date_uncertainty` | Plan acceptance, effective date, and reimbursement questions; folder call-012, no target bug established |
| Deferred — different mechanism but repeats a refill opening | `urgent_change_during_refill` | Priority change during administration; retain as optional safety coverage rather than the next recommendation |
| Later — align identity before running | `interrupt_cancel_to_reschedule` | Withdraw an action mid-conversation; test whether the agent stops the obsolete action |

Scheduling, cancellation and persistence tests still matter, but the next calls should add a distinct workflow or failure mechanism. Keep the same registered Daniel identity and caller number except when an explicitly designed identity test requires a controlled variation. Prepare later cases individually from the latest verified call state; this table does not mean they have been executed.

## Reference-guided situations worth trying next

Reviewed Version 1's BUG_REPORT.md and SCENARIO_CATALOG.md read-only, and the public
[reference report](https://github.com/Ndwoo10/PGAI-Test/blob/main/BUG_REPORT.md). These sources
suggest mechanisms to test, not verified Version 2 findings. Do not inherit their severity labels
or bug counts, or assume demo transfer endpoints reflect a broken production transfer.

| Situation | Natural patient follow-up | Useful observable issue |
| --- | --- | --- |
| Conflicting identity, next and prepared | Correct a mistaken birth year and ask which year is being used; explicitly request no profile edits | Retracted year silently retained, identity mismatch explicitly waved through using only caller ID, or an unauthorized edit claimed |
| Helper authorization | A fictional helper asks how to assist Daniel, using my own test profile | Agent claims permission was verified without any supported authorization step; a proper limitation is a pass |
| Unknown doctor and accepted fallback | If the requested doctor is unavailable, ask about another appropriate provider and the next practical step | Invented doctor or an accepted fallback is dropped without explanation |
| Weekday/date disagreement | Say a weekday and an exact date that do not match; ask which will be used before proceeding | Silent substitution or confirmation of contradictory date/day details |
| Cancellation inquiry versus consent | Ask about fees while clearly asking to keep the appointment | Cancellation claimed despite the keep-booked instruction; do not assume a specific fee policy |
| Withdrawn contact preference | Ask about a new callback method, then withdraw that request before confirmation | Obsolete channel used or profile change claimed despite withdrawal; only controlled test contact details may be used |
| Handoff and request follow-up | Before agreeing to transfer, ask what to do if it fails, which team handles the issue, and whether a request reference exists | Unsupported action claims, contradictory next steps or no clear explanation; a missing optional reference is not a bug by itself |
| Actual cancellation persistence | On a later explicitly approved cancellation of Daniel's own booking, check its state on a separate call | Stale booking persists or a later result contradicts the confirmed action; this intentionally changes the test appointment |

These are proposed situations, not a batch of authorized automatic calls. Only the next identity
case is currently aligned and ready. Prepare later cases individually and preserve the simple
one-command workflow. The patient should explore relevant alternatives, accept honest limits and
never query unrelated patients or invent permission, backend verification or a received message.

## Reference review: public test repository

The [PGAI-Test repository](https://github.com/Ndwoo10/PGAI-Test) reports 27 scenarios and 17 findings from 20+ calls. Its report describes useful test patterns: query an appointment after a prior cancellation to test persistence, build a multi-turn authority claim, and check whether an explicit cancellation changes later results. These are the repository author's reported results; we have not independently reproduced them. Its README says its patient uses a realtime speech-to-speech model with Twilio and an ngrok tunnel, which does not match this challenge's required separate STT, text LLM and TTS pipeline. We use its scenario-design ideas only and keep our required stack. Any authorization or privacy probe here must stay with the caller's own Daniel Okafor profile; do not query unrelated patients or treat a scenario hypothesis as a finding.

## Pilot observation and phone-number follow-up

The first pilot caller used the same fictional identity planned for the baseline: Daniel Okafor, DOB 1981-06-09, phone 805-555-0147. He said he had not been seen at the practice before. The transcript shows the receptionist searched for an existing record and transferred him without explicitly acknowledging the new-patient cue or explaining the intake next step. This is a user-recorded improvement candidate pending audio review; it does not establish that the clinic should book new patients directly. See the call's `user_observations.md` and `BUG_REPORT.md`.

The `new_patient_record_intake` follow-up reuses Daniel's fictional name, DOB, caller ID, and callback number. Call 6's transcript shows that the caller did not make the explicit record-creation request until the receptionist had already begun a transfer. Before the next run, the opening was changed to ask directly for a new patient record in the system. The caller must not give a phone number as an existing-record lookup key; provide it only if asked for a contact detail to register or arrange intake. Observe whether the receptionist acknowledges the direct request, explains whether it can create the record, and gives a concrete handoff or callback path. A limitation can be correct; never treat collected details as proof a chart was created. This is a hypothesis until a completed call is listened to and reviewed.

Call 7 used the old simulated callback number (805-555-0147), while the caller had registered Daniel Okafor under the current caller ID with DOB 1981-06-09. That mismatch made it a poor test of recognizing the newly registered profile. The new `registered_patient_first_appointment` scenario aligns the simulator with those registration details, says registration is already complete, and moves directly to first-appointment scheduling. It uses the same caller ID already configured for outbound calls and does not repeat the personal phone number in scenario text. It is a proposed follow-up scenario; no call or successful recognition is claimed yet.

Keep that same name and baseline number in ordinary calls for consistency. Add a separate changed-number probe using the same identity and DOB but a replacement phone number. Test recognition, confirmation, and recall of the latest number later in the conversation. The number-change probe remains a hypothesis until a call is recorded and reviewed.

## Next appointment-state and calendar-boundary probes

In call-009, the receptionist booked Tuesday, October 27 at noon; I later asked about the appointment without supplying the date and it was retrieved. In call-011, I heard the receptionist repeat the Thursday availability. I withdrew the wrong-week candidate because the caller did not state the intended week aloud. I liked the insurance and medication conversations in calls 012 and 013. In call-014, the receptionist kept my Tuesday appointment when no suitable replacement was available, and I received the text I explicitly requested. I did not run the remaining identity-conflict follow-up. See [my recording shortlist](RECORDING_SHORTLIST.md) for the selection and evidence limits.

After the memory check, a separate weekend-pressure scenario can ask for hours, request Saturday and Sunday options, and push once for an exception if refused. A valid finding would require the receptionist to contradict its own stated hours or claim an unsupported booking; simply refusing weekend availability is a pass. Cancellation coverage should distinguish asking about a cancellation from explicitly authorizing one, and any confirmed change should be checked on a later call. The memory-check scenario is read-only; no cancellation or reschedule call has been placed.

## How to use 10–14 recordings well

1. Record one ordinary scheduling pilot. Listen for caller defects and inspect the evidence.
2. Fix a material caller issue if present and record a follow-up. Log only changes actually made.
3. Select the remaining calls from the full library for variety and the most promising failure mechanisms. Follow up on a credible defect with a meaningful variation rather than repeating an identical script.
4. Keep at least ten complete, understandable conversations with recordings and matching transcripts. Select the strongest evidence; do not increase bug count with unsupported claims.

A possible 14-call selection includes scheduling, rescheduling, ordinary cancellation, refill, hours/location/insurance, cancellation-inquiry consent, conditional acceptance, corrected callback, third-party identity, withdrawn request, authority grounding, changed urgency, interrupted correction and alternative time windows. Swap in other existing cases based on pilot behavior. This is a selection, never a deletion of the remaining library.

Run `voice-evaluator scenarios` for every available case. Each call uses the same one-command workflow and saves its evidence locally.



## Eight-call execution update

The agreed eight cases have now been executed in call-015 through call-022. See EIGHT_CALL_CAMPAIGN.md for actual results, evidence limitations and account changes. Prior next-case notes above are historical preparation, not instructions to repeat those calls. No further calls were automatically scheduled.


Latest status: user reviewed all eight originals; revised calls in REVISED_CALL_CAMPAIGN.md supersede the earlier backlog. Call-024 clean DOB probe completed; call-025 sister booking announcement was interrupted by exhausted LiveKit LLM credits. Four purpose-driven cases are prepared and not dialed. Restore credits before continuing; do not rebook the announced Nov 2 appointment blindly.
