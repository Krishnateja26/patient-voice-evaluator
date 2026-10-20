# GitHub readiness checklist

- [x] Create the **private** repository `Krishnateja26/patient-voice-evaluator`.
- [ ] Push the source, setup and review documentation, and curated call bundles in `artifacts/submission_calls/` from the user's authenticated Git session. The GitHub repository is currently empty.
- [ ] Keep the repository private. The selected audio and transcripts may contain the user's voice and test identity details.
- [ ] Do not invite `eng-challenge@prettygoodai.com` until the user confirms the required files and Loom links are uploaded.
- [ ] Upload the two Loom links when ready; the current project folder contains no videos.
- [x] Confirm `.env`, local caller identity data, `.venv`, caches, the full local call archive, WAV intermediates and source attachments are excluded from the tracked file list.
- [x] Review the committed file list: 362 tracked files, including 18 selected MP3 call folders (218 files total); no `.env` or full archive paths are tracked. Largest selected bundle file is under 1 MiB.
- [ ] Run `ruff check src tests` and `pytest` locally. The full suite was not completed in the latest documented run.
- [ ] Review `COMPLIANCE_REVIEW.md`; the current local audit reports **NOT SUBMISSION READY** and must not be represented as a pass.
- [ ] After every upload is complete and the user says so, invite the reviewer and complete the assessment form with the private repository link and originating number.

The local Version 2 repository is clean on `main` at commit `e76ab38`, with `origin` pointing to the private GitHub repository. The Codex environment cannot start Git Credential Manager because its helper process is blocked, so the push has not completed. Run `git push -u origin main` from an authenticated PowerShell session in this project folder. No collaborator has been invited. The current compliance audit still reports open submission requirements, including formal call review and both videos.
