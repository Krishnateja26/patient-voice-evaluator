# How I chose the recordings

I kept the full local call archive on my computer and selected 18 folders for the private GitHub bundle. I chose one clear example from the repeated first-time-patient calls and kept the different scheduling, insurance, refill, identity, reminder, and cancellation cases. The selection is documented in docs/SUBMISSION_CALLS.md; other local recordings remain untouched.

| Call or group | Why I kept it | What I cannot claim from it |
| --- | --- | --- |
| Calls ending 1477, 37db, plus call-004 and call-007 | These were near-duplicates. I chose 37db as the clearest representative. | They count as one baseline flow, not four different bugs. |
| Call 2 | It clearly acknowledged a first-time patient and explained setup. | It does not prove the clinic's full registration policy. |
| Call 3 | It raised a caller-ID versus supplied-number clarification question. | I did not run a controlled number-change test or prove an unauthorized disclosure. |
| Call 4 | I liked the appointment conversation overall. | I did not receive a booking text, but there was no promise in the transcript. |
| Call 5 | I heard the Thursday availability list repeated without a new request. | I did not state the intended week aloud, so this is not a proven wrong-week booking. |
| Call 6 | I thought the insurance answers and follow-ups were strong. | It is positive capability evidence, not a bug. |
| Call 7 | I thought the refill follow-up stayed within limits. | A spoken promise to document the request does not prove a ticket or staff notification. |
| Call 8 | I received a text after I explicitly requested one, and the receptionist kept my original slot. | It was not a completed reschedule and does not prove all bookings trigger texts. |
| Call 9 | It captures my concern about conflicting DOB years. | I had given the correct DOB earlier and did not complete the planned retest. |
| Call 13 | I heard a specific case ID given and then withdrawn. | It does not establish whether a backend request exists. |
| Calls 17 and 18 | Together they show my sister's cancellation request was refused and the appointment stayed active. | They do not test an unauthorized booking or unknown successful cancellation. |
| Source folders call-027 to call-030 (selected Calls 15–18) | They cover a firm provider request, reminder options, an unauthorized cancellation attempt, and a follow-up state check. | They used a different caller pipeline and sounded less natural to me, so the receptionist-side quality comparison is confounded. |

I excluded the short Call 10 from the earlier archive. Calls 027–030 were made during a temporary direct-OpenAI caller experiment; I keep them as historical records. I have not marked the calls formally human-verified. The saved user_observations notes preserve my listening feedback, while transcripts, timing summaries, and automatic evaluations remain separate evidence.
