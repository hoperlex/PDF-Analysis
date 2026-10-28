# Task CMP-VC-OVERVIEW-01 — the overview of «Проекты и этапы» and the comparison queue summary

## Outcome
The two sealed reads `getComparisonOverview` (`GET /projects/{project_uid}/comparison-overview`) and
`getComparisonQueueSummary` (`GET /execution/comparison-queue`) answer instead of `503`, served by
`ComparisonOverviewAdapter` over a new read service in `src/auditmanager/comparison/overview/**`.

`getComparisonOverview(project_uid)` gives one row per document set of the project with the state of the steps wave C1
carries (`upload`, `profile`, `matrix`, `series`; the three steps of wave C2 — `ai_pairs`, `ai_changes`, `report` — answer
`not_applicable`), the next step the chip proposes by the original's next-step rule (`overview.py:297-331` of
`23f379fd`), the counters «Все / Ждут действия / Идут / Ошибки / Готовы», the totals «N версий · M переходов» and the batches
still being uploaded. `getComparisonQueueSummary` gives the per-install comparison queue: the module set, whether
execution is paused, the items by state, and by module, kind and state, and the age of the oldest queued item. Both are
reads: no write, no work enqueued, no model call. Any role reads. An absent project is `404`. One project's overview is a
fixed number of queries whatever the number of its sets.

## Depends on
- CMP-SEAL-C1, CMP-MATRIX-01, CMP-ENGINE-01, CMP-VIEWER-01, CMP-SERIES-01 (all merged on `integration/compare-modules`),
  CMP-WORK-01, CMP-INGEST-01, CMP-INGEST-02, CMP-PROFILE-QUEUE-01

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at the wave base
- API contract: `contracts/api/v1/openapi.json` `1.10.0`, 131 paths / 148 operations / 432 schemas
- analysis/comparison/event contract: ADR-0025 decisions 4, 6, 23 and its addenda; plan `COMPARE-MODULES-PLAN.md` sections 1.1,
  3.2, 4.0 and 4 wave C1; wave brief `docs/program/dispatch/CMP-WAVE-C1.md`; `docs/program/CMP-SEAL-C1.md` sections 3, 4, 9, 10
- migration head: `0039_comparison_core` (no table is added or changed; every table is read)
- base commit: `c228cf2e` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`, `SEALED_STUB_QUERY`), `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_ADDRESSED`, `SEALED_STUB_COLLECTIONS`, `EXPECTED_ADDRESSED`) and `tests/integration/composition/test_comparison_core_stub_operations.py` (`WIRED`)
- enumerator_owner: CMP-VC-OVERVIEW-01 for the two rows of its operations only (wave brief section 1 rule 4, plan 4.0 rules 1 and 3); merge order MATRIX, ENGINE, VIEWER, SERIES, OVERVIEW, VC-UI-01
- totality_query: `grep -n "comparison-overview\|comparison-queue\|getComparisonOverview\|getComparisonQueueSummary" tests/integration/composition/test_router_answers.py tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` prints no stub row of the two operations, and `tests/integration/composition/test_comparison_core_stub_operations.py` names both in `WIRED`

## Captured premise evidence
- premise: contract `1.10.0`, 131 paths / 148 operations / 432 schemas, head `0039_comparison_core`; the two operations are sealed stubs on the base (`ComparisonOverviewAdapter()` has no state); the reads the brief names for the matrix (`ComparisonMatrixService.get_matrix`) and the series (`ComparisonSeriesService.list_series`) take one document set each, and `ComparisonWorkRepository.counts` takes one project, upload or series, so a project-wide overview needs reads of its own for the bounded query count; the original's overview exists at the pinned commit `23f379fd`.

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0039_comparison_core.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.10.0 131 paths 148 operations 432 schemas 27 error codes
  0.9.0
  79:revision: str = "0039_comparison_core"
  c228cf2ed36a1bff26f169f10143b2e6855ebeaf
  ```
- interpretation: equal to the premise of the wave brief (`1.10.0`, 131 / 148 / 432, head `0039_comparison_core`), so the lane did not STOP

### P-02 — the two operations are a stateless stub class of `adapters.py`
- captured_at: 2026-10-28
- command: `grep -n "class ComparisonOverviewAdapter" -A4 src/auditmanager/bootstrap/adapters.py; grep -n "comparison_overview=" src/auditmanager/bootstrap/composition.py; grep -n "getComparisonOverview\|getComparisonQueueSummary" tests/integration/composition/test_comparison_core_stub_operations.py`
- captured_output:
  ```text
  5954:class ComparisonOverviewAdapter:
  5955-    """`CMP-VC-OVERVIEW-01` replaces the bodies."""
  5956-
  5957-    _DEPENDENCY = "comparison_overview"
  5958-
  505:        comparison_overview=ComparisonOverviewAdapter(),
  60:    "getComparisonOverview": ("GET", f"/projects/{PRJ}/comparison-overview", None, False),
  61:    "getComparisonQueueSummary": ("GET", "/execution/comparison-queue", None, False),
  ```
- interpretation: the adapter has no state; the lane gives it the session factory and the module set (one constructor line, `composition.py:505`); both operations are rows of the stub register `test_comparison_core_stub_operations.py`

### P-03 — the reads the brief names are per document set, per project or per upload
- captured_at: 2026-10-28
- command: `grep -n "    def get_matrix" src/auditmanager/comparison/matrix/service.py; grep -n "    def list_series" -A2 src/auditmanager/comparison/series/service.py; grep -n "    def counts" -A3 src/auditmanager/comparison/work/repository.py; grep -n "^_COUNTS" -A5 src/auditmanager/comparison/work/repository.py`
- captured_output:
  ```text
  258:    def get_matrix(self, *, project_uid: str, document_uid: str) -> dict[str, Any]:
  242:    def list_series(
  243-        self, *, project_uid: str, document_uid: str, after: tuple[datetime, str] | None, limit: int
  244-    ) -> SeriesPage:
  669:    def counts(
  670-        self, session: Session, *, project_uid: str | None = None, upload_id: str | None = None,
  671-        series_id: str | None = None,
  672-    ) -> dict[str, int]:
  213:_COUNTS = text(
  214-    "SELECT state, count(*) AS n FROM comparison_work "
  215-    "WHERE (CAST(:project_uid AS text) IS NULL OR project_uid = :project_uid) "
  216-    "AND (CAST(:upload_id AS text) IS NULL OR comparison_upload_id = :upload_id) "
  217-    "AND (CAST(:series_id AS text) IS NULL OR comparison_series_id = :series_id) GROUP BY state"
  218-)
  ```
- interpretation: calling the three per document set or per series makes the overview N+1, which the brief forbids. The lane therefore reads the tables itself in a set-based repository inside its own package (read-only, a fixed number of statements) and reuses the pure rules of the matrix and the series (the digest, the order, the stale reasons, the effective matrix) by import inside the comparison context; it proves the two agree with the services on the same data (oracle tests). It edits nothing under `matrix/**`, `series/**`, `work/**` or `ingest/**`. The queue summary needs counts by module, kind and state, which `counts` does not give.

### P-04 — the original's sources (the local clone does not exist)
- captured_at: 2026-10-28
- command: `ls /root/projects/PDF-proverka 2>&1 | head -1; for f in backend/app/services/version_comparison/overview.py frontend/static/js/version-comparison-projects.js; do printf "%s " $f; curl -sSf "https://raw.githubusercontent.com/SU10KAZ/PDF-proverka/23f379fd/$f" | wc -l; done`
- captured_output:
  ```text
  ls: cannot access '/root/projects/PDF-proverka': No such file or directory
  backend/app/services/version_comparison/overview.py 385
  frontend/static/js/version-comparison-projects.js 629
  ```
- interpretation: the two files are read as data from the public repository at the pinned commit into a scratch directory outside git (the method of CMP-ORIGINAL-READ-01, CMP-MATRIX-01 and CMP-SERIES-01); every rule the lane ports cites the file and line of that copy; nothing of it is copied into the repository

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/overview/**`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/api/routers/ports.py`
- `tests/unit/comparison/overview/**`
- `tests/integration/comparison/overview/**`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_comparison_core_stub_operations.py`
- `docs/program/CMP-VC-OVERVIEW-01.md`
- `docs/program/tasks/CMP-VC-OVERVIEW-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-vc-overview-01`
- postgres_port: `57880`
- s3_api_port: `61880`
- s3_console_port: `61881`
- postgres_db: `auditmanager_cmp_vc_overview_01`
- s3_bucket: `auditmanager-cmp-vc-overview-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `web/**`, `infra/**`, the `Makefile`, `scripts/**`
- `src/auditmanager/comparison/matrix/**`, `src/auditmanager/comparison/series/**`, `src/auditmanager/comparison/work/**`, `src/auditmanager/comparison/engine/**`, `src/auditmanager/comparison/profile/**`, `src/auditmanager/comparison/profile_queue/**`, `src/auditmanager/comparison/tiles/**`, `src/auditmanager/ingest/**`, `src/auditmanager/documents/**`, `src/auditmanager/storage/**`, `src/auditmanager/jobs/**`, `src/auditmanager/workers/**`, `src/auditmanager/execution/**`
- `bootstrap/adapters.py` outside the body of `ComparisonOverviewAdapter` (and the imports it needs); `bootstrap/composition.py` outside the one constructor line of that adapter; `comparison/public.py` outside the appended names of this lane
- every `conftest.py` outside `tests/unit/comparison/overview/` and `tests/integration/comparison/overview/`

## Non-goals
- the screens, the chip's Russian text, the filter tiles and the search (CMP-VC-UI-01); the steps 4, 6 and 7 (wave C2: they answer `not_applicable`)
- any write, any enqueue, any model call; a cache of the overview; a change of the matrix, series or queue
- a contract or migration change: a missing field is a STOP to the FIX slot

## Deliverables
- `src/auditmanager/comparison/overview/**`: the pure rules (step states, the next-step rule, the counters, the totals), the set-based repository, the read service of the two operations
- `ComparisonOverviewAdapter` (replaces the stub body), one constructor line in `composition.py`, the rows of the three composition enumerators, the appended names of `comparison/public.py`
- unit tests, integration tests (database and the composed application over HTTP; oracle tests against the matrix and series services; the query count over 1 and 30 sets), the mutation proofs
- the report `docs/program/CMP-VC-OVERVIEW-01.md` with the field-by-field mapping for CMP-VC-UI-01

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/overview tests/integration/comparison/overview tests/integration/composition`
- expected: all pass; neither operation answers a stub `503` and no stub row of them remains
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_validate_bootstrap.py --ignore=tests/contract/test_cp00_final_state.py`
- expected: all pass (after the last code commit)

## Integration contract
The integrator can rely on: both operations only read (the row counts of every comparison table, the queue and the command
records are equal before and after a call; no work item is enqueued); one project's overview runs a fixed number of
statements whatever the number of its document sets; a set of another project never appears in a row, a count or the
totals; an unknown project is `404`; the counters add up to the number of rows and each row falls in exactly one of the
four groups; the steps of wave C2 answer `not_applicable`; the queue summary is the whole installation's.

## Failure/idempotency/security cases
- an unknown project: `404` naming `Project`; a malformed identity: `422`; no credential: `401` (the router and the guards of the wave)
- the module set `none`: the overview and the queue read still answer (as the matrix and series reads do); `modules` of the queue summary says `none`
- a set with no profile rows, no build and no series reads `not_started` on each step and proposes the preparation
- a series whose inputs changed reads `stale`; a build whose inputs changed reads `stale`

## Rollback / feature flag
No flag. The reads change nothing; rollback is not merging the lane, after which both operations answer the sealed `503`.

## Handoff
- changed files: to be written with the last commit
- commands/results: to be written with the last commit
- known limits: to be written with the last commit
- integration notes: to be written with the last commit
