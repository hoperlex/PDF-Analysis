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
- captured_at: 2026-10-26
- command: `git grep -n -E 'def completed_v3_call|def record_provider_response|completed_v3_call\(|prepare_v3_execution_request\(|read_v3_reply\(|require_current\(session, authority\)' f475a179f35d51f6316a5f4694eab6f335b9395f -- src/auditmanager/runs/v3_cite_preflight.py src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:864:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:925:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:960:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:1010:    def completed_v3_call(
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:1019:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:1093:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:1111:    def record_provider_response(
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:1122:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:1153:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:1177:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:1207:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:1275:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/jobs/repository.py:1298:        self.require_current(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/runs/v3_cite_preflight.py:72:    call = job_repo.completed_v3_call(session, authority)
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/runs/v3_cite_preflight.py:75:    prepared = prepare_v3_execution_request(
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/runs/v3_cite_preflight.py:96:    reply = read_v3_reply(
  f475a179f35d51f6316a5f4694eab6f335b9395f:src/auditmanager/runs/v3_cite_preflight.py:128:    ) != binding or job_repo.completed_v3_call(session, authority) != call):
  ```
- interpretation: Re-captured on 2026-10-26 from base commit f475a179f35d51f6316a5f4694eab6f335b9395f with git grep against that tree (not at dispatch time). At the base, v3_cite_preflight.py calls completed_v3_call at line 72, prepare_v3_execution_request (the saved-request Blob read) at 75, read_v3_reply (the reply Blob read) at 96 and completed_v3_call again at 128. JobRepository.completed_v3_call starts at repository.py:1010 and calls require_current(session, authority) at 1019 and 1093, with the next def (record_provider_response) at 1111, so the authority check sits at both ends of the completed-call reader and the reader runs before the request and reply reads. Not shown by this output: that the SQL read lies between lines 1019 and 1093 (taken from reading repository.py:1010-1109 of the base) and that require_current takes the lock (the task's own premise). Difference from the dispatch-time record: it placed the reply read at line 95; the base commit has it at line 96. Dispatch-time record (2026-10-23, quoted from the original section, not re-run): command `rg -n 'completed_v3_call\(|prepare_v3_execution_request\(|read_v3_reply\(|require_current\(session, authority\)' src/auditmanager/runs/v3_cite_preflight.py src/auditmanager/jobs/repository.py`; captured_output was a prose summary: current `v3_cite_preflight.py` calls completed call at line 72, request at 75, reply at 95, and completed call again at 128; `JobRepository.completed_v3_call` calls `require_current` before and after its DB query. Original interpretation: both request and reply external reads can inherit an authority lock; move all Blob reads before one final locked witness check.

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
