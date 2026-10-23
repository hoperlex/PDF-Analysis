# AR-V3-BETA-SOURCE-PEEK-01 — saved text without lease lock

`load_saved_reference_text` now has an explicit `lock_authority=False` mode for the v3 request assembler. It checks the current Attempt without row locks before and after reading the saved text Blob, while preserving the existing locked behavior by default. The result carries the source StageResult and project witness. After all Blob reads, `recheck_saved_reference_text_facts` compares the Run, Version, page count and exact source stage inside the caller's final locked transaction. A missing witness or changed fact refuses; the nonlocking read alone grants no provider or publication authority.

## Verification and handoff

- Task: [AR-V3-BETA-SOURCE-PEEK-01](tasks/AR-V3-BETA-SOURCE-PEEK-01.md), frozen from `798f05ff5b307178745d45d0e962418ba3e52f57`.
- Changed paths: `src/auditmanager/runs/reference_text_input.py`, `tests/integration/runs/test_reference_text_input_offline.py`, this note, task file and `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`.
- Focused checks: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_reference_text_input_offline.py tests/integration/runs/test_v3_execution_request.py -x --tb=short` — **39 passed**. Python compilation and `git diff --check` passed; task handoff runs after commit.
- New or changed contracts: none in `contracts/**`; the saved-text return value adds optional DB witness fields, leaving existing three-field construction valid.
- Known limits: verified-set reader, initial v3 binding and CITE call reader still acquire authority locks before Blob I/O. The assembler has not yet switched to this mode; no real delayed-S3/heartbeat test ran locally.
- Integration: call nonlocking mode only before any locked authority read in the Session; after both text and set Blobs, call locked `require_current`, then `recheck_saved_reference_text_facts` before provider intent or CITE publication.
- Rollback: additive mode; default remains locked and unserved v3 guard remains.
- Forbidden hotspots: contracts, migration, root dependencies/lockfiles, composition root, active executor, transports, global styles and normative map/source/set data were untouched.
