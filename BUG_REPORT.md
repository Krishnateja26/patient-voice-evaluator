# What I noticed in the calls

These are my observations from listening to selected calls, alongside the saved transcripts. I use the audio as the source of truth. The local metadata still marks the calls as not formally human-verified, so I am keeping these as observed candidates until I complete the required review records. I also separate what the receptionist said from backend actions I could not verify.

## Repeated appointment options

**Evidence:** Submission Call 5, recording and transcript, around 01:27–02:14.

I heard the receptionist give Thursday availability and then repeat substantially the same options without me asking for them again. That made the conversation feel repetitive and could make it harder to keep track of the actual choices. I did not establish a wrong-week error: the caller did not say the intended week aloud. I also did not run the later any-doctor Friday follow-up.

## Conflicting medication case reference

**Evidence:** Submission Call 13, recording and transcript, around 01:55–02:14.

I heard the receptionist give a case ID and say staff could use it to find the request. When I asked whether to use the ID or my name, the receptionist said no case ID was on file. I would not know which reference to rely on. This supports an inconsistent spoken reference, but it does not prove whether the clinic received a medication request or created a staff ticket.

## Request for a doctor who may not be on the roster

**Evidence:** Submission Call 15, recording and transcript.

For this test I asked for Dr Jennifer, who was not on the roster I expected the receptionist to use. I found that the reply did not clearly verify the name or guide me to a useful alternative, while the simulated caller kept repeating the same demand. I have not independently checked the clinic's provider database, so I am recording this as a grounding and conversation-quality concern, not a confirmed roster defect. This call also used the temporary direct-OpenAI caller setup, which sounded less natural to me.

## Other things I want to track

- **New-patient intake:** Calls 1 and 2 show different acknowledgements of a first-time caller. I would prefer the receptionist to recognize the caller as new and explain the next step. The recordings do not establish the clinic's actual registration workflow.
- **Number mismatch:** Call 3 raises a useful question: if I give a callback number different from caller ID, the receptionist could ask which number to use. This was not a controlled phone-number change test.
- **Booking texts:** I did not receive a booking text after Call 4, but the transcript contains no promise to send one. I did receive a text after I explicitly requested one in Call 8. I do not have delivery logs, so I am tracking consistency as an improvement question rather than a verified bug.
- **Cancellation notices:** The receptionist refused my sister's cancellation request in Call 17, and the booking was still active in Call 18. I would like an alert or audit record when someone attempts a change, but these calls did not test an unauthorized successful cancellation.
- **Date-of-birth check:** In Call 9, I was concerned by the conflicting year read-back and the request for me to validate it. I wanted a retest, but I did not make one.
- **Medication follow-up:** In Call 7, the receptionist said the request would be documented for staff. I could not inspect the clinic's tools or records, so I cannot say whether a ticket or notification was actually created.

## Current status

I have not marked any candidate as formally verified in the review metadata. I keep the candidate, the relevant call, and the evidence limits visible rather than presenting an unverified backend action as fact.
