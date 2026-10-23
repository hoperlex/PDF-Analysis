# AR-V3-BETA-REQUEST-LEASE-01 — AR v3 request Blob reads before lease lock

`prepare_v3_execution_request` now checks the trusted group pins without row locks, reads the saved PDF text and verified retrieval-set Blobs through their explicit nonlocking modes, and constructs the exact v3 candidate and provider body before locking the Attempt. Its final resolver takes the existing locked authority fence, then the source and set DB witnesses are compared inside that short transaction. The default binding and corpus readers remain locked for existing callers. Provider intent still commits before dispatch in the separate journal operation.

This removes the request assembler's own lease-row lock across its two Blob reads. It does not yet fix CITE preflight, which currently reads `completed_v3_call` before rebuilding the request; that call takes the lock. The CITE writer's stage-start transaction commits before preflight, so the next change can reorder those reads without changing the active executor.

## Verification and handoff

- Task: [AR-V3-BETA-REQUEST-LEASE-01](tasks/AR-V3-BETA-REQUEST-LEASE-01.md), frozen from `4bda0b804f1da6a256ddc0bbd59c370358a1e96b`.
- Changed paths: `src/auditmanager/runs/v3_execution_binding.py`, `src/auditmanager/runs/v3_citations.py`, `src/auditmanager/runs/v3_execution_request.py`, `tests/integration/runs/test_v3_execution_request.py`, this note, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_v3_provider_call.py tests/integration/runs/test_v3_corpus_citation_bridge.py -x --tb=short` — **42 passed**; with saved-text/set reader suites, **85 passed**. Tests assert `peek → text Blob → set Blob → lock → both witnesses` and refuse changed witnesses. Python compilation and `git diff --check` passed; handoff runs after commit.
- New or changed contracts: none in `contracts/**`; explicit optional nonlocking mode added to the unserved group/corpus readers, locked defaults unchanged.
- Known limits: CITE completed-call ordering still acquires a lock before request Blobs. A live PostgreSQL/S3 delayed-Blob heartbeat test has not run locally. No approved six-set pack exists.
- Integration: call the assembler only in a transaction that has not already used `require_current`; the provider journal's subsequent locked effect gate and committed intent remain mandatory. Reorder CITE preflight to rebuild first, then read the completed call.
- Rollback: unserved behind the active v3 executor guard; no migration.
- Forbidden hotspots: contracts, migrations, root dependencies/lockfiles, composition root, active executor, transports, global styles and normative map/source/set data were untouched.
