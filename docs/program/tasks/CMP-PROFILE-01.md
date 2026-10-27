# Task CMP-PROFILE-01 — page profiles of a version: words, vector lines, stamp, ink mask, scan flag, stored preview and thumbnail, tiles

## Outcome
For a stored version a function builds, page by page, the raw deterministic profile in `comparison_page_profile`
(a ULID `cpr_` row with a unique content key): words with boxes and vector lines (pdfplumber), the stamp zone with the
sheet number and the sheet title, a 36 dpi ink mask, the scan flag, the annotation count and hashes, the page content
Merkle; a stored preview PNG and thumbnail PNG (and the tile levels 2 and up) are published as blobs; tile levels 0 and 1
are rendered on request in a ceilinged child process, never inside the API process. Every render and extraction runs in a
child under a kernel ceiling (768 MiB; 1024 MiB for the child that runs pdfplumber; 300 s CPU; 600 s wall) and any end
without a result is a `needs_review` profile with reason `RENDER_FAILED` for that one page. A page over 40 Mpx at the
registration dpi is refused, not rendered. The five sealed reads `listVersionPageProfiles`, `getVersionPageProfile`,
`streamVersionPagePreview`, `streamVersionPageThumbnail`, `streamVersionPageTile` answer from what the worker stored.

## Depends on
- CMP-SEAL-C0 (merged on `integration/compare-modules`, tip `0990de4b`), CMP-FIXTURES-01 (the synthetic corpus and its
  answer keys), CMP-MEASURE-01A (`docs/program/compare/MEASURE-RENDER-01.md`, the ADR-0025 addendum of 2026-10-27)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at the wave base (prefix `cpr` is in the catalogue)
- API contract: `contracts/api/v1/openapi.json` `1.9.0`, 115 paths / 130 operations / 351 schemas
- analysis/comparison/event contract: ADR-0025 decisions 2, 8, 9 and the addendum of 2026-10-27 (child ceilings 768 / 1024 MiB,
  any end without a result is `RENDER_FAILED`, 40 Mpx cap, registration dpi rule, store preview and thumbnail and tile levels
  2 and up, levels 0 and 1 on request in a ceilinged child)
- migration head: `0038_comparison_foundation`
- base commit: `cc3dd36b` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`) and `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_ADDRESSED`, `EXPECTED_ADDRESSED`)
- enumerator_owner: CMP-PROFILE-01 for the five rows of its operations only (wave brief section 1 rule 4)
- totality_query: `grep -n "page-profiles\|VersionPage" tests/integration/composition/test_router_answers.py tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` prints no stub row of the five operations

## Captured premise evidence
- premise: contract `1.9.0`, 115 paths / 130 operations / 351 schemas, head `0038_comparison_foundation`; the lane printed them before any edit and would have STOPPED if they differed

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0038_comparison_foundation.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.9.0 115 paths 130 operations 351 schemas 27 error codes
  0.9.0
  81:revision: str = "0038_comparison_foundation"
  cc3dd36b5b05b28ed0232107c8d0a437e304f07b
  ```
- interpretation: equal to the premise of the wave brief (`1.9.0`, 115 / 130 / 351, head `0038_comparison_foundation`), so the lane did not STOP

### P-02 — facts of `comparison_page_profile` the design rests on (migration `0038`)
- captured_at: 2026-10-28
- command: `grep -n "uq_comparison_page_profile\|ck_comparison_page_profile_reason\|write_once\|am_check_comparison_page_profile" db/migrations/versions/20261028_0038_comparison_foundation.py`
- interpretation: `UNIQUE (version_uid, content_key)` and `UNIQUE (version_uid, page_number, algo_version)`; the status is `ready | needs_review | refused` and `reason` is NULL exactly when the status is `ready`; `profile` is a frozen jsonb object and the three blob references are write-once; a trigger refuses a page beyond the version's `page_count`. Two identical pages of one version (the VS-1 duplicate sheet) therefore need a content key that includes the page number, and a profile row is written once, with its blobs already published

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/profile/**`
- `src/auditmanager/analysis/geometry/render.py`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/routers/version_pages.py`
- `scripts/recovery/grant_classification.py`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/unit/comparison/profile/**`
- `tests/integration/comparison/profile/**`
- `docs/program/tasks/CMP-PROFILE-01.md`
- `docs/program/CMP-PROFILE-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-profile-01`
- postgres_port: `57750`
- s3_api_port: `61750`
- s3_console_port: `61751`
- postgres_db: `auditmanager_cmp_profile_01`
- s3_bucket: `auditmanager-cmp-profile-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`
- `src/auditmanager/comparison/work/**` (CMP-WORK-01), `src/auditmanager/storage/**` (CMP-STORAGE-PARTS-01), `src/auditmanager/ingest/**`, `src/auditmanager/jobs/**`
- `src/auditmanager/bootstrap/composition.py` except the one argument list of `version_pages=VersionPageAdapter(...)`: the file is CMP-WORK-01's in this wave (wave brief section 2), the adapter cannot reach the database without it, and the integrator resolves the overlapping hunk
- global styles, `web/**`

## Non-goals
- the sheet matrix, the comparison engine, registration and the diff (CMP-MATRIX-01, CMP-ENGINE-01); overlay tiles of differences (CMP-VIEWER-01)
- the queue: the lane exposes a function that builds the profiles of one version and does not import CMP-WORK-01's code; the work kind is registered by the integrator from the function's name
- the stamp fields that need the document (stage and section proposals, the «Изм.» history of the set): CMP-INGEST-01
- OCR: a page with no text layer is flagged `scan` and is never given invented text
- eviction or deletion of any blob (ADR-0025 decision 9)

## Deliverables
- `src/auditmanager/comparison/profile/**`: limits and the registration dpi rule, the child program (render, extract), the ceilinged child runner, the stamp reader, the content Merkle, the profile pack (JSON, ink mask, tile levels 2 and up), the builder of a version's profiles, the reader behind the five operations
- the full-page renderer in `analysis/geometry/render.py` under `PDFIUM_LOCK`, exported from `analysis/public.py`
- `VersionPageAdapter`, the `VersionPagePort` rows, `version_pages.py`; the five stub rows removed from the two enumerators and `comparison_page_profile` from `SEALED_NOT_YET_WRITTEN`
- unit tests (pure parts and the children) and integration tests (database and object store), mutation proofs, measurements on the synthetic corpus
- the report `docs/program/CMP-PROFILE-01.md`

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/profile tests/integration/comparison/profile`
- expected: all pass; `tests/integration/composition` answers 404 for an absent page profile and no stub row remains for the five operations

## Integration contract
The integrator can rely on: `auditmanager.comparison.public.build_version_page_profiles(...)` builds and stores every missing
profile of a version (idempotent by `(version, page, ALGO_VERSION)`), one page per child; `read_page_profile(...)` returns the
typed raw profile (words, lines, ink mask, stamp, flags) of a stored page for the matrix and engine lanes; a page the child
could not finish is stored `needs_review` with reason `RENDER_FAILED` and never becomes «Совпадает». `VersionPageAdapter(sessions,
blob_store=store)` is the wiring of the five reads; the one-line hunk is in `composition.py` (see Forbidden hotspots).

## Failure/idempotency/security cases
- a page over 40 Mpx at the registration dpi is refused with reason `PAGE_TOO_LARGE`, not rendered
- an overrun child (address space, CPU, wall, a signal) yields `RENDER_FAILED` for that page only
- the API process never imports PDFium for tiles: levels 0 and 1 run in a child started with a bare environment
- a repeated build writes nothing new (the unique keys), and a row is never updated after insert (frozen columns)
- a path, file name, display number, «шифр» or sheet number is never an identity

## Rollback / feature flag
The comparison module flag (`comparison/modules.py`) governs the screens that read these operations; the lane adds no flag. Rollback is not merging the lane; the tables are empty until a worker builds profiles.

## Handoff
- changed files: the new package `src/auditmanager/comparison/profile/**` (with `child/**`), `analysis/geometry/render.py` and `analysis/public.py` (the full-page renderer and its export), `bootstrap/adapters.py` (`VersionPageAdapter`), **one line** of `bootstrap/composition.py`, `comparison/public.py` (appends), `api/routers/version_pages.py` (docstring), `scripts/recovery/grant_classification.py` (one name), the two composition enumerators (five stub rows), `tests/unit/comparison/profile/**` (11 files, 159 tests), `tests/integration/comparison/profile/**` (2 files, 18 tests), this file and `docs/program/CMP-PROFILE-01.md`; the full list is `git diff --name-only cc3dd36b..HEAD`
- commands/results: the report's section 7 (unit 159 passed; integration selection 281 passed and 1 skipped; contract battery minus the three `D-220` files; 22 mutation proofs, each shown red and then green) and section 6 (time, address space and bytes per page on the synthetic corpus and, numbers only, on the real set)
- known limits: the report's section 10; the first three are that the stamp reader is unmeasured on real stamps, that tiles of levels 0 and 1 rendered on request differ from the whole raster's cut in 0.13 % of the pixels, and that a failed page is stored (frozen) and rebuilt only by `retry_failed` or a new `ALGO_VERSION`
- integration notes: the report's section 9; first, the one `composition.py` line is `CMP-WORK-01`'s file in this wave (take its file, re-apply `version_pages=VersionPageAdapter(sessions, blob_store=store)`), then register `build_version_page_profiles` as a work kind with payload `{"version_uid": ...}`
