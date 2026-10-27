# Task CMP-INGEST-02 — the batch operations over comparison work (ADR-0025 decisions 9, 10, 16)

## Outcome
An expert pauses a batch after the set in hand and resumes it, cancels it («Отменить пакет»: the multipart uploads of
unfinished files are aborted, the account's one active slot is freed, no completed version is deleted), leaves a set
out of the batch («Исключить») and queues a failed set again («Повторить», only for a reason a retry can fix); anyone
who holds a role lists a project's batches with their states. Every version a confirmed set creates has its page
profiles put on the comparison queue (idempotent), one confirmed set at a time, and an abandoned or cancelled upload's
multipart parts are aborted by a work kind of the comparison queue. Six sealed operations of contract `1.9.0` are
served instead of stubbed: `listComparisonUploads`, `excludeComparisonUploadSet`, `retryComparisonUploadSet`,
`pauseComparisonUpload`, `resumeComparisonUpload`, `cancelComparisonUpload`.

## Depends on
- CMP-SEAL-C0 (merged): contract `1.9.0`, migration `0038_comparison_foundation`, the nine tables
- CMP-WORK-01 (merged): `ComparisonWorkRepository.enqueue`, `pause_for_upload` / `resume_for_upload` /
  `cancel_for_upload`, `counts(upload_id=...)`, `HandlerRegistry`, the worker hook
- CMP-STORAGE-PARTS-01 (merged): `abort_multipart_sweep`
- CMP-PROFILE-QUEUE-01 (merged): `enqueue_version_page_profiles`, the `page_profile` handler
- CMP-INGEST-01 (merged at `ae5873e9`): `ComparisonUploadService`, `ComparisonUploadRepository`,
  `ACTIVE_BATCH_STATES`, `RETRYABLE_FILE_REASONS`, `require_expert`
- CMP-ADR-01 (ADR-0025 decisions 9, 10, 16)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` unchanged; the conflict reasons used are the registered
  `comparison_upload_state` and `comparison_set_state`
- API contract: `contracts/api/v1/openapi.json` `1.9.0`, 115 paths / 130 operations / 351 schemas, 27 error codes
- analysis/comparison/event contract: ADR-0025 decisions 9, 10, 16 and the addendum of 2026-10-27
- migration head: `0038_comparison_foundation` (not touched)
- base commit: `ae5873e9` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the base is the tree with CMP-INGEST-01 merged: contract `1.9.0`, 115 / 130 / 351, head
  `0038_comparison_foundation`, the six batch operations still sealed stubs inside `ComparisonUploadAdapter`; the lane
  re-reads it before any edit and STOPs if it differs

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `git show HEAD:contracts/api/v1/openapi.json | python3 -c "import json,sys;d=json.load(sys.stdin);print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; git grep -n "^revision: str" HEAD -- db/migrations/versions/20261028_0038_comparison_foundation.py | cut -d: -f3-; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes
  revision: str = "0038_comparison_foundation"
  ae5873e9a05e0358bbcfc510ecde48b0606a6d18
  ```
- interpretation: equal to the premise (contract `1.9.0`, 115 / 130 / 351, head `0038_comparison_foundation`), so the
  lane did not STOP. The base holds CMP-INGEST-01, CMP-WORK-01, CMP-PROFILE-QUEUE-01 and CMP-STORAGE-PARTS-01

### P-02 — the sealed methods and the enumerator rows the lane unseals
- captured_at: 2026-10-28
- command: `grep -n "class ComparisonUploadAdapter\|comparison_uploads=" src/auditmanager/bootstrap/adapters.py src/auditmanager/bootstrap/composition.py; grep -n "listComparisonUploads\|comparison-uploads\"" tests/integration/composition/test_router_answers.py tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- captured_output:
  ```text
  src/auditmanager/bootstrap/adapters.py:5331:class ComparisonUploadAdapter(_SessionHolder):
  src/auditmanager/bootstrap/composition.py:479:        comparison_uploads=ComparisonUploadAdapter(
  tests/integration/composition/test_router_answers.py:65:    f"/projects/{_PRJ}/comparison-uploads",
  tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py:209:    "listComparisonUploads",
  ```
- interpretation: the adapter exists with the six INGEST-02 methods as `503` stubs and the two enumerators hold exactly
  one row each (the last stub row), so this lane empties `SEALED_STUB_GETS` and `SEALED_STUB_ADDRESSED`

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/ingest/comparison_batch/**`
- `tests/integration/ingest/comparison_batch/**`
- `docs/program/tasks/CMP-INGEST-02.md`
- `docs/program/CMP-INGEST-02.md`
- `src/auditmanager/comparison/profile_queue/enqueue.py` (the optional keyword `comparison_upload_id` only)
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_comparison_stub_operations.py`

The last four are the wiring hunks of `docs/program/dispatch/CMP-WAVE-C0.md` section 1 rule 4 (the adapter methods, the
two enumerators, the stub register) plus the composition hunk the batch service and the two handler factories need
(`bootstrap` may import a context's `public` and the handlers are registered by the composition root, because a
`comparison` module may not import `ingest` internals). `api/routers/ports.py` and `comparison_uploads.py` already carry
the six signatures and are not edited. Each hunk is kept minimal; the integrator resolves overlaps in the merge order of
section 3.

## Lane resources
- foundation_instance: `auditmanager-cmp-ingest-02`
- postgres_port: `57770`
- s3_api_port: `61770`
- s3_console_port: `61771`
- postgres_db: `auditmanager_cmp_ingest_02`
- s3_bucket: `auditmanager-cmp-ingest-02`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, root dependency and lock files
- `src/auditmanager/ingest/comparison_pdf/**` (CMP-INGEST-01), `src/auditmanager/ingest/public.py`,
  `src/auditmanager/storage/**`, `src/auditmanager/comparison/work/**`, `src/auditmanager/comparison/public.py`,
  `src/auditmanager/comparison/profile_queue/handler.py`, `src/auditmanager/workers/**`
- every other lane's paths of `docs/program/dispatch/CMP-WAVE-C0.md` section 2

## Non-goals
- the comparison runs of «После подготовки сравнить все соседние версии» (wave C1): the flag is recorded nowhere here,
  because the frozen contract carries no field for it
- the page profile reads, the ZIP reader, the web screens; no contract, migration or dependency change; no new error code

## Deliverables
1. `src/auditmanager/ingest/comparison_batch/`: the batch service (list, exclude, retry, pause, resume, cancel), the
   batch lifecycle (release one confirmed set at a time, complete, cancel, abandon), the repository, the two work
   handlers (`comparison_batch_drive`, `upload_abort_sweep`), `public.py`
2. `comparison/profile_queue/enqueue.py`: the optional keyword `comparison_upload_id`
3. wiring: the six adapter methods and the two hooks (after a declaration, after a confirmation), the composition lines,
   the two enumerators emptied, the stub register
4. tests in `tests/integration/ingest/comparison_batch/`, every guard shown failing under a quoted mutation
5. the report `docs/program/CMP-INGEST-02.md`

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/integration/ingest/comparison_batch tests/integration/comparison/profile_queue` on the lane's own PostgreSQL and MinIO
- expected: all green
- command: `git diff --check`; `pytest -q tests/contract` minus the three `D-220` files; the three register files of
  `tests/integration/composition` that the wiring touches; `tests/integration/ingest/comparison_pdf`
- expected: clean / green

## Integration contract
INGEST-01's confirmation is unchanged. After it the adapter calls the batch service's hook in a second, idempotent
transaction (a failed hook is repaired by the client's retry of the same key, which replays the confirmation and runs
the hook again). The batch is `processing` from its first confirmed set until every set is `done` or `excluded` and no
queued work of the batch is left; `completed` is written by the lifecycle then. The two work kinds are registered by the
composition root beside `comparison.public.HANDLER_FACTORIES`.

## Failure/idempotency/security cases
- every keyed write replays its recorded outcome under the same key and refuses a different payload
- every write is an expert's act, refused for an administrator without `expert` before anything is read
- pause only while processing, resume only while paused, cancel only while the batch is active, exclude and retry only
  on a set of an active batch that has been proposed
- cancel frees the account's active slot, keeps every confirmed set's versions and their bytes, and the sweep never
  touches a published blob nor a live batch's upload

## Rollback / feature flag
The module flag (`comparison/modules.py`) gates the screens and the claim of the two work kinds; the operations are
additive. Reverting the merge restores the sealed stubs; with live items of a kind this build has no handler for the
worker refuses to start (`CMP-WORK-01`), so a revert cancels or lets those items end first. No migration is involved.

## Handoff
- changed files: (written last)
- commands/results: (written last)
- known limits: (written last)
- integration notes: (written last)
