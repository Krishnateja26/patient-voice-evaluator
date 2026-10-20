# GitHub readiness checklist

- [ ] Create a **private** repository with a neutral name such as `patient-voice-evaluator`.
- [ ] Upload the source, setup and review documentation, and curated call bundles in `artifacts/submission_calls/`.
- [ ] Keep the repository private. The selected audio and transcripts may contain the user's voice and test identity details.
- [ ] Do not invite `eng-challenge@prettygoodai.com` until the user confirms the required files and Loom links are uploaded.
- [ ] Upload the two Loom links when ready; the current project folder contains no videos.
- [ ] Confirm `.env`, local caller identity data, `.venv`, caches, the full local call archive, WAV intermediates and source attachments are excluded.
- [ ] Review the staged file list before committing and pushing.
- [ ] Run `ruff check src tests` and `pytest` locally. The full suite was not completed in the latest documented run.
- [ ] Review `COMPLIANCE_REVIEW.md`; the current local audit reports **NOT SUBMISSION READY** and must not be represented as a pass.
- [ ] After every upload is complete and the user says so, invite the reviewer and complete the assessment form with the private repository link and originating number.

The local repository is on `main` and has no remote. The curated submission package is staged locally; this checklist does not certify that a GitHub repository, video, reviewer access, or assessment form exists.
