# Voice Agent Evaluator

I built this Python patient caller to test a phone-based assistant through realistic conversations. It uses LiveKit Agents with separate speech-to-text, text LLM, and text-to-speech stages, records both sides locally, and saves evidence for review. The selected, numbered calls are in `artifacts/submission_calls/`.

## Set up once

Requirements: Windows PowerShell, Python 3.11 or newer, a LiveKit Cloud project, and one outbound SIP trunk connected to a caller number you control. See [service setup](docs/SERVICE_SETUP.md) for the short LiveKit and Twilio steps.

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
Copy-Item .env.example .env
```

Edit `.env` and fill in the six required LiveKit and phone settings. Keep the file private. Do not put API keys in chat or commit `.env`.

## Run

List scenarios, then start one only when you intend to place a real call:

```powershell
voice-evaluator scenarios
voice-evaluator call new_patient_record_intake --execute
```

The generic one-command form is `voice-evaluator call --execute`. It starts the local patient, calls the configured fixed assessment destination, records both room audio tracks locally, and saves the MP3, transcript, metadata and evaluation in a numbered folder under `artifacts/calls/`.

The assessment project is already in its no-more-calls documentation and review phase. The command remains documented for reproducibility; do not use it unless you intentionally resume live testing.

## Current live-call models

The patient simulator uses LiveKit Inference with the LiveKit project credentials:

- STT: Deepgram Nova-3
- Text LLM: GPT-4.1 mini through LiveKit Inference
- TTS: Cartesia Sonic-3
- Turn handling: LiveKit turn detection, dynamic endpointing and adaptive interruption handling

These are separate pipeline stages. The `openai/gpt-4.1-mini` model name is a LiveKit Inference model identifier; live calls do not use a direct OpenAI API key. `OPENAI_API_KEY` is optional and used only by post-call audio transcription or semantic evaluation. Leave it blank to use the saved live transcript and local heuristic evaluation.

Calls 027–030 came from a temporary direct-OpenAI experiment. I found the simulated caller sounded less natural and the conversations felt slower. That experiment changed the caller's speech recognition, voice, and turn handling, so I keep those calls clearly marked as historical and avoid attributing the difference to the receptionist alone. The current code and `.env.example` use the LiveKit Inference setup I preferred.

## Project notes

- [Architecture](ARCHITECTURE.md)
- [Environment variables](docs/ENVIRONMENT.md)
- [Scenarios](docs/SCENARIOS.md)
- [Call plan and coverage](docs/CALL_PLAN.md)
- [Selected submission calls](docs/SUBMISSION_CALLS.md)
- [Recording shortlist and review notes](docs/RECORDING_SHORTLIST.md)
- [Bug report and user observations](BUG_REPORT.md)
- [User review and scenario fidelity](docs/USER_REVIEW.md)
- [Campaign outcomes](docs/REVISED_CALL_CAMPAIGN.md)
- [Compliance checklist](docs/COMPLIANCE_CHECKLIST.md)
- [Current compliance review](COMPLIANCE_REVIEW.md)
- [Iteration history](ITERATION_LOG.md)
- [GitHub readiness](docs/GITHUB_READINESS.md)
 - [Project explanation and Loom notes](docs/PROJECT_AND_LOOM_GUIDE.md)

## Development checks

Install optional test tools and run local checks without making calls:

```powershell
pip install -e ".[dev]"
ruff check src tests
pytest
```

For local configuration checks, use `voice-evaluator preflight`. The strict `voice-evaluator verify` audit reports evidence and submission gaps; passing tests alone does not mean the assessment is ready to submit.

## GitHub handling

I keep the repository private because the selected recordings and call metadata contain personal test details. The code, documentation, and 18 selected call folders have been pushed to the private GitHub repository. I have not invited the reviewer or submitted the form; I will finish the videos and final review first. Local credentials, caller configuration, caches, intermediate WAV files, and the unselected full archive stay out of the repository.
