# Task AR-V3-BETA-REQUEST-LEASE-01 — keep Blob reads outside final lock

## Outcome
The saved AR v3 request assembler reads group pins, PDF text and verified set without locking the Attempt lease, then takes one final locked authority fence and rechecks all three DB witnesses before returning exact provider bytes.

## Depends on
- `AR-V3-BETA-SOURCE-PEEK-01`
- `AR-V3-BETA-SET-PEEK-01`
- `AR-V3-BETA-REQUEST-CUSTODY-01`

## Frozen inputs
- domain/API/analysis/events contract: `1.2.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `4bda0b804f1da6a256ddc0bbd59c370358a1e96b`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: initial group binding and both saved readers currently take locked authority before Blob I/O
### P-01 — request flow
- captured_at: 2026-10-23
- command: `rg -n 'resolve_v3_execution_binding\(|load_saved_reference_text\(|prepare_v3_corpus_request\(' src/auditmanager/runs/v3_execution_request.py`
- captured_output:
  ```text
  88:    binding = resolve_v3_execution_binding(
  94:    saved_text = load_saved_reference_text(
  108:    pinned = prepare_v3_corpus_request(
  141:    if resolve_v3_execution_binding(
  ```
- interpretation: all early reads must use nonlocking checks; only the last resolver call may take authority locks, followed by DB-only source/set witness rechecks.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/runs/v3_execution_binding.py`
- `src/auditmanager/runs/v3_citations.py`
- `src/auditmanager/runs/v3_execution_request.py`
- `tests/integration/runs/test_v3_execution_request.py`
- `docs/program/tasks/AR-V3-BETA-REQUEST-LEASE-01.md`
- `docs/program/AR-V3-BETA-REQUEST-LEASE-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Changing default locked group/set/source readers for other callers.
- Reordering CITE preflight's completed-call read, which is a later task.
- Claiming a real delayed-S3/heartbeat acceptance result without a live service.

## Deliverables
- Explicit nonlocking group/set request path and final locked DB witness checks.
- Focused sequencing and changed-witness tests; result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_v3_provider_call.py tests/integration/runs/test_v3_corpus_citation_bridge.py -x --tb=short`
- expected: all passed; governance and exact changed-path check clear.

## Integration contract
`prepare_v3_execution_request` starts with an unlatched group/pack check, then nonlocking saved text and set Blob reads. It builds provider bytes before any lock, takes the existing locked group/Attempt fence, then rechecks source and set DB witnesses in the same transaction. A dispatch caller still commits provider intent before the external call. CITE must rebuild the request before `completed_v3_call` to avoid taking a lock before this flow.

## Failure/idempotency/security cases
- Stale Attempt or changed group/source/Version/set/custody after either Blob refuses before provider intent.
- The early resolver never grants effect authority; the final locked resolver remains unchanged for direct callers.
- Same bytes and settings yield the same candidate/provider-body SHA.

## Rollback / feature flag
Unserved behind v3 executor guard. Revert to default locked path if needed before activation; no migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: CITE call-order lock and live heartbeat acceptance remain
- integration notes: do not hold a prior `require_current` lock when calling this assembler
