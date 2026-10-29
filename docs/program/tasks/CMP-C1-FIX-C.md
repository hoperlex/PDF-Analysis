# Task CMP-C1-FIX-C — the third FIX lane of wave C1, backend: a plain-PDF upload is profiled, a version is built in bounded items, an identical version is not profiled again

## Outcome
The three items of `MEASURE-ENGINE-01.md` section 9 that are backend code are closed, each with a test that fails before the
change and passes after it (a quoted mutation shows the guard red, then green):

1. **FIX-1 (blocking).** A version admitted through the product's own plain-PDF upload (`comparison.source_pdf`) can be
   profiled, compared and tiled: `load_source_version` accepts the manifest role of a portal version (`source.document`) and
   that of a comparison version (`comparison.source_pdf`), nothing else, and refuses a manifest with both with a typed reason.
   One end-to-end integration test drives the chain through the product's own path, with no seeded manifest: the comparison
   upload operations, the confirmation, the worker's comparison runner for `page_profile`, `matrix_build`, the series and its
   `pair_result` items, and one pair tile read, on the corpus `fixtures/comparison/`.
2. **FIX-3.** One `page_profile` item no longer has to finish a whole version inside one attempt's 900 s watchdog: an attempt
   builds at most `N` pages and gives the item back (`Yielded`, which spends no attempt), so the item, its dedupe key
   (`page_profile:<version_uid>`, `…:retry_failed`) and its retry semantics stay as they are. `N` is derived from the
   measured rates and recorded; a synthetic version of more pages than one attempt holds is profiled completely.
3. **FIX-4 (if small).** A version whose source bytes equal those of another version of the same project is not rendered and
   extracted again: its pages are copied from the stored profiles of that version (same algorithm version, same page).

## Depends on
- CMP-MEASURE-01, CMP-C1-FIX-A, CMP-C1-FIX-B, CMP-INGEST-01, CMP-INGEST-02, CMP-PROFILE-01, CMP-PROFILE-QUEUE-01, CMP-WORK-01,
  CMP-MATRIX-01, CMP-ENGINE-01, CMP-SERIES-01, CMP-VIEWER-01 (all merged on `integration/compare-modules`)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at the wave base
- API contract: `contracts/api/v1/openapi.json` `1.10.0`, 131 paths / 148 operations / 432 schemas (unchanged)
- analysis/comparison/event contract: ADR-0025 decisions 4, 6, 8 and both addenda; wave briefs `docs/program/dispatch/CMP-WAVE-C1.md`
  section 1 and `CMP-WAVE-C0.md` section 1; the report `docs/program/compare/MEASURE-ENGINE-01.md` sections 2, 8.2 and 9
- migration head: `0039_comparison_core` (no table or column is added or changed)
- base commit: `00afbc21` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: contract `1.10.0`, 131 paths / 148 operations / 432 schemas, head `0039_comparison_core`; `load_source_version` selects only `MANIFEST_ROLE_SOURCE_DOCUMENT` while the plain-PDF upload writes `MANIFEST_ROLE_COMPARISON_PDF`; the attempt watchdog is 900 s and a `page_profile` item is a whole version.

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-29
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0039_comparison_core.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.10.0 131 paths 148 operations 432 schemas
  0.9.0
  79:revision: str = "0039_comparison_core"
  00afbc210d507d8ead88cb62c7fd16af5a8181dc
  ```
- interpretation: equal to the premise of the dispatch (`1.10.0`, 131 / 148 / 432, head `0039_comparison_core`), so the lane did not STOP

### P-02 — the role the profile reads and the role the upload writes, and the watchdog, at the base
- captured_at: 2026-10-29
- command: `grep -n 'MANIFEST_ROLE_SOURCE_DOCUMENT' src/auditmanager/comparison/profile/source.py; grep -n 'role=MANIFEST_ROLE_COMPARISON_PDF' src/auditmanager/ingest/comparison_pdf/service.py; grep -n '^ATTEMPT_WATCHDOG_SECONDS' src/auditmanager/comparison/work/model.py src/auditmanager/jobs/lease.py`
- captured_output:
  ```text
  60:    from auditmanager.documents.public import MANIFEST_ROLE_SOURCE_DOCUMENT, DocumentRepository
  64:    entry = next((item for item in record.manifest if item.role == MANIFEST_ROLE_SOURCE_DOCUMENT), None)
  905:                        role=MANIFEST_ROLE_COMPARISON_PDF,
  src/auditmanager/comparison/work/model.py:78:ATTEMPT_WATCHDOG_SECONDS: Final[float] = 900.0
  src/auditmanager/jobs/lease.py:21:ATTEMPT_WATCHDOG_SECONDS = 900
  ```
- interpretation: the reader takes `source.document` only, the upload writes `comparison.source_pdf`, and the watchdog fences an attempt after 900 s whatever its progress (`comparison/work/heartbeat.py`), so a heartbeat per page cannot extend it

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/profile/**`
- `src/auditmanager/comparison/profile_queue/**`
- `src/auditmanager/comparison/engine/inputs.py`
- `src/auditmanager/comparison/tiles/**`
- `tests/unit/comparison/**`
- `tests/integration/comparison/**`
- `docs/program/CMP-C1-FIX-C.md`
- `docs/program/tasks/CMP-C1-FIX-C.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-c1-fix-c`
- postgres_port: `57930`
- s3_api_port: `61930`
- s3_console_port: `61931`
- postgres_db: `auditmanager_cmp_c1_fix_c`
- s3_bucket: `auditmanager-cmp-c1-fix-c`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `web/**`, `infra/**`, the `Makefile`, `scripts/**`
- `src/auditmanager/jobs/**`, `src/auditmanager/documents/**`, `src/auditmanager/comparison/{work,matrix,overview,series}/**`, `src/auditmanager/comparison/public.py`
- `src/auditmanager/bootstrap/**`, `src/auditmanager/api/**`, `src/auditmanager/ingest/**`
- every `conftest.py` outside `tests/unit/comparison/` and `tests/integration/comparison/`

## Non-goals
- a longer watchdog for the kind, or a change of `comparison/work/**` or `jobs/lease.py` (the item size is made bounded instead)
- the dedupe key, the payload keys, the contract or a table of the work queue: a lane that needs one STOPs and reports
- a cache keyed by the page content Merkle that skips rendering (the Merkle is a product of the extraction child, which is
  most of the cost; the reuse built here is keyed by the source bytes)
- FIX-2 and FIX-5 of the measurement report (the upload dialog, the claim cadence)

## Deliverables
- item 1: `profile/source.py` (both roles, ambiguity refused), the tile and engine readers follow because they call it; unit tests, the end-to-end test `tests/integration/comparison/test_upload_to_series_end_to_end.py`
- item 2: `profile/builder.py` (a page cap per call, a retry cutoff), `profile/repository.py`, `profile_queue/handler.py` (`Yielded` when pages remain); unit and integration tests
- item 3: `profile/builder.py`, `profile/repository.py` (copy of the stored pages of an identical version of the same project); unit and integration tests
- the report `docs/program/CMP-C1-FIX-C.md` and this file's Handoff

## Required tests
- command: `git diff --check`; `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=/tmp/pytest-cmp-c1-fix-c/<run> tests/unit/comparison`; `tests/integration/comparison` in ONE process (own containers, `.env` loaded); `tests/integration/ingest/comparison_pdf` and `comparison_batch`; the whole `tests/integration/composition` directory; after the last code commit the whole `tests/unit` and `tests/contract` minus `tests/contract/test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` (`D-220`)
- expected: every command exits 0 with the counts in the report; every new guard is shown red under a quoted mutation

## Integration contract
- a version admitted by `completeComparisonUploadFile` → `confirmComparisonUploadSet` is profiled by the worker's `page_profile` item, compared by the engine and read by the tile route with no further step
- a `page_profile` item keeps its dedupe key and payload; an attempt builds at most `N` pages and ends `Yielded`, the item goes back to the queue with its attempt budget intact and the next attempt continues after the stored pages
- a `retry_failed` item rebuilds the pages that had ended without a result when it was asked for; a page that fails again while the item runs stays a stored page and is not rebuilt by a later attempt of the same item (otherwise a continuation would loop)
- a version of identical source bytes in the same project reuses stored page rows of `cmp-profile/3` that are not `RENDER_FAILED`; a different project never does

## Failure/idempotency/security cases
- a manifest with both source roles is refused with a typed reason; a manifest with neither is `page_profile_source_unreadable` as before
- a yield or a re-run builds nothing twice (the unique keys of the table and `ON CONFLICT DO NOTHING` hold)
- no page row of another project is read or copied

## Rollback / feature flag
The comparison modules are off by default (`AUDITMANAGER_COMPARISON_MODULES`, ADR-0025 decision 23). No stored row changes; a revert of the commits restores the old behaviour.

## Handoff
- changed files: `src/auditmanager/comparison/profile/{source,builder,repository,reuse}.py` (`reuse.py` new), `src/auditmanager/comparison/profile_queue/handler.py`; tests `tests/integration/comparison/test_upload_to_series_end_to_end.py` (new), `tests/integration/comparison/profile_queue/{conftest.py, test_a_long_version_is_built_in_bounded_attempts.py, test_identical_versions_reuse_profiles.py}`, `tests/unit/comparison/profile/{test_source_roles.py, test_reuse_donors.py}`, `tests/unit/comparison/profile_queue/test_page_profile_handler_unit.py`; this file and the report `docs/program/CMP-C1-FIX-C.md`; commits `3649d801`..`c0f3da8c` and the docs commit after them on `agent/cmp-c1-fix-c`.
- commands/results: `git diff --check 00afbc21..HEAD` exit 0; `tests/unit/comparison` 1248 passed; `tests/integration/comparison` in ONE process 566 passed; `tests/integration/ingest/comparison_pdf` + `comparison_batch` 298 passed; `tests/integration/composition` 1955 passed, 5 skipped; whole `tests/unit` 4985 passed, 76 skipped; `tests/contract` minus the three `D-220` files 1310 passed, 19283 subtests; the end-to-end test is red on the base (`page_profile_source_unreadable`, 3 attempts each) and green after; every new guard is shown red under a quoted mutation and green after restoring (report sections 2 to 4).
- known limits: the attempt bound (30 pages) is a constant derived from one real set; a retry item no longer builds again a page that failed again inside the same item; reuse is per attempt and uncoordinated between worker slots; the matrix build and the worker's footprint are not bounded here; no `make gate` (no contract, migration, infrastructure, dependency or composition-root change).
- integration notes: no contract, migration, dependency, web, `jobs/`, `documents/` or composition-root file changed; new work failure reason `page_profile_source_ambiguous`; a `page_profile` item may be `queued` between two attempts of one version (its attempts are `superseded`), which every reader of the live item already counts as live; the dedupe key, the payload and the attempt budget are unchanged.
