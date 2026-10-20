# My last four calls

I kept these calls after restoring the live runtime. They are a small follow-up set, not four fully verified findings.

| Source folder | Scenario | What I heard or concluded |
| --- | --- | --- |
| call-026 | Failed Dr Jennifer attempt | The recording is about seven seconds and ends with a provider error. I kept it for history, but it is not a completed conversation. |
| call-027 | Dr Jennifer request | I asked for Dr Jennifer only. The receptionist said there were no openings and offered a staff follow-up, but did not clearly verify the provider name or guide me through alternatives. |
| call-028 | Reminder options | I thought the explanation was acceptable. I did not verify delivery or backend settings. |
| call-029 | Sister requests cancellation without authorization | My sister said I had not authorized the cancellation. The receptionist refused and made no change. |
| call-030 | Appointment-state follow-up | I was told the appointment remained active and no cancellation request or notice was recorded. |

Calls 029 and 030 show that the appointment remained active after the refused cancellation request. I did not test an unauthorized sister booking or a successful cancellation that I did not recognize. A log or alert for a refused third-party attempt would be useful, but I do not claim a security defect from this pair.

I heard Calls 027–030 as slower and less natural than earlier calls. During that period, I changed the simulated caller to a direct OpenAI speech-transcription and speech-generation setup while keeping GPT-4.1 mini for text responses. The turn detector also changed. That means the caller changed too; the difference cannot be blamed on the receptionist alone. I later restored the LiveKit Inference pipeline. The recordings keep their original provider metadata.

The automatic evaluation and transcript timing still need review against the audio. My metadata has not been marked formally human-verified.
