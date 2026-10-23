# AR-V3-BETA-CITE-WRITER-01 — durable review-only CITE stage

`run_v3_cite_stage` now uses the profile-specific CITE declaration to record `stage.started`, rebuild the saved request/call/reply and grounded review under the current Attempt, and seal the beta review artifact. It checks prior StageResult rows before any Blob effect. The existing publication outbox commits an intent before the Blob write; exact readback, current Attempt, group, completed call and prior rows are checked again before `ar_v3_citation_review` StageResult and the Blob binding commit together. A verified input or grounding refusal records a failed StageResult with no review artifact. A stale Attempt, changed input after publication or unexpected storage failure never records success.

The writer is unserved. It does not call the model, publish a finding, produce a numeric conclusion, choose a Run terminal state or aggregate the six Runs. The active executor still refuses v3 and new groups still require the absent approved six-map/six-set pack.

## Verification and handoff

- Task: [AR-V3-BETA-CITE-WRITER-01](tasks/AR-V3-BETA-CITE-WRITER-01.md), frozen from `cc94c8e3a7e27096148ed45847d5b7a630faca7e`.
- Changed paths: `src/auditmanager/runs/v3_cite_stage.py`, `tests/integration/runs/test_v3_cite_stage.py`, this note, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_cite_stage.py tests/integration/runs/test_v3_cite_preflight.py tests/integration/runs/test_v3_review_artifact.py -x --tb=short` — **33 passed**. Python compilation and `git diff --check` passed; handoff checks run after commit.
- New or changed contracts: none; consumes the profile CITE extension from `AR-V3-BETA-CITE-STAGE-CONTRACT-01`.
- Known limits: the focused writer tests use fake transactions and publication; no local PostgreSQL/S3 acceptance was possible with the present stack and free space. The existing saved text/set readers hold Attempt locks during Blob reads, so a delayed Blob/heartbeat test and a lock-boundary fix are required before serving. No six-Run beta acceptance is claimed.
- Integration: activate only after the reviewed pack, saved-stage/Blob acceptance, lease safety and per-Run terminal/aggregate policy are in place. A later worker may consume a prior completed call of the same Job but must use its current Attempt for review publication. On unexpected failure, caller rolls back the open transaction; the outbox intent remains recoverable.
- Rollback: unserved writer can be removed without migration; do not erase durable intents or completed calls.
- Forbidden hotspots: contracts, migrations, root dependencies/lockfiles, composition root, active executor, provider transports, global styles and normative map/source/set data were untouched.
