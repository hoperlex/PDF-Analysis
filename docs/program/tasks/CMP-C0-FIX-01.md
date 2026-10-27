# Task CMP-C0-FIX-01 — four fixes the wave C0 lanes left to the integrator

## Outcome
Four defects that the C0 lanes reported and could not fix inside their own paths are closed, each by a test that is red
without the fix: (1) a `PullAdapter` call made for a comparison work attempt writes an `executor_task` of origin
`comparison_call` carrying `comparison_attempt_id` (a run call is written exactly as before); (2) the comparison queue's
reclaim asks the registered `SPEND_SETTLERS` also for an item it ends `cancelled`, so no sent comparison call stays open;
(3) `test_every_other_field_still_counts_toward_equality` names `upload_kind`; (4) `start_ar_v3_group` refuses a
comparison-only version with `analysis_input_invalid`, reason `comparison_only_version`, not `missing_required_input`.

## Depends on
- CMP-SPEND-01 (merged; report section 8 items 2 and 3, section 9 item 2)
- CMP-INGEST-01 (merged `ae5873e9`; report section 6 items 8 and 9)
- CMP-WORK-01, CMP-SEAL-C0 (merged)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` unchanged (the reason `comparison_only_version` and the origin
  `comparison_call` are already registered by the seal)
- API contract: `contracts/api/v1/openapi.json` `1.9.0`, 115 paths / 130 operations / 351 schemas, 27 error codes
- analysis/comparison/event contract: ADR-0025 decisions 4, 5 and 11
- migration head: `0038_comparison_foundation` (not touched)
- base commit: `ae5873e9a05e0358bbcfc510ecde48b0606a6d18`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the base is `integration/compare-modules` at `ae5873e9`: contract `1.9.0`, 115 / 130 / 351, head
  `0038_comparison_foundation`; the lane re-reads it before any edit and STOPs if it differs

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `git show HEAD:contracts/api/v1/openapi.json | python3 -c "import json,sys;d=json.load(sys.stdin);print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; git grep -n "^revision: str" HEAD -- db/migrations/versions | sort | tail -1 | cut -d: -f3-; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes
  revision: str = "0038_comparison_foundation"
  ae5873e9a05e0358bbcfc510ecde48b0606a6d18
  ```
- interpretation: equal to the premise, so the lane did not STOP

### P-02 — the four defects, as the reports state them and as the code shows them
- captured_at: 2026-10-28
- command: `grep -n 'origin="run_call"' src/auditmanager/executors/pull.py; grep -n 'if work\["cancel_requested"\]:' -A4 src/auditmanager/comparison/work/repository.py | sed -n 8,12p; grep -n '"recognised_character_count": 3' tests/integration/documents/test_version_record_equality.py; grep -n 'DocumentRepository().get_version' -A3 src/auditmanager/runs/v3_group.py`
- captured_output:
  ```text
  265:                revision_id=self._revision.revision_id, origin="run_call",
  512-                self._advance_work(session, work_id, state, "cancelled")
  513-            elif any(settle(session, attempt_id) for settle in spend_settlers):
  514-                self._advance_work(session, work_id, state, "spend_unknown")
  515-            elif int(work["attempt_count"]) >= int(work["max_attempts"]):
  83:        "recognised_character_count": 3,
  242:    version = DocumentRepository().get_version(session, VersionUid.parse(version_id))
  243-    if version.classification is None:
  244-        raise DomainError(ErrorCode.VERSION_CLASSIFICATION_REQUIRED)
  245-    if version.classification.section_code != "AR":
  ```
- interpretation: item 1 the origin is a literal; item 2 the cancel branch ends the item before it asks the settlers;
  item 3 the mapping has no `upload_kind`; item 4 nothing refuses by the kind between `get_version` and the
  classification check

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/executors/pull.py`
- `src/auditmanager/comparison/work/**`
- `src/auditmanager/runs/v3_group.py`
- `tests/unit/comparison/spend/**`
- `tests/unit/comparison/work/**`
- `tests/integration/comparison/work/**`
- `tests/integration/documents/test_version_record_equality.py`
- `tests/unit/executors/**`
- `tests/integration/runs/**`
- `tests/integration/comparison/spend/test_reclaim_spend_unknown.py`
- `docs/program/CMP-C0-FIX-01.md`
- `docs/program/tasks/CMP-C0-FIX-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-c0-fix-01`
- postgres_port: `57810`
- s3_api_port: `61810`
- s3_console_port: `61811`
- postgres_db: `auditmanager_cmp_c0_fix_01`
- s3_bucket: `auditmanager-cmp-c0-fix-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependency and lock files
- `src/auditmanager/bootstrap/**` (the composition root), `src/auditmanager/comparison/public.py`
- `src/auditmanager/comparison/spend/**`, `src/auditmanager/executors/runner_repository.py` (CMP-SPEND-01's, already merged)
- `src/auditmanager/runs/commands.py` (the refusal already exists there; item 4 only calls it)
- every other lane's paths of `docs/program/dispatch/CMP-WAVE-C0.md` section 2

## Non-goals
- linking the journal row to the task (`attach_task`): a later lane, once its adapter knows the task id
- building the comparison call's context (`comparison_attempt_id`, `remaining_seconds()`): the lane that calls a model
  builds it; this lane only makes `PullAdapter` honour it
- asking every settler in the `spend_unknown` branch (it stays `any(...)`; only one settler is registered)
- no contract, migration or dependency change; no new error code

## Deliverables
1. `executors/pull.py`: `_write_task` writes origin `comparison_call` and `comparison_attempt_id` for a context that
   carries one; the strict-xfail marker of the spend pin removed; new unit tests for the pull path
2. `comparison/work/repository.py`: `reclaim_expired` asks the settlers in the cancel branch; the test that pinned the
   defect now pins the fix; new tests in the work directories
3. `test_version_record_equality.py`: `upload_kind` named in `changed`
4. `runs/v3_group.py`: `refuse_comparison_only_version(version)` right after `get_version`; a new integration test
5. the report `docs/program/CMP-C0-FIX-01.md` with a quoted mutation for every guard

About the allowed paths: `tests/unit/executors/**` and `tests/integration/runs/**` take only new tests for items 1 and 4. The one file of
`tests/integration/comparison/spend/` is **not** in the brief's list and is added by necessity: its test
`test_a_cancel_that_arrives_with_a_lost_lease_is_not_settled_by_the_queue_but_by_the_next_call` pins the defect of
item 2 (it asserts the call is still `sent` after the reclaim), so it cannot stay green once the defect is fixed; the lane
changes that one test and nothing else in the file, and the report asks the integrator to ratify the hunk.

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison tests/unit/executors tests/integration/comparison tests/integration/documents/test_version_record_equality.py tests/integration/runs` on the lane's own PostgreSQL and MinIO
- expected: all green
- command: `git diff --check`; `pytest -q tests/contract` minus the three `D-220` files
- expected: clean / green

## Integration contract
A caller that builds a comparison call's context (`comparison_attempt_id`, `remaining_seconds()`) and hands it to
`PullAdapter` gets an `executor_task` of origin `comparison_call` that the runner repository's three liveness statements
already understand; a context without `comparison_attempt_id` is written as before. A reclaim that ends a cancelled
item has asked every registered settler about the lost attempt, so no `sent` row of that attempt is left.

## Failure/idempotency/security cases
- a comparison context that also names a run is refused by the database (`ck_executor_task_origin_shape`), not repaired
- a cancel that arrives with a lost lease still ends the item `cancelled` (the cancel wins), whatever a settler answers
- a live lease never reaches the settlers; an attempt of another item is never settled
- a comparison-only version is refused before any key is claimed, so the refusal writes nothing

## Rollback / feature flag
Not applicable: the changes are corrections of reported defects on the unreleased comparison foundation; reverting the
merge restores the reported behaviour. No migration is involved.

## Handoff
- changed files: `src/auditmanager/executors/pull.py`, `src/auditmanager/comparison/work/repository.py`,
  `src/auditmanager/runs/v3_group.py`; tests `tests/unit/comparison/spend/test_wiring_and_pins.py` (xfail removed),
  `tests/unit/comparison/work/test_reclaim_settlers_unit.py` (new), `tests/unit/executors/test_pull_comparison_origin.py`
  (new), `tests/integration/comparison/work/test_lease_reclaim.py`, `tests/integration/comparison/spend/test_reclaim_spend_unknown.py`
  (the one hunk outside the brief's list, report section 6 item 1), `tests/integration/documents/test_version_record_equality.py`,
  `tests/integration/runs/test_v3_group_refuses_a_comparison_only_version.py` (new); this file and `docs/program/CMP-C0-FIX-01.md`
- commands/results: unit (`tests/unit/comparison`, `tests/unit/executors`) 1244 passed; integration (comparison, documents,
  ingest/comparison_pdf, db/test_ar_v3_run_group, executors) 806 passed, 16 skipped (sshd opt-ins); `tests/integration/runs` 948
  passed; `tests/contract` minus the three `D-220` files 1307 passed, 19283 subtests; `git diff --check` clean; every guard
  shown red under a quoted mutation (report section 5)
- known limits: report section 6 (one test hunk outside the brief's list awaits ratification; `any(...)` stays in the
  `spend_unknown` branch; no end-to-end test of `PullAdapter` against real rows with a comparison context; trailer names
  Sonnet 4.6 as the brief says)
- integration notes: report section 7; no wiring file is touched, nothing overlaps another lane
