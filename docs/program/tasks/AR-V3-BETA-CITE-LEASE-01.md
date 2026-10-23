# Task AR-V3-BETA-CITE-LEASE-01 — keep CITE Blob reads outside lease locks

## Outcome
The unserved AR v3 CITE preflight reads the saved request and private reply Blobs without holding the Attempt lease lock, then verifies the group, source, set and completed call inside one final locked transaction before returning a grounded review.

## Depends on
- `AR-V3-BETA-CITE-PREFLIGHT-01`
- `AR-V3-BETA-REQUEST-LEASE-01`
- `AR-V3-BETA-CALL-READ-01`

## Frozen inputs
- domain/API/analysis/events contract: `1.2.0`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `f475a179f35d51f6316a5f4694eab6f335b9395f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the completed-call reader locks authority and CITE calls it before request and reply Blob reads
### P-01 — CITE order and completed-call lock
- captured_at: 2026-10-23
- command: `rg -n 'completed_v3_call\(|prepare_v3_execution_request\(|read_v3_reply\(|require_current\(session, authority\)' src/auditmanager/runs/v3_cite_preflight.py src/auditmanager/jobs/repository.py`
- captured_output: current `v3_cite_preflight.py` calls completed call at line 72, request at 75, reply at 95, and completed call again at 128; `JobRepository.completed_v3_call` calls `require_current` before and after its DB query.
- interpretation: both request and reply external reads can inherit an authority lock; move all Blob reads before one final locked witness check.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/runs/v3_execution_request.py`
- `src/auditmanager/runs/v3_cite_preflight.py`
- `tests/integration/jobs/test_v3_completed_call.py`
- `tests/integration/runs/test_v3_execution_request.py`
- `tests/integration/runs/test_v3_cite_preflight.py`
- `docs/program/tasks/AR-V3-BETA-CITE-LEASE-01.md`
- `docs/program/AR-V3-BETA-CITE-LEASE-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies/lockfiles
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Activating the served v3 executor or publishing a normative decision.
- Changing locked defaults for existing completed-call/request consumers.
- Claiming a real delayed-storage heartbeat result without PostgreSQL/S3.

## Deliverables
- Explicit unlatched completed-call and request modes, plus a reusable final request witness fence.
- CITE ordering and changed-evidence refusal tests; result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/jobs/test_v3_completed_call.py tests/integration/runs/test_v3_execution_request.py tests/integration/runs/test_v3_cite_preflight.py tests/integration/runs/test_v3_cite_stage.py -x --tb=short`
- expected: all passed; handoff exact paths and clean tree.

## Integration contract
An unlocked completed-call read is provisional only. CITE assembles the request without its final lock, reads and grounds the verified reply, then locks group/Attempt authority and compares saved source/set DB witnesses and the same completed call. The normal request assembler and completed-call reader remain locked by default. A caller must not hold an earlier authority lock during preflight.

## Failure/idempotency/security cases
- Changed call, group, source or set after Blob I/O refuses before a successful CITE StageResult.
- Stale Attempt refuses; no provider redispatch or fallback.
- The CITE writer still performs its publication-side rechecks after outbox readback.

## Rollback / feature flag
Unserved behind the v3 executor guard. Revert this preflight path before activation; no migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: real delayed-storage heartbeat acceptance and served wiring remain
- integration notes: treat unfenced request/call as provisional inputs only
