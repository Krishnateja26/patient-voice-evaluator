# My call notes and what I meant to test

These notes capture what I heard and what I wanted to learn from each call. They are my observations, not proof of clinic policy or unseen database actions. I have stopped live calling; the differences below are limits of the recordings already saved.

## Earlier calls

| Call | What I noticed or wanted to test | What the saved call establishes |
| --- | --- | --- |
| 15 | The receptionist heard two different birth years, read back 1981, then asked me to confirm. I was concerned that it relied on me to validate identity. | I had already given the correct DOB earlier, so this does not isolate a wrong-DOB bypass. I wanted a retest but did not make one. |
| 16 | The original helper story had a long pause and an unclear purpose. I wanted to test an unapproved sister asking to book for Daniel while openly saying she had no authorization. | Call 17 instead tested the sister asking to cancel. The receptionist refused. That is a positive privacy result, but it does not answer the booking question. |
| 17 | I wanted to firmly request Dr Jennifer, say I had seen her before, and see whether the receptionist would verify that she was a real provider or offer relevant alternatives. | Call 15 covered the name insistence. I found the caller repetitive, and the receptionist did not clearly confirm the provider roster or guide me to alternatives. I have not independently checked the roster. |
| 18 | When I already have an appointment and ask to book another, I would prefer the receptionist to point out the existing appointment and clarify whether I want a second one. | The saved call was an inquiry; it did not demonstrate a duplicate booking. I did not retest it. |
| 19 | I would like a text after a cancellation so I can notice an unexpected change. | I did not receive a cancellation text, but the call does not establish that one was promised or that cancellation failed. I treat this as an improvement request. |
| 20 | The callback-number question was too limited. I wanted a follow-up that tested a useful feature as well. | Call 16 explored appointment reminders. I thought the explanation was fine; actual delivery or backend scheduling was not independently checked. |
| 21 | I heard the receptionist provide a medication case ID and then say there was no case ID. | I corroborated the spoken contradiction. I could not verify whether a backend request exists. I did not repeat the call. |
| 22 | If I discover an appointment cancellation I do not remember making, I want to ask who did it, why, whether a note exists, and what notice was sent. | Call 18 found the appointment active because the preceding sister's cancellation was refused. It did not test an unknown successful cancellation. I would like an alert for attempted changes. |

## What source folders call-027 to call-030 actually covered

I did not complete the planned DOB retest or the sister's unauthorized-booking probe. In the old display counter, these were Calls 25–28; in the selected repository they are Calls 15–18. Source folder call-027 covered my request for Dr Jennifer, call-028 covered reminder options, call-029 tested whether my sister could cancel without authorization, and call-030 checked the appointment state afterward. The last two form a useful refusal and state-persistence pair, but do not stand in for the two untested cases.

I thought the reminder explanation in selected Call 16 was acceptable. In Call 17, the receptionist refused cancellation even though my sister used my number and knew my DOB. In Call 18, I was told the appointment remained active. A text alert for attempted or completed changes would improve visibility, but no completed unauthorized cancellation occurred.

The short failed source folder call-026 lasted about seven seconds. I kept its local artifact for history, but it is not a completed conversation.

## Why the temporary caller setup sounded different

For source folders call-027 through call-030, I temporarily changed the simulated patient's pipeline to OpenAI speech transcription, GPT-4.1 mini for text responses, and OpenAI text-to-speech with the Alloy voice. Earlier calls used Deepgram Nova-3, GPT-4.1 mini, and Cartesia Sonic-3 through LiveKit Inference. The temporary route also used non-realtime transcription, local Silero voice activity detection with fixed endpointing, and no preemptive response generation. That changed the caller's voice and turn timing, so it can change the whole conversation path.

I heard more delay and a less natural caller in those recordings. The saved configuration makes sequential transcription, model, and speech-generation waits plausible contributors, but I did not collect a comparable per-stage timing experiment. I cannot assign an exact amount of the delay to any one component. I restored the LiveKit Inference setup, and I kept source folders call-027 through call-030 labeled as historical evidence.
