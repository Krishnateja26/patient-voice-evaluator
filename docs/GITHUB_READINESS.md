# GitHub readiness checklist

- [x] Create the **private** repository `Krishnateja26/patient-voice-evaluator`.
- [ ] Push the source, setup and review documentation, and curated call bundles in `artifacts/submission_calls/` from the user's authenticated Git session.
- [ ] Keep the repository private. The selected audio and transcripts may contain the user's voice and test identity details.
- [ ] Do not invite `eng-challenge@prettygoodai.com` until the user confirms the required files and Loom links are uploaded.
- [ ] Upload the two Loom links when ready; the current project folder contains no videos.
- [ ] Confirm `.env`, local caller identity data, `.venv`, caches, the full local call archive, WAV intermediates and source attachments are excluded.
- [ ] Review the staged file list before committing and pushing.
- [ ] Run `ruff check src tests` and `pytest` locally. The full suite was not completed in the latest documented run.
- [ ] Review `COMPLIANCE_REVIEW.md`; the current local audit reports **NOT SUBMISSION READY** and must not be represented as a pass.
- [ ] After every upload is complete and the user says so, invite the reviewer and complete the assessment form with the private repository link and originating number.

The local repository is on `main` at commit `0ec08b0` with `origin` pointing to the private GitHub repository. GitHub Credential Manager cannot access the saved credential in this environment, so the push has not completed. The user can run `git push -u origin main` from their normal authenticated PowerShell session. No collaborator has been invited. The current compliance audit still reports open submission requirements.
