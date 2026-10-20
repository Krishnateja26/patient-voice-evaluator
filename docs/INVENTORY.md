# Project contents

- `src/voice_evaluator/` contains the LiveKit patient simulator, fixed-destination SIP call flow, local recorder, transcripts, evaluators and compliance checks.
- `scenarios/` contains the complete authored scenario library. Scenarios are preserved even when a corresponding call is not in the submission bundle.
- `artifacts/calls/` is the full local call archive. It stays on this computer and is excluded from Git.
- `artifacts/submission_calls/` contains 18 numbered, selected call folders. Each selected call includes an MP3 and transcript plus available scenario and evaluation evidence.
- `docs/`, `prompts/` and `tests/` contain setup, architecture, campaign and review notes, simulator prompts, and automated checks.

The project uses local recording storage and a single call command. It does not require S3, a separate recording worker, or a public tunnel. See [architecture](../ARCHITECTURE.md), [setup](SERVICE_SETUP.md), and [submission call selection](SUBMISSION_CALLS.md).
