# Task AR-V3-BETA-CALL-READ-01 — read completed v3 call for CITE

## Outcome
A current CITE Attempt can obtain one completed AR v3 call/effect pair for its Run and Job, with verified request/response hashes, response Blob identity, provider provenance and usage; malformed or ambiguous pairs refuse.

## Depends on
- `AR-V3-BETA-PROVIDER-JOURNAL-01`
- `AR-V3-BETA-ANSWER-CUSTODY-01`
- `AR-V3-BETA-REPLY-REPLAY-01`

## Frozen inputs
- domain contract: `contracts/domain/v1`, unchanged
- API contract: `contracts/api/v1`, unchanged
- analysis/comparison/event contract: `contracts/analysis/v1`, unchanged
- migration head: `0032_ar_v3_run_group`, unchanged
- base commit: `6025bcc0784bfb76876c4d3233d1c755b1b9eac4`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the jobs boundary already has a completed recorded-call reader, but no v3 reader
### P-01 — existing reader
- captured_at: 2026-10-23
- command: `rg -n 'def completed_recorded_call' src/auditmanager/jobs/repository.py`
- captured_output:
  ```text
879:    def completed_recorded_call(
  ```
- interpretation: add a separate v3 shape without loosening v2's exact recorded-call rule.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/jobs/public.py`
- `tests/integration/jobs/test_v3_completed_call.py`
- `docs/program/tasks/AR-V3-BETA-CALL-READ-01.md`
- `docs/program/AR-V3-BETA-CALL-READ-01.md`
- `docs/program/dispatch/AR-V3-BETA-CODE-QUEUE.md`

## Forbidden hotspots
- `contracts/**`, migration head, root dependencies and lock files
- composition root, active executor, provider transports, global styles
- normative maps, source corpus and set data

## Non-goals
- Grounding citations, writing a CITE StageResult or serving v3.
- Treating a provider answer as an expert decision.
- Altering historical v1/v2 completed-call readers.

## Deliverables
- An Attempt-fenced completed-v3-call reader and public immutable value.
- Focused matching and mutation tests; result note.

## Required tests
- command: `PYTHONPATH=src /root/projects/PDF-Analysis/.venv/bin/python -m pytest -q -p no:cacheprovider tests/integration/jobs/test_v3_completed_call.py tests/integration/runs/test_v3_reply_custody.py -x --tb=short`
- expected: all passed; governance and exact changed-path check clear.

## Integration contract
The CITE owner calls `JobRepository.completed_v3_call(session, authority)` while the new Attempt is current. The returned call may belong to a prior Attempt of the same Job after recovery, but its completed effect and canonical call must agree. CITE rebuilds the current saved request/set and compares its candidate, scope, set and provider-body SHA with this value before reading the reply Blob through `read_v3_reply`.

## Failure/idempotency/security cases
- Zero/multiple calls, incomplete effect, wrong Job, mismatched Run mode/connection, provider/model/hash/usage drift or malformed Blob parameters refuse.
- The reader never returns prompt or answer text and performs no external effect.
- Current Attempt is checked before and after the query; earlier completed Attempt is usable only within the same Job.

## Rollback / feature flag
The v3 executor guard remains. This read-only method can be reverted before CITE activation without data migration.

## Handoff
- changed files: result note
- commands/results: result note
- known limits: CITE StageResult and served wiring remain open
- integration notes: compare returned fields with rebuilt saved request and verified Blob
