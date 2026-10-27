# Task CMP-PROFILE-QUEUE-01 — the `page_profile` work kind: a handler on the comparison queue and the call that enqueues a version's profiles

## Outcome
A version's page profiles are built by the comparison worker, not by a caller waiting on children. A handler of kind
`page_profile` is registered through `HANDLER_FACTORIES`; it runs `build_version_page_profiles` for the item's version,
heartbeats and looks for a cancel or a lost lease between pages (stopping cleanly there), maps a child that could not
start to a retried failure, and completes only when every page of the version has a profile row (ready, needs_review or
refused). A public function `enqueue_version_page_profiles(session, *, project_uid, version_uid, created_by_user_uid,
retry_failed=False)` puts the item on the queue (module `versions`, one live item per version, one per version for a
retry) for `CMP-INGEST-02` to call after a set is confirmed.

## Depends on
- CMP-WORK-01 (merged on `integration/compare-modules`): `HANDLER_FACTORIES`, `WorkHandler`, `Outcome`, `WorkItem`,
  `ComparisonWorkRepository.enqueue` with its live dedupe key
- CMP-PROFILE-01 (merged on `integration/compare-modules`): `build_version_page_profiles`, `ChildStartError`,
  `PAGE_PROFILE_WORK_KIND`, the `retry_failed` rebuild of failed pages only

## Frozen inputs
- domain contract: `contracts/domain/v1/**` unchanged
- API contract: `contracts/api/v1/openapi.json` `1.9.0`, 115 paths / 130 operations / 351 schemas, 27 error codes (unchanged)
- analysis/comparison/event contract: ADR-0025 decisions 4, 6, 7, 8, 9 (one handler per kind; an item is one version's
  page loop with a stop between pages; ceilinged children; stored profiles are never changed after insert)
- migration head: `0038_comparison_foundation` (not touched)
- base commit: `b774856c` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the base is the merge of CMP-PROFILE-01 on `integration/compare-modules`: contract `1.9.0`, 115 / 130 / 351, 27 error codes, `VERSION` `0.9.0`, head `0038_comparison_foundation`; the lane printed them before any edit and would have STOPPED if they differed

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0038_comparison_foundation.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes
  0.9.0
  81:revision: str = "0038_comparison_foundation"
  b774856cfe640add88ba996d0fe56d08c5266a25
  ```
- interpretation: equal to the premise of the wave brief (`1.9.0`, 115 / 130 / 351, head `0038_comparison_foundation`), so the lane did not STOP

### P-02 — the facts of the two parts the handler joins
- captured_at: 2026-10-28
- command: `grep -n "HANDLER_FACTORIES\|PAGE_PROFILE_WORK_KIND" src/auditmanager/comparison/public.py; grep -n "def build_version_page_profiles\|on_page\|class ChildStartError" src/auditmanager/comparison/profile/builder.py src/auditmanager/comparison/profile/runner.py; grep -n "def finish" -A12 src/auditmanager/comparison/work/repository.py`
- interpretation: `HANDLER_FACTORIES` is the empty tuple a slice appends to; `PAGE_PROFILE_WORK_KIND = "page_profile"` is only a name; `on_page` is called after each stored page and whatever it raises ends the build there; `finish` ends an item `cancelled` when a cancel was requested and the outcome is not `Completed`, so a stop between pages may answer `Yielded` and the queue decides

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/profile_queue/**`
- `src/auditmanager/comparison/public.py`
- `tests/unit/comparison/profile_queue/**`
- `tests/integration/comparison/profile_queue/**`
- `docs/program/CMP-PROFILE-QUEUE-01.md`
- `docs/program/tasks/CMP-PROFILE-QUEUE-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-profile-queue-01`
- postgres_port: `57790`
- s3_api_port: `61790`
- s3_console_port: `61791`
- postgres_db: `auditmanager_cmp_profile_queue_01`
- s3_bucket: `auditmanager-cmp-profile-queue-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`
- `src/auditmanager/comparison/work/**` (CMP-WORK-01) and `src/auditmanager/comparison/profile/**` (CMP-PROFILE-01): the handler uses their public names and changes neither
- `src/auditmanager/bootstrap/**`, `src/auditmanager/workers/**`, `src/auditmanager/api/**`, `src/auditmanager/ingest/**`, `src/auditmanager/storage/**`, `src/auditmanager/jobs/**`
- `web/**`, global styles

## Non-goals
- the call site of `enqueue_version_page_profiles` (`CMP-INGEST-02` calls it after a set is confirmed) and any link of the item to a `comparison_upload`
- a new migration, column or state; a change to `build_version_page_profiles`
- the page publication under `WorkItem.require_current` (the builder is CMP-PROFILE-01's and stores a page in its own transaction; see the report's limits)
- a status operation or a screen for the queue

## Deliverables
- `src/auditmanager/comparison/profile_queue/**`: the handler class and its factory, the enqueue function, the payload and the dedupe keys
- one append to `src/auditmanager/comparison/public.py`: the factory in `HANDLER_FACTORIES` and the enqueue function with its names in `__all__`
- unit tests (container-free) and integration tests (own PostgreSQL and MinIO), mutation proofs
- the report `docs/program/CMP-PROFILE-QUEUE-01.md`

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/profile_queue tests/integration/comparison/profile_queue`
- expected: all pass; the unit and integration directories of `comparison/work` and `comparison/profile` still pass (the shipped tuple makes a registry with one kind per factory)

## Integration contract
The integrator can rely on: `auditmanager.comparison.public.HANDLER_FACTORIES` holds one factory whose handler has the kind
`page_profile` (equal to `PAGE_PROFILE_WORK_KIND`); `enqueue_version_page_profiles(...)` answers `Enqueued(work_id, created)`
for module `versions` with payload `{"version_uid": ...}` (plus `"retry_failed": true` for a retry), dedupe key
`page_profile:<version_uid>` (`page_profile:<version_uid>:retry_failed` for a retry): a live item of the same project, kind
and key is returned, not doubled, and the item runs on the worker once the module `versions` is on and a handler is
registered (the worker refuses to start while live items of an unhandled kind exist, so the registration and the first
enqueue ship together). The item ends `succeeded` only when every page of the version has a profile row.

## Failure/idempotency/security cases
- a child that never started (`ChildStartError`) is the server's fault: the attempt fails with a retry
- a page that ended without a result is a stored `needs_review` page, not a failed item; the item still completes
- a cancel requested while the item runs, or a lease that is gone, stops the build before the next page (nothing after it)
- a version unknown to the database fails without a retry; a source that cannot be read fails with a retry and the attempt budget
- a payload that is not `{"version_uid": "ver_...", "retry_failed"?: bool}` fails without a retry
- the same version enqueued twice while live is one item; a version of another project is refused at enqueue
- a repeated build writes nothing new (the unique keys of CMP-PROFILE-01), so a resumed or repeated item costs time, not rows
- a path, file name, display number or sheet number is never an identity: the version is addressed by its `ver_` id

## Rollback / feature flag
The comparison module flag (`comparison/modules.py`) governs the worker: with `AUDITMANAGER_COMPARISON_MODULES=none` (the
default) the item stays `queued` and nothing runs. Rollback is not merging the lane.

## Handoff
- changed files: the new package `src/auditmanager/comparison/profile_queue/**` (`handler.py`, `enqueue.py`, `__init__.py`), `src/auditmanager/comparison/public.py` (appends: the imports, the factory in `HANDLER_FACTORIES`, four names in `__all__`), `tests/unit/comparison/profile_queue/**` (2 files, 45 tests), `tests/integration/comparison/profile_queue/**` (a conftest and 3 files, 18 tests), this file and `docs/program/CMP-PROFILE-QUEUE-01.md`; the full list is `git diff --name-only b774856c..HEAD` (11 files)
- commands/results: the report's section 6 (unit 45 and integration 18 passed, 63 together on three runs; the neighbours 880 passed and 1 skipped; the contract battery minus the three `D-220` files 1 307 passed) and section 7 (23 mutation proofs, each shown red and then green; the layered ones are named)
- known limits: the report's section 8; the first three are that a page is stored in the builder's own transaction and not under `WorkItem.require_current` (a worker that lost its lease stores at most the page it was on), that a cancel noticed after the last page ends the item `cancelled` with every page stored, and that `retry_failed` is asked again at each attempt of the same item
- integration notes: the report's section 9; the one shared-file hunk is `comparison/public.py`; `CMP-INGEST-02` calls `enqueue_version_page_profiles(session, project_uid=, version_uid=, created_by_user_uid=)` once per version of a confirmed set (it carries no `comparison_upload_id`); the integrator's `comparison_work=` line of `CMP-WORK-01` section 7.1 is still needed before a worker process runs any comparison item
