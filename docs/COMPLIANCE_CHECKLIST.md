# Complete challenge checklist

Source: user-supplied Downloads PDF, all four pages read before this audit. The Desktop PDF is obsolete. Requirement IDs below are review identifiers, not text from the challenge.

The user additionally requests structured state, destination/caller guards, evidence verification, a real iteration log, and strict PASS / PASS WITH ISSUES / FAIL reviews. Those are implementation requirements from the user, not new mandatory clauses invented for the PDF. In particular, the PDF does not mandate a specific STT/LLM/TTS provider, a research framework, dual-channel audio, a fixed 45-second minimum, or ten distinct scenario IDs.

| ID | PDF page | Category | Requirement |
| --- | --- | --- | --- |
| C01 | 1 | HARD REQUIREMENT | Create a test account at pgai.us/athena to understand the patient experience. |
| C02 | 1 | PROHIBITION | Do not call the number on the account confirmation screen. |
| C03 | 1 | SAFETY REQUIREMENT | All assessment calls go only to +18054398008. |
| C04 | 1 | HARD REQUIREMENT | Simulate realistic patient scenarios and identify target bugs or quality issues. |
| C05 | 1 | DELIVERABLE | Record and transcribe conversations. |
| C06 | 1 | RECOMMENDATION / OPTIONAL IMPROVEMENT | Typical API/telephony cost is below $20; reimbursement is capped at $20 and requires receipts. |
| C07 | 2 | HARD REQUIREMENT | Use Python and LiveKit Agents in pipeline mode with separate STT, text LLM and TTS; provider choice is open. |
| C08 | 2 | PROHIBITION | Do not use realtime/speech-to-speech models, RealtimeModel plugins, Gemini Live or equivalent. |
| C09 | 2 | PROHIBITION | Do not use Vapi, Retell, Bland or hosted voice-agent platforms that replace the required pipeline. |
| C10 | 2 | DELIVERABLE | Include working Python code in the private GitHub repository. |
| C11 | 2 | DOCUMENTATION REQUIREMENT | README must explain setup and running; ideally one command after setup. |
| C12 | 2 | DOCUMENTATION REQUIREMENT | Formal architecture explanation is one to two paragraphs and explains design choices. |
| C13 | 2 | TESTING REQUIREMENT | Submit at least ten complete conversations, both sides recorded and transcribed; typically one to three minutes, not question-and-hang-up. |
| C14 | 2 | DELIVERABLE | Submit actual audio recordings in OGG or MP3 as well as transcripts. |
| C15 | 2 | DELIVERABLE | Bug report makes clear what happened, why it is a problem and where evidence can be found; example format is optional. |
| C16 | 2 | DELIVERABLE | Project walkthrough video is at most three minutes and communicates approach and reasoning. |
| C17 | 2 | PROHIBITION | Do not use Pretty Good AI or PGAI in Loom presentation language. |
| C18 | 2 | SUBMISSION REQUIREMENT | Use webcam/video and your own voice in the required videos. |
| C19 | 2 | DELIVERABLE | Provide a second screen recording showing genuine iterative AI prompting to debug/fix code and prompts used at each step. |
| C20 | 3 | CODE QUALITY REQUIREMENT | Keep code clean, readable and reasonably structured. |
| C21 | 3 | CODE QUALITY REQUIREMENT | Document needed API keys and environment variables; do not commit secrets. |
| C22 | 3 | DELIVERABLE | Include .env.example showing needed variables. |
| C23 | 3 | PROHIBITION | Do not use Pretty Good AI or PGAI in repository name, description or README title. |
| C24 | 3 | SUBMISSION REQUIREMENT | Keep the repository private after submission. |
| C25 | 3 | TESTING REQUIREMENT | Cover appointment scheduling, reschedule/cancel, refills, office hours/location/insurance and interruption/unclear/unusual cases. |
| C26 | 3 | RECOMMENDATION / OPTIONAL IMPROVEMENT | Expected project time is up to six hours; deeper useful analysis and creative edge cases can distinguish the submission. |
| C27 | 3 | EVALUATION PRIORITY | First review is call audio: coherent conversation is the highest priority and a rejection gate. |
| C28 | 3 | EVALUATION PRIORITY | Useful well-described bugs beat a long list of nitpicks. |
| C29 | 3 | HARD REQUIREMENT | Code must actually make real telephone calls. |
| C30 | 3 | DOCUMENTATION REQUIREMENT | Explain STT, LLM, TTS, turn detection, interruptions, phone connectivity, latency, alternatives and tradeoffs in architecture/Loom. |
| C31 | 3 | EVALUATION PRIORITY | Show improvements based on early call results. |
| C32 | 3 | EVALUATION PRIORITY | Follow all instructions rigorously and provide understandable code. |
| C33 | 4 | RECOMMENDATION / OPTIONAL IMPROVEMENT | Perfect code, overengineering, fancy diagrams, punctuation nitpicks, one-shot copy-paste and production infrastructure are not the goal. |
| C34 | 4 | VOICE QUALITY REQUIREMENT | Calls have natural conversational interaction and sensible turn taking except intentional barge-in tests. |
| C35 | 4 | VOICE QUALITY REQUIREMENT | Actively steer toward the scenario outcome while preserving realistic pacing and flow. |
| C36 | 4 | VOICE QUALITY REQUIREMENT | Audio is clear with minimal glitches, latency, unintended interruptions or awkward pauses; caller behaves like a real user. |
| C37 | 4 | SUBMISSION REQUIREMENT | Create a private GitHub repository and invite eng-challenge@prettygoodai.com as collaborator. |
| C38 | 4 | SUBMISSION REQUIREMENT | Complete the assessment submission form with private repository URL and reviewer access. |
| C39 | 4 | SUBMISSION REQUIREMENT | Include both videos; debugging video is viewable by anyone with the link. |
| C40 | 4 | SAFETY REQUIREMENT | Use one originating number for all calls and submit that exact number in E.164 format. |
| C41 | 4 | RECOMMENDATION / OPTIONAL IMPROVEMENT | No hard deadline; submissions are reviewed in arrival order. |
| C42 | 4 | PROHIBITION | Do not directly contact the team for support/clarification/feedback outside submission channels. |


Campaign implementation note (2026-10-19): C03/C40 fixed destination and caller guards unchanged; C04/C25/C28/C35 eight distinct adaptive scenarios executed sequentially; C05/C13/C14 recordings and transcripts retained; C15 findings remain evidence-limited; C36 goodbye guard added after observed simulator hang-up, four regression cases pass. See EIGHT_CALL_CAMPAIGN.md for final outcomes and remaining audio review.

Revised-user-review campaign: C04/C25/C35 six additional purposeful cases preserve the original library; C03/C40 fixed caller/destination maintained; C05/C13/C15 original and partial evidence preserved without false completion labels; C36 prompt answer-isolation fix tested. Call-025 provider_error reflects exhausted LLM credits. See REVISED_CALL_CAMPAIGN.md for prepared versus executed work.

Current runtime (2026-10-20): C07-C09 use separate LiveKit Inference STT, text LLM and TTS stages; direct OpenAI live routing was removed at the user's request after calls 027-030 sounded less natural and more latent. C03/C40 destination/caller guards remain. C11 setup and one-command execution remain documented. Optional OpenAI access is for post-call analysis only. Calls 027-030 retain their historical provider metadata.
