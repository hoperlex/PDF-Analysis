# Task AR-V3-BETA-SET-PEEK-01 — read verified set without lease lock

## Outcome
The saved verified retrieval-set reader offers explicit nonlocking pre-Blob authority checks and a complete DB pin witness for the final locked transaction, while preserving its default locked behavior.

## Depends on
- `AR-V3-BETA-LEASE-PEEK-01`
- `AR-V3-BETA-SOURCE-PEEK-01`

## Frozen inputs
- domain/API/analysis/events contract: `1.2.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `2ffb03676d624f54d24f6ceb8aa7edc434e92692`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the existing set reader locks Attempt before and after a potentially 10 MB Blob read
### P-01 — set gates
- captured_at: 2026-10-23
- command: `rg -n 'job_repo.require_current|payload = _read_exact' src/auditmanager/findings/retrieval_set_input.py`
- captured_output:
  ```text
  123:    job_repo.require_current(session, authority)
  138:    payload = _read_exact(
  142:    job_repo.require_current(session, authority)
  ```
- interpretation: keep the default, add an explicit nonlocking mode and later DB-only recheck before any effect.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/findings/retrieval_set_input.py`
- `src/auditmanager/findings/public.py`
- `tests/integration/findings/test_w57a_retrieval_set_input_offline.py`
- `docs/program/tasks/AR-V3-BETA-SET-PEEK-01.md`
- `docs/program/AR-V3-BETA-SET-PEEK-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Changing default locked set reading or any current caller.
- Reordering the v3 request/CITE preflight in this task.
- Claiming heartbeat safety before the entire request path uses the new mode.

## Deliverables
- Nonlocking set reader mode and DB witness recheck on the findings public boundary.
- Focused stale/custody drift tests and result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/findings/test_w57a_retrieval_set_input_offline.py tests/integration/runs/test_v3_execution_request.py -x --tb=short`
- expected: all passed; governance and exact changed-path check clear.

## Integration contract
Call `load_verified_retrieval_set(..., lock_authority=False)` only before any locked authority read in the Session; after all Blob reads, call locked `require_current`, then `recheck_verified_retrieval_set_facts` in that same short transaction. The witness binds the whole confirmed set/catalogue/Blob pin row, not just set SHA. No provider or publication effect is authorized by nonlocking checks.

## Failure/idempotency/security cases
- Expired/stale Attempt before or after Blob, changed custody/catalogue/set pin, absent witness and changed Run state refuse.
- Default locked behavior and set byte cap remain unchanged.

## Rollback / feature flag
Additive unserved mode; default stays locked. Revert before assembler integration without migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: v3 binding/preflight still locks before Blob reads
- integration notes: final locked recheck is mandatory for effect authority
