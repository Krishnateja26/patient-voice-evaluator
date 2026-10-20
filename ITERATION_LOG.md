# How I built and refined the caller

I used an AI coding assistant to help implement and debug the project. I chose the test cases, listened to the calls, and decided which observations were worth keeping. This is my concise record of the changes that mattered to the calls.

## Making calls and saving evidence

I built the caller in Python with LiveKit Agents and separate speech recognition, text response, and speech generation. I connected my Twilio number through an outbound SIP trunk configured in LiveKit. I moved the recording flow to the local call command so each run would save audio, transcript, metadata, and evaluation together. I kept the setup local instead of adding S3 or a separate recording worker.

A setup attempt exposed a credentials issue before the phone call started: LiveKit Inference was not receiving the credentials loaded from my .env file. I changed the model constructors to pass the existing LiveKit project credentials directly and checked the fix without placing another call.

## Changes I made after listening

- When I heard the simulated patient check in while the receptionist was still looking something up, I changed the patient prompt to wait through announced pauses and avoid answering its own check-in.
- I wanted to know whether appointment information carried across calls, so I added read-only follow-ups that ask about an appointment without first giving its date. The saved calls showed the previously booked appointment could be retrieved.
- I heard the receptionist repeat substantially the same Thursday availability without being asked. I recorded it as a candidate conversational issue and added a distinct follow-up scenario for an any-doctor Friday search. I did not make another call for that follow-up.
- I broadened the scenarios to cover insurance timing, refill boundaries, identity checks, appointment reminders, and cancellation authorization rather than repeating one appointment flow.
- I heard a specific medication case reference given and then withdrawn in the same conversation. I kept the audio and transcript reference, while leaving backend request status unverified.
- I found the Dr Jennifer caller too repetitive and the receptionist did not clearly establish whether the requested provider was listed. I kept the limitation in the notes rather than claiming the clinic roster was independently checked.

## The temporary OpenAI caller experiment

When LiveKit Inference credits ran out, I used a temporary direct-OpenAI caller pipeline for source folders call-027 through call-030 (old display labels Calls 25–28; selected Calls 15–18). It changed speech transcription, speech generation, and turn handling; GPT-4.1 mini remained the text model. I heard a different caller voice and more delay. Since I did not record a comparable per-stage benchmark, I cannot attribute the delay to one component. I restored the LiveKit Inference caller pipeline and kept those four recordings labeled as historical.

## What I still need to verify

The selected bundle has 18 MP3 recordings and supporting evidence. Automated checks confirm the audio files decode and contain energy, but the metadata currently marks none as complete or human-verified. My listening notes are useful, but they are not a substitute for the formal review records or a transcript check against each recording. I stopped live calls and am finishing documentation and review only.
