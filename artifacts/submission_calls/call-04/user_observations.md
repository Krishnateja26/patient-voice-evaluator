# User listening observations

**Call:** Call 8 · `registered_patient_first_appointment`  
**Review status:** The user said the call was good overall: the receptionist handled varied scheduling turns, checked multiple appointment options and booked one, and the registered identity was recognized. The user also flagged the caller-pacing issue below and said a text-message notification would have been preferable. The artifact's `human_verified` and `call_completed` fields are unchanged; the saved recording ends during the receptionist's post-booking instructions.

## Appointment text-message expectation

The user did not receive a text notification and would have preferred one. The saved transcript includes a spoken appointment confirmation, but contains no offer or promise of an SMS; the call artifacts have no SMS-sending or delivery evidence. Record this as an unverified product expectation, not a confirmed receptionist or notification-system bug. A future call can ask whether a text confirmation will be sent and record the answer; do not assume the practice supports SMS reminders.

The user also wants to test cross-call appointment memory before changing anything: first ask whether the just-booked appointment can be found under the same identity without giving its date. Call 8's spoken confirmation is evidence of what the receptionist said, not proof the booking was saved in the appointment system. The next scenario is read-only and will not cancel, reschedule, or make a duplicate booking.

## Caller pacing improvement

At about 02:04–02:09, the simulated patient says, “Hello? Are you still…” even though the receptionist had said “One moment” while checking availability. The receptionist then resumes with a clipped “your”; the patient says, “Yes, I'm here,” and repeats the request. The exchange sounds distracted because the patient checks in during a normal lookup pause and then answers its own check-in.

The call timeline shows the receptionist's “One moment” at about 02:00, followed by the clipped “The next week,” and an interrupted patient check-in. The original transcript is in `transcript.txt`; `live_transcript.json` preserves the turn interruption flags. Treat this as a simulated-caller naturalness issue, not a target receptionist bug.

**Change made:** The caller prompt now tells the patient to wait through announced lookups, only check in after at least eight seconds of genuine silence, and never answer its own check-in. The registered-patient scenario repeats the relevant lookup instruction.

**Follow-up:** Listen to the same scenario on the next authorized call to confirm the caller waits naturally. No follow-up call has been placed.
