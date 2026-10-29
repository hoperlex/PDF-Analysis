# Task CMP-SERIES-01 — the series of adjacent transitions: sheet pairs, results, post-phases, verdicts, steering and the compare-after-preparation flag

## Outcome
The nine operations `startComparisonSeries`, `listComparisonSeries`, `getComparisonSeries`, `pauseComparisonSeries`,
`resumeComparisonSeries`, `cancelComparisonSeries`, `finishComparisonSeries`, `listComparisonSheetPairs` and
`getComparisonSheetPair` answer instead of `503`, served by `ComparisonSeriesAdapter` over a new service in
`src/auditmanager/comparison/series/**`. A series is comparison work over the **adjacent** transitions of the ordered
versions of one document set: it starts only when the matrix is `ready`, binds the matrix revision `{matrix_id,
edit_no}` and the version order revision, has at most one live series per document set, gets its sheet pairs from the
matrix (`read_adjacent_sheet_pairs`) and each pair's result from the engine (`compare_sheet_pair`), runs the post-phases
of the original after the sheet loop (parts coverage, permit reconciliation), derives the transition verdict as a list of
codes beside the counts, and is steered by pause / resume / cancel / finish («Досчитать») / restart («Заново»). All
progress is in the database. `compare_after_preparation` is stored by `createComparisonUpload` (the adapter's refusal of
`true` is removed) and a set whose preparation completes starts the matrix preparation and then the series.

## Depends on
- CMP-SEAL-C1, CMP-MATRIX-01, CMP-ENGINE-01, CMP-VIEWER-01 (all merged on `integration/compare-modules`), CMP-WORK-01,
  CMP-INGEST-01, CMP-INGEST-02, CMP-PROFILE-QUEUE-01

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at the wave base (prefixes `cser`, `ctn`, `ctp`, `csp`, `cpr` are in the catalogue)
- API contract: `contracts/api/v1/openapi.json` `1.10.0`, 131 paths / 148 operations / 432 schemas
- analysis/comparison/event contract: ADR-0025 decisions 3, 4, 5, 7 (and its addendum), 10, 13, 14, 16, 18, 20, 23;
  wave brief `docs/program/dispatch/CMP-WAVE-C1.md` section 4 (the pair evidence interface, the result `jsonb`);
  `docs/program/CMP-SEAL-C1.md` sections 3 (shape decisions 3, 4, 7, 8), 4 and 9
- migration head: `0039_comparison_core` (tables `comparison_series`, `comparison_transition`, `comparison_sheet_pair`
  and the column `comparison_work.comparison_series_id` exist; the lane writes them)
- base commit: `9f5f4912` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`, `SEALED_STUB_QUERY`), `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_ADDRESSED`, `EXPECTED_ADDRESSED`), `tests/integration/composition/test_comparison_core_stub_operations.py` (`WIRED`) and `scripts/recovery/grant_classification.py` (`SEALED_NOT_YET_WRITTEN`)
- enumerator_owner: CMP-SERIES-01 for the nine rows of its operations and the three tables `comparison_series`, `comparison_transition`, `comparison_sheet_pair` only (wave brief section 1 rule 4, plan 4.0 rules 1 and 3); merge order MATRIX, ENGINE, VIEWER, SERIES
- totality_query: `grep -n "comparison-series\|comparison-transitions\|comparison-sheet-pairs/\|ComparisonSeries\|ComparisonSheetPair" tests/integration/composition/test_router_answers.py tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` prints no stub row of the nine operations (the tile row of CMP-VIEWER-01 is gone too), and `grep -n "comparison_series\|comparison_transition\|comparison_sheet_pair\b" scripts/recovery/grant_classification.py` prints no member of `SEALED_NOT_YET_WRITTEN`

## Captured premise evidence
- premise: contract `1.10.0`, 131 paths / 148 operations / 432 schemas, head `0039_comparison_core`; the nine operations are sealed stubs on the base; the pair `compare_sheet_pair` and the adjacency read `read_adjacent_sheet_pairs` are exported; the original's `parts.py`, `permit.py` and the phases of `jobs.py` exist at the pinned commit `23f379fd`.

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0039_comparison_core.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.10.0 131 paths 148 operations 432 schemas 27 error codes
  0.9.0
  79:revision: str = "0039_comparison_core"
  9f5f49128723c231813430ef3d941c1723643028
  ```
- interpretation: equal to the premise of the wave brief (`1.10.0`, 131 / 148 / 432, head `0039_comparison_core`), so the lane did not STOP

### P-02 — the nine operations are a stub class of `adapters.py` with a no-argument constructor
- captured_at: 2026-10-28
- command: `grep -n "class ComparisonSeriesAdapter" -A4 src/auditmanager/bootstrap/adapters.py; grep -n "comparison_series=" src/auditmanager/bootstrap/composition.py; grep -n "comparison_series_id" db/migrations/versions/20261028_0039_comparison_core.py | head -3; grep -n "compare_after_preparation" src/auditmanager/bootstrap/adapters.py | head -3`
- captured_output:
  ```text
  5833:class ComparisonSeriesAdapter:
  5834-    """`CMP-SERIES-01` replaces the bodies (the sheet-pair results are written by
  5835-    `CMP-ENGINE-01`)."""
  5836-
  5837-    _DEPENDENCY = "comparison_series"
  503:        comparison_series=ComparisonSeriesAdapter(),
  49:``comparison_work.comparison_series_id`` (nullable, frozen once set) so that a series can pause, resume and
  350:                 WHERE s.comparison_series_id = NEW.restarted_from_series_id
  370:                WHERE s.comparison_series_id = NEW.comparison_series_id
  5397:        compare_after_preparation: bool = False,
  5401:        if compare_after_preparation:
  ```
- interpretation: the adapter has no state; the lane gives it the session factory and the object store (one constructor line, `composition.py:503`); the refusal of `compare_after_preparation` is the `if` at `adapters.py:5401`; the column of the work item exists in the migration

### P-03 — the entry points of the two lanes the series stands on
- captured_at: 2026-10-28
- command: `grep -n "def read_adjacent_sheet_pairs" -A3 src/auditmanager/comparison/matrix/service.py; grep -n "def compare_sheet_pair" -A14 src/auditmanager/comparison/engine/service.py | head -16`
- captured_output:
  ```text
  706:def read_adjacent_sheet_pairs(
  707-    session_factory: sessionmaker[Session], *, project_uid: str, document_uid: str
  708-) -> AdjacentSheetPairs:
  127:def compare_sheet_pair(
  128-    session_factory: sessionmaker[Session],
  129-    blob_store: Any,
  130-    *,
  131-    project_uid: str,
  132-    page_a_profile_id: str | None,
  133-    page_b_profile_id: str | None,
  134-    link_reasons: Sequence[str] = (),
  135-    part: str | None = None,
  136-    runner: ChildRunner | None = None,
  137-    child_limits: profile_limits.ChildLimits = CHILD_LIMITS,
  138-    work_dir: str | None = None,
  139-    before_publish: Callable[[], None] | None = None,
  140-    fence: Callable[[Session], None] | None = None,
  ```
- interpretation: the adjacency read answers the pairs of every adjacent transition with the revision it was read at; the pair comparison takes a `fence` called in the transaction that inserts the result row, which the series' pair handler hands `WorkItem.require_current`

### P-04 — the original's sources the inventory did not read (the local clone does not exist)
- captured_at: 2026-10-28
- command: `ls /root/projects/PDF-proverka 2>&1 | head -1; for f in parts permit jobs series; do printf "%s.py " $f; curl -sSf "https://raw.githubusercontent.com/SU10KAZ/PDF-proverka/23f379fd/backend/app/services/version_comparison/$f.py" | wc -l; done; curl -sSf "https://raw.githubusercontent.com/SU10KAZ/PDF-proverka/23f379fd/backend/app/services/version_comparison/jobs.py" | grep -n "^def _parts_phase\|^def _permit_phase\|^def _with_parts\|^def create_run"`
- captured_output:
  ```text
  ls: cannot access '/root/projects/PDF-proverka': No such file or directory
  parts.py 75
  permit.py 219
  jobs.py 1222
  series.py 301
  420:def create_run(object_id: str, project_id: str, a_vid: str, b_vid: str, scope: str,
  532:def _with_parts(object_id: str, sha_a: str, sha_b: str, items: list[dict[str, Any]],
  875:def _parts_phase(object_id: str, run_id: str) -> None:
  951:def _permit_phase(object_id: str, run_id: str) -> None:
  ```
- interpretation: the files are read as data from the public repository at the pinned commit into a scratch directory outside git (the method of CMP-ORIGINAL-READ-01, CMP-MATRIX-01 and CMP-ENGINE-01); every rule the lane ports cites the file and line of that copy; nothing of it is copied into the repository

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/series/**`
- `src/auditmanager/comparison/engine/enqueue.py`
- `src/auditmanager/comparison/work/**`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/ingest/comparison_pdf/**`
- `src/auditmanager/ingest/comparison_batch/**`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/api/routers/ports.py`
- `scripts/recovery/grant_classification.py`
- `tests/unit/comparison/series/**`
- `tests/unit/comparison/engine/test_handler_unit.py`
- `tests/unit/comparison/work/test_composition_unit.py`
- `tests/integration/comparison/series/**`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_comparison_core_stub_operations.py`
- `docs/program/CMP-SERIES-01.md`
- `docs/program/tasks/CMP-SERIES-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-series-01`
- postgres_port: `57870`
- s3_api_port: `61870`
- s3_console_port: `61871`
- postgres_db: `auditmanager_cmp_series_01`
- s3_bucket: `auditmanager-cmp-series-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `web/**`, `infra/**`, the `Makefile`
- `src/auditmanager/comparison/profile/**`, `src/auditmanager/comparison/matrix/**`, `src/auditmanager/comparison/tiles/**`, `src/auditmanager/comparison/engine/**` except `enqueue.py` (the series keyword), `src/auditmanager/storage/**`, `src/auditmanager/jobs/**`, `src/auditmanager/workers/**`, `src/auditmanager/documents/**`
- `src/auditmanager/comparison/work/**` beyond the series id (the column, the keyword of `enqueue`, the three `*_for_series` controls, the counts filter); `src/auditmanager/ingest/comparison_pdf/**` and `src/auditmanager/ingest/comparison_batch/**` beyond the `compare_after_preparation` flag and the `BatchLifecycle.advance` hook
- `bootstrap/adapters.py` outside the body of `ComparisonSeriesAdapter` (and the imports it needs), the refusal lines of `ComparisonUploadAdapter.create_upload` and the one mapping line of the flag in `_comparison_upload`; `bootstrap/composition.py` outside the one constructor line of that adapter
- `HANDLER_FACTORIES` of `comparison/public.py` and its pins only by the lane's own kinds

## Non-goals
- the matrix (MATRIX), the pair result and its mask (ENGINE), the tiles (VIEWER): read, never written
- the overview of the seven steps and the queue summary (CMP-VC-OVERVIEW-01), the screens and the Russian sentences of the verdict and of the new refusal reasons (CMP-VC-UI-01)
- the AI layers (the pair check, the sheet description, the specification comparison, the reports): wave C2
- a contract or migration change: a missing field or table is a STOP to the FIX slot
- an automatic repair of a failed pair other than the explicit «Досчитать»

## Deliverables
- `src/auditmanager/comparison/series/**`: the plan of a series from the adjacent pairs, the repository of the three tables, the stored input digest and the stale reasons, the pair handler (`series_pair`), the drive (`series_drive`), the follow-up of an upload (`series_after_preparation`), the advance that finalises a transition (parts coverage, permit reconciliation, summary, verdict codes) and the series, the service of the nine operations, the contract-shaped views
- `ComparisonSeriesAdapter` (replaces the stub body), one constructor line in `composition.py`, the rows of the three composition enumerators and of `SEALED_NOT_YET_WRITTEN`, the appended names and the three handler factories of `comparison/public.py`
- the series id on the work item (`comparison/work/**`) and on `enqueue_pair_result`
- the flag `compare_after_preparation` stored by the ingest create path, read back by the upload view, no longer refused, and the follow-up hook in `BatchLifecycle.advance`
- unit tests, integration tests (database, object store, the composed application over HTTP, the real runner and the real engine on the synthetic corpus), the mutation proofs
- the report `docs/program/CMP-SERIES-01.md`

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/series tests/integration/comparison/series tests/integration/comparison tests/integration/composition tests/integration/ingest/comparison_pdf tests/integration/ingest/comparison_batch`
- expected: all pass; none of the nine operations answers a stub `503` and no stub row of them remains
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py`
- expected: all pass (after the last code commit)

## Integration contract
The integrator can rely on: a series is created `queued` with every adjacent transition and every sheet pair of the matrix
revision `{matrix_id, edit_no}` in one transaction, and its work (one `series_pair` item per pair that needs the engine,
one `series_drive` item per series, all carrying `comparison_work.comparison_series_id`) in the same one; an added,
removed or unmatched pair is `done` at once and is never compared; a pair that is compared gets its result from
`compare_sheet_pair` under the item's lease fence; a transition is finalised when none of its pairs is `queued` or
`computing`, and its verdict never holds `content_same` while a pair has not finished or has failed; the post-phases write
`parts` and `permit` on the pairs and never touch the result row; `getComparisonSheetPair` copies the members of the
result `jsonb` verbatim; every command is keyed, an expert's act checked in the transaction that acts, and replays its
recorded outcome; `restart: true` names the series it replaced; `compare_after_preparation` is stored on the upload and a
set whose preparation completes queues one `series_after_preparation` item attached to the upload.

## Failure/idempotency/security cases
- a second `startComparisonSeries` while a series is queued, running or paused: `409 conflict` `comparison_series_active`, nothing written; a stale `base_order_revision_no`: `comparison_version_order_stale`; a matrix that is not `ready`: `409 conflict` `comparison_matrix_stale`
- a command the series' state does not allow: `409 conflict` `comparison_series_state`; an administrator without the expert role is refused on every command
- an attempt that lost its lease writes no pair (`WorkItem.require_current` in every transaction that writes one)
- a key replay answers the recorded outcome; the same key with another payload is `idempotency_key_reuse`
- an unknown series, transition or sheet pair is `404`; a document of another project is `404`

## Rollback / feature flag
The module flag (`comparison/modules.py`) gates the worker: with `versions` off the series items stay `queued`. The
operations themselves answer whatever the flag says (as the matrix and upload operations do). Rollback is not merging the
lane: the operations then answer the sealed `503`, and the upload refuses `compare_after_preparation: true` again.

## Handoff
- changed files: `src/auditmanager/comparison/series/**` (new, 13 files), the series id in `src/auditmanager/comparison/work/{model,repository}.py` and one keyword in `comparison/engine/enqueue.py`, the flag and the hook in `src/auditmanager/ingest/comparison_pdf/{repository,service,views}.py` and `ingest/comparison_batch/{repository,service,lifecycle}.py`, the body of `ComparisonSeriesAdapter` and three lines of `ComparisonUploadAdapter` in `bootstrap/adapters.py`, **one line** of `bootstrap/composition.py` (`comparison_series=ComparisonSeriesAdapter(sessions, blob_store=store)`), twelve names and three handler factories in `comparison/public.py`, three names out of `SEALED_NOT_YET_WRITTEN` in `scripts/recovery/grant_classification.py`, the three composition registers, the tuple pin in `tests/unit/comparison/engine/test_handler_unit.py`, `tests/unit/comparison/series/**`, `tests/integration/comparison/series/**`, this file and `docs/program/CMP-SERIES-01.md`; the full list is `git diff --name-only 9f5f4912..HEAD`
- commands/results: the report's section 8 (series unit 67 and integration 77 passed; the comparison integration directories 506 passed; the ingest directories 298 passed; the whole composition directory 1956 passed, 4 skipped, 0 failed; the whole `tests/unit` 4808 passed, 76 skipped; the contract battery 1310 passed) and section 7 (34 mutation proofs, each red and then green)
- known limits: the report's section 9; first: the engine's `UNCHECKED_CHANNEL:<channel>` reason is mapped for the contract's pattern, the engine registers the corpus' second split part onto the wrong region (the ink coverage is refused, the text coverage stands), two refusal reasons are not registered, the permit port reads the first ten text pages and is unmeasured on a real set, and the worker entry point still needs the one line of `CMP-WORK-01` section 7.1
- integration notes: the report's sections 10 and 11; merge after MATRIX, ENGINE and VIEWER; run the comparison integration directories one at a time (they share one database and two of them refuse live items of other kinds)
