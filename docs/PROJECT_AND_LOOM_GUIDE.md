# My project and Loom notes

## How I describe the project

I built a Python voice caller that tests a phone-based assistant through realistic patient conversations. I give the caller a scenario, place a real outbound call, record both sides locally, and save the transcript and review evidence. I used the recordings to look for issues such as repeated appointment options, unclear identity checks, and inconsistent follow-up references. I used an AI coding assistant to help implement and debug parts of the tool; I chose the scenarios and made the final calls on what the recordings showed.

## What LiveKit does, and where Twilio fits

LiveKit is the real-time session and voice framework in this project. LiveKit Agents runs the caller session, connects the audio tracks, handles turn-taking and interruptions, and places the call through an outbound SIP trunk. LiveKit Inference provides the three separate live model stages: Deepgram Nova-3 converts the receptionist's speech to text, GPT-4.1 mini decides the simulated patient's next response, and Cartesia Sonic-3 speaks that response. The GPT model name is routed through LiveKit Inference; the live call does not use my direct OpenAI API key.

The phone connection is not all LiveKit. I reused my Twilio phone number and configured a Twilio Elastic SIP trunk, then connected it to the LiveKit outbound SIP trunk. Twilio supplies the telephone number and carrier connection; LiveKit runs the voice session and routes it through SIP. I keep the recordings on my computer, so the setup does not need S3 or a separate recording service.

## What is in each call folder

Each numbered folder under artifacts/submission_calls is a selected copy of one call. The folder number is the simple display name; the metadata and scenario files retain the original call and scenario identifiers. Some evaluation.md headings also retain the old display counter. I use docs/SUBMISSION_CALLS.md as the crosswalk between the new number, original folder, and scenario. A few review files exist only for calls where I wrote a specific note.

| File | What I use it for |
| --- | --- |
| recording.mp3 | The call audio. The patient and receptionist are stored on separate audio channels in the same MP3. I use this as the source of truth when checking what was actually said. |
| transcript.txt | A readable transcript for quickly finding the relevant exchange. I check quotes against the recording because transcription can mishear words or timing. |
| transcript.json | The structured transcript, including speaker labels and any available timing or confidence details. |
| live_transcript.json | Conversation text and turn information captured during the LiveKit session, including interruption and speech timing data when available. In this caller session, LiveKit can label the remote receptionist as “user”; the normalized transcript uses patient and agent labels. |
| scenario.json and scenario.yaml | The patient profile, opening line, facts the caller knows, conversation strategy, and intended test outcome. These are two formats of the same scenario snapshot, not two separate tests. |
| metadata.json | Call status, recording details, hashes, channel mapping, selected call name, and whether audio or human review has been completed. A saved or decoded recording is not automatically a completed, human-verified call. |
| timeline.jsonl | A chronological event log for the session, such as state changes, transcript events, speech events, and call completion. |
| timing_summary.json | SDK timing samples and percentiles for turn completion, LLM response, TTS start, and measured end-to-end processing. These are not a measurement of when audio first reached the remote phone. |
| evaluation.json | Machine-readable results from the local checks: scenario assertions, rule-based findings, warnings, and available metrics. It helps me triage calls; it is not a human verdict. |
| evaluation.md | A readable version of the evaluation results. I use it to locate candidate issues, then check the recording and my listening notes before reporting a finding. |
| user_observations.md | My own listening notes: what I noticed, what worked, and what I would improve. These notes distinguish my observation from facts that the recording or transcript cannot establish. |
| transcript_review.md | A focused review of a particular exchange. It says whether I checked the audio or only the transcript and records what still needs confirmation. |

Not every call folder contains every review file. The MP3, transcripts, scenario snapshot, metadata, event timeline, timing summary, and automatic evaluation form the usual evidence bundle. The evaluation files can flag a candidate, but I do not treat an automatic score or a spoken claim as proof of a backend action.

## A short walkthrough outline

This outline is for my own-voice project walkthrough. I should speak naturally, keep my webcam on, and stay within the three-minute limit.

1. **What I built:** “I built a Python caller that tests a phone assistant using patient scenarios. It records both sides and saves evidence so I can review what happened.”
2. **How a call works:** Show one scenario, then explain that LiveKit Agents manages the session and turn-taking, LiveKit Inference runs separate speech recognition, text response, and speech generation stages, and the Twilio-connected SIP trunk carries the phone call.
3. **What I learned:** Show one recording and its transcript. Point to a useful observed issue, such as the repeated appointment options or the inconsistent case reference, and explain why it matters. Be clear about which observations I confirmed by listening and which backend effects remain unknown.
4. **How I improved the tool:** Show one real code or prompt iteration and its actual test result. For the separate AI-debugging video, use the real prompts and changes from the working session rather than recreating or inventing a prompt history.
5. **Close with the limits:** Explain that automatic evaluation is a triage aid, recordings still need human review, and the project does not verify the clinic's internal database or staff actions.

## How I keep the story honest

The brief asks for the simulated caller to sound like a real person rather than a scripted benchmark. I describe what I built and why, without claiming it predates the assessment. I explain where AI helped with implementation and what remains unverified. My listening notes are in first person; machine-generated transcripts, event logs, and evaluation data stay neutral so their source remains clear.
