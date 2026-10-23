# AR-V3-BETA-CITE-PREFLIGHT-01 — saved call to grounded beta review

`prepare_v3_cite_preflight` now joins the Run's saved text and verified set to one completed model call and its private reply Blob under a current Attempt. It rebuilds the exact v3 transport body using explicit generation settings, compares candidate/scope/set/body digests to the durable call, reads and verifies the reply, checks usage, status, presence of a live model report and measured cost, and runs the existing beta citation reviewer. The reported model name was already checked against the connection pin at dispatch; it can differ from the request's model pin ID. A truncated answer refuses before review. The group binding and completed call are read again after grounding.

The result is diagnostic only: it contains a provisional/context-only beta review and no publication candidate or expert decision. No provider call, database write or StageResult is made. The active v3 executor still refuses without the approved six-map/six-set pack and a CITE writer.

## Verification and handoff

- Task: [AR-V3-BETA-CITE-PREFLIGHT-01](tasks/AR-V3-BETA-CITE-PREFLIGHT-01.md), frozen from `717e904c20cf05ed438218af28260041930efb95`.
- Changed paths: `src/auditmanager/runs/v3_cite_preflight.py`, `tests/integration/runs/test_v3_cite_preflight.py`, this result, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_cite_preflight.py tests/integration/runs/test_v3_reply_custody.py tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_v3_corpus_citation_bridge.py -x --tb=short` — **54 passed**. `git diff --check` passed; task governance and exact changed-path check run at handoff.
- New or changed contracts: none in `contracts/**`; the unserved runs boundary adds `V3CitePreflight` and `prepare_v3_cite_preflight`.
- Known limits: saved source/set readers currently hold caller transaction locks across Blob reads. A slow Blob store can block the independent lease heartbeat. The CITE writer must be followed by a delayed-Blob/heartbeat check before serving v3. Real PostgreSQL and S3 acceptance was unavailable in this local lane. `ruff` is not installed in the local virtual environment; focused tests and `git diff --check` passed.
- Integration: use a dedicated, short CITE read transaction; later bind the same call and reply reference with the grounded review artifact and CITE StageResult under a fresh current-Attempt check. Keep context-only or mixed citations withheld and require expert edition/number checks.
- Rollback: unserved read-only bridge can be removed without migration.
- Forbidden hotspots: contracts, migrations, root dependencies/lockfiles, composition root, active executor, transports, global styles and normative corpus/maps/sets were not changed.
