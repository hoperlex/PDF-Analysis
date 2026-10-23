# AR-V3-BETA-CALL-READ-01 — completed AR v3 call reader

`JobRepository.completed_v3_call` reads exactly one canonical `model_call` and its completed `provider_call_effect` for a Run under a current Job Attempt. It verifies their same-Job ownership and matching provider, model, mode, request/response SHA, usage, connection revision and identity basis, plus the reply Blob identity recorded at call completion. A completed call from an earlier Attempt of the same Job can be consumed after recovery; no second dispatch is inferred. The result contains no prompt or answer text.

The reader does not grant citation authority on its own. CITE must rebuild the saved request and verified set under the current Attempt, compare candidate/scope/set/body SHA with this value, construct `V3ReplyExpectation`, verify the private Blob through `read_v3_reply`, then ground and publish a review artifact. The active v3 executor still refuses and no reviewed six-map pack is installed.

## Verification and handoff

- Task: [AR-V3-BETA-CALL-READ-01](tasks/AR-V3-BETA-CALL-READ-01.md), frozen from `6025bcc0784bfb76876c4d3233d1c755b1b9eac4`.
- Changed paths: `src/auditmanager/jobs/repository.py`, `src/auditmanager/jobs/public.py`, `tests/integration/jobs/test_v3_completed_call.py`, this result, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/jobs/test_v3_completed_call.py tests/integration/runs/test_v3_reply_custody.py tests/integration/runs/test_v3_provider_call.py tests/integration/runs/test_v3_execution_request.py -x --tb=short` — **65 passed**. The new task's governance findings are empty and `git diff --check` passed.
- New or changed contracts: none in `contracts/**`; public jobs value `V3CompletedCall` added, no migration.
- Known limit: SQL was checked through focused reader tests; local PostgreSQL is not running and available disk is low, so a real-DB acceptance check remains for CITE integration.
- Integration: compare returned hashes/pins to the rebuilt sealed request and use the saved reply ref; bind answer and review artifacts only under current Attempt authority.
- Rollback: read-only and unserved behind the existing v3 executor guard.
- Forbidden hotspots: contracts, migrations, root dependencies/lockfiles, composition root, active executor, global styles, transports and normative maps/source data were not changed.
