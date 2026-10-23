# Task AR-V3-BETA-SOURCE-PEEK-01 — read saved PDF text without lease lock

## Outcome
The saved Run text reader has an explicit nonlocking pre-Blob mode for AR v3 and returns a DB witness that a later final locked transaction can recheck after other Blob reads.

## Depends on
- `AR-V3-BETA-LEASE-PEEK-01`
- `AR-V3-BETA-SAVED-SOURCE-01`

## Frozen inputs
- domain/API/analysis/events contract: `1.2.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `798f05ff5b307178745d45d0e962418ba3e52f57`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the existing source reader locks authority on both sides of its Blob read
### P-01 — reader gates
- captured_at: 2026-10-23
- command: `rg -n 'job_repo.require_current|payload = _read_exact' src/auditmanager/runs/reference_text_input.py`
- captured_output:
  ```text
  101:    job_repo.require_current(session, authority)
  136:    payload = _read_exact(
  152:    job_repo.require_current(session, authority)
  ```
- interpretation: keep this as the default; the new v3 mode uses the nonlocking Job check before/after Blob and a later locked DB witness check.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/reference_text_input.py`
- `tests/integration/runs/test_reference_text_input_offline.py`
- `docs/program/tasks/AR-V3-BETA-SOURCE-PEEK-01.md`
- `docs/program/AR-V3-BETA-SOURCE-PEEK-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Changing the default locked reader or its existing callers.
- Changing the verified norm-set reader or v3 request assembler yet.
- Claiming the complete slow-Blob lease hazard closed.

## Deliverables
- Explicit nonlocking source read and DB witness recheck helper.
- Focused stale/changed source tests and result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_reference_text_input_offline.py tests/integration/runs/test_v3_execution_request.py -x --tb=short`
- expected: all passed; governance and exact changed-path check clear.

## Integration contract
The v3 request assembler calls `load_saved_reference_text(..., lock_authority=False)` only when its Session holds no prior authority row lock, then after all Blob reads calls locked `JobRepository.require_current` and `recheck_saved_reference_text_facts` in the same short transaction. The returned text remains input only; no provider effect is authorized by the nonlocking check.

## Failure/idempotency/security cases
- Stale Attempt before or after Blob, wrong Run/Version/project/stage, changed artifact ref or page count refuse. Locked default behavior remains identical.
- A missing witness refuses the final recheck rather than relying on supplied text alone.

## Rollback / feature flag
Additive unserved mode; default stays locked. Revert before v3 assembler integration without migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: verified set reader and assembler still hold locks
- integration notes: do not call nonlocking mode after any earlier `require_current` in the same transaction
