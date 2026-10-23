# AR-V3-BETA-SETTINGS-REPLAY-01 — CITE replays saved generation settings

The completed AR v3 call reader now validates the exact generation-parameter shape in its matched effect and call JSON, and returns the saved token ceiling and effort. CITE reconstructs `V3GenerationSettings` from these canonical facts and compares the rebuilt provider-body SHA with the stored call. It no longer needs matching settings from the current worker process. The final locked call reread compares those settings again before a review StageResult can succeed.

## Verification and handoff

- Task: [AR-V3-BETA-SETTINGS-REPLAY-01](tasks/AR-V3-BETA-SETTINGS-REPLAY-01.md), frozen from `3bffe5eb8f21b53595737a82b2e116a2c7ef6e4f`.
- Changed paths: `src/auditmanager/jobs/repository.py`, `src/auditmanager/runs/v3_cite_preflight.py`, `src/auditmanager/runs/v3_cite_stage.py`, their three focused test files, this note, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Checks: focused completed-call/CITE suite **61 passed**; extended provider/request suite **89 passed**. Python compilation and `git diff --check` passed; handoff follows commit. Tests cover missing/extra/wrong generation fields and settings drift at the final call fence.
- New or changed contracts: none in `contracts/**`; the internal `V3CompletedCall` value now includes `max_output_tokens` and `effort`, and the unserved CITE APIs derive their settings from it.
- Risks: old experimental v3 calls with malformed parameter JSON refuse replay. This is intentional; no schema or migration changes. The API StageId reseal, served worker wiring, approved six-set pack and real PostgreSQL/S3 acceptance remain open.
- Integration: invoke CITE from the canonical completed call; do not pass process-local generation settings. Its request-body SHA remains the final byte-level drift check.
- Rollback: unserved behind the active v3 executor guard; no migration.
- Forbidden hotspots: contracts, migration head, root dependencies/lockfiles, composition root, active executor, transports, global styles and normative map/source/set data were untouched.
