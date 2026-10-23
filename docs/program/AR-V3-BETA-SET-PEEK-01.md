# AR-V3-BETA-SET-PEEK-01 — verified set without lease lock

`load_verified_retrieval_set` now has an explicit `lock_authority=False` mode. It checks the current Attempt without row locks before and after reading the exact verified set Blob, while retaining the locked behavior by default. The result carries a witness of the full confirmed set/catalogue/Blob pin row. `recheck_verified_retrieval_set_facts` compares that witness with the saved value and a fresh DB row inside a later caller-owned locked transaction. A missing or altered witness, changed custody or stale Attempt refuses. The existing 10 MB ceiling and exact Blob digest checks remain.

## Verification and handoff

- Task: [AR-V3-BETA-SET-PEEK-01](tasks/AR-V3-BETA-SET-PEEK-01.md), frozen from `2ffb03676d624f54d24f6ceb8aa7edc434e92692`.
- Changed paths: `src/auditmanager/findings/retrieval_set_input.py`, `src/auditmanager/findings/public.py`, `tests/integration/findings/test_w57a_retrieval_set_input_offline.py`, this note, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/findings/test_w57a_retrieval_set_input_offline.py tests/integration/runs/test_v3_execution_request.py -x --tb=short` — **24 passed**. Python compilation and `git diff --check` passed; handoff checks run after commit.
- New or changed contracts: none in `contracts/**`; the findings public boundary adds a DB witness recheck and the return value adds an optional witness field, preserving old construction.
- Known limits: the v3 request assembler and CITE preflight still enter locked authority reads before Blob I/O. No real delayed-S3/heartbeat test ran locally.
- Integration: use this mode only in a Session without prior authority row locks, then locked `require_current` plus `recheck_verified_retrieval_set_facts` after both source and set Blobs and before an external effect. It is not an effect authorization shortcut.
- Rollback: additive unserved mode; default remains locked and v3 executor guard remains.
- Forbidden hotspots: contracts, migration, root dependencies/lockfiles, composition root, active executor, transports, global styles and normative map/source/set data were untouched.
