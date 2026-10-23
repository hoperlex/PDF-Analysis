# AR-V3-BETA-CITE-LEASE-01 — CITE reads Blobs before final lease fence

The unserved CITE preflight now reads the canonical completed call without row locks, builds the saved-source/set request in a provisional mode, verifies the private reply Blob and grounds the review. Only then does it lock the current group/Attempt, recheck the saved source and set DB witnesses, and reread the completed call under the lock. A changed call, stale Attempt or changed witness refuses before a successful StageResult. Normal request preparation and completed-call reads retain their locked defaults. The writer still rechecks call and group after review-artifact outbox readback.

## Verification and handoff

- Task: [AR-V3-BETA-CITE-LEASE-01](tasks/AR-V3-BETA-CITE-LEASE-01.md), frozen from `f475a179f35d51f6316a5f4694eab6f335b9395f`.
- Changed paths: `src/auditmanager/jobs/repository.py`, `src/auditmanager/runs/v3_execution_request.py`, `src/auditmanager/runs/v3_cite_preflight.py`, their three focused test files, this note, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Checks: focused completed-call/request/CITE writer suite **67 passed**; extended with provider/reply custody **94 passed**. Python compilation and `git diff --check` passed. Handoff follows commit.
- New or changed contracts: none in `contracts/**`; optional `lock_authority=False` for completed-call read and `defer_final_fence=True` for request preparation are unserved internal calls. `fence_v3_execution_request` performs the mandatory final witness check.
- Risks: no local PostgreSQL/S3 delayed-Blob heartbeat acceptance. A caller that holds a prior `require_current` lock before entering CITE preflight would still block the heartbeat; the current CITE writer commits its start event first. No approved six-set pack or served v3 execution exists.
- Integration: keep early call/request values provisional and let this preflight finish its final locked checks before review publication. Do not add an authority lock before its Blob phase. The CITE writer's post-outbox rechecks remain mandatory.
- Rollback: unserved behind the active v3 executor guard; no migration.
- Forbidden hotspots: contracts, migration head, root dependencies/lockfiles, composition root, active executor, provider transports, global styles and normative map/source/set data were untouched.
