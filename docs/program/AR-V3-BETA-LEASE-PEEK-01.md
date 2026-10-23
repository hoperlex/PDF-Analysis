# AR-V3-BETA-LEASE-PEEK-01 — nonlocking Attempt read for Blob preflight

`JobRepository.check_current_unlocked` performs one read-only SELECT over the Job, current Attempt and lease. It verifies the Run/Job/Attempt/lease identity, running states, nonreleased/unexpired lease and execution token without locking the lease row that the independent heartbeat updates. A stale or expired authority refuses; a missing or wrong token uses the existing execution-token error. The method makes no write and grants no authority for provider dispatch, outbox publication or StageResult binding: those still require the existing locked `require_current` after Blob reads.

## Verification and handoff

- Task: [AR-V3-BETA-LEASE-PEEK-01](tasks/AR-V3-BETA-LEASE-PEEK-01.md), frozen from `a559f9653212f56e2d9e5b659f5c55b392ae051f`.
- Changed paths: `src/auditmanager/jobs/repository.py`, `tests/integration/jobs/test_unlocked_attempt_read.py`, this note, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/jobs/test_unlocked_attempt_read.py tests/integration/jobs/test_v3_completed_call.py -x --tb=short` — **41 passed**. The test asserts a single SELECT without `FOR UPDATE` or `FOR SHARE`. Python compilation and `git diff --check` passed; handoff checks run after commit.
- New or changed contracts: none in `contracts/**`; an additive read-only method on the existing jobs boundary.
- Known limits: saved-text/set and CITE readers still call the locked gate before Blob I/O; this task does not close the slow-Blob lease hazard. No real PostgreSQL heartbeat test ran in the local lane.
- Integration: next task uses this early check only for Blob reads, then rechecks exact saved DB facts and calls locked `require_current` immediately before effect. Do not substitute this method for the final authority gate.
- Rollback: additive, unserved read method can be removed without migration.
- Forbidden hotspots: contracts, migration, root dependencies/lockfiles, composition root, active executor, transports, global styles and normative map/source/set data were untouched.
