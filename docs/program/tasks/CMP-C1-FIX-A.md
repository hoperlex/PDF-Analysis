# Task CMP-C1-FIX-A — the FIX slot of wave C1, backend: engine reason form, split-part registration, one-process integration runs, tile headers, one tile renderer, streamed mask decode, optional content and rectangles in the page profile

## Outcome
Eight items found by the wave-C1 lanes are closed, each with a test that fails before the change and passes after it
(a quoted mutation shows the guard red, then green):

1. the engine writes the contract's form of the reason of an unchecked channel (`UNCHECKED_CHANNEL_<CHANNEL>`, never a
   colon), its `ALGO_VERSION` is bumped, the series view keeps its mapping only as tolerance for stored rows;
2. each part of a split sheet registers onto its own region of the older sheet, so the parts do not overlap and the ink
   coverage of the split is computed; the answer keys of the corpus still hold;
3. `pytest tests/integration/comparison` passes in ONE process (every comparison integration test ends the live work
   items it creates);
4. `streamComparisonPairTile` and `streamVersionPageTile` send `Cache-Control: private, max-age=3600` and an `ETag`
   derived from the identity of the page or pair and the tile parameters (headers only: the contract declares no `304`);
5. one `TileRenderer` is built in the composition root and shared by `VersionPageAdapter` and `ComparisonPairTileAdapter`;
6. `decode_mask` inflates into a preallocated buffer with a bounded decompressor and keeps every refusal; the peak is
   measured before and after with the viewer's tool;
7. the page profile's content Merkle covers the optional-content configuration that affects the page, the profile's
   algorithm version is bumped, and a visibility-only change is no longer `same`;
8. the profile keeps rectangle edges (and straight curve segments if cheap) as line segments in its vector lines,
   within the extraction child's 1024 MiB ceiling (measured on the corpus and, by code only, on the real set).

## Depends on
- CMP-SEAL-C1, CMP-MATRIX-01, CMP-ENGINE-01, CMP-VIEWER-01, CMP-SERIES-01, CMP-VC-OVERVIEW-01, CMP-VC-UI-01 (all merged on
  `integration/compare-modules`), CMP-PROFILE-01, CMP-PROFILE-QUEUE-01, CMP-WORK-01

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at the wave base
- API contract: `contracts/api/v1/openapi.json` `1.10.0`, 131 paths / 148 operations / 432 schemas (no `304`, no
  `If-None-Match` parameter on the two tile operations)
- analysis/comparison/event contract: ADR-0025 decisions 8, 9, 15 and its addenda; wave brief
  `docs/program/dispatch/CMP-WAVE-C1.md` sections 4 and 5; the reports `CMP-ENGINE-01.md` (sections 5, 9, 11),
  `CMP-PROFILE-01.md`, `CMP-VIEWER-01.md` (section 12), `CMP-SERIES-01.md` (section 9), `CMP-MATRIX-01.md`
- migration head: `0039_comparison_core` (no table or column is added or changed)
- base commit: `0e867b12` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: contract `1.10.0`, 131 paths / 148 operations / 432 schemas, head `0039_comparison_core`; the engine writes `UNCHECKED_CHANNEL:<channel>` (`status.py:91`), the two tile routers answer a `WireResponse` with only `Content-Type` and `Content-Length`, `composition.py` builds `VersionPageAdapter` and `ComparisonPairTileAdapter` without a shared renderer, `decode_mask` inflates through a decompressor object that is read to the end into one buffer, the content Merkle names no `/OCProperties`, and the extraction child keeps `page.lines` only.

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-29
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0039_comparison_core.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.10.0 131 paths 148 operations 432 schemas
  0.9.0
  79:revision: str = "0039_comparison_core"
  0e867b12cbbfbed1e048e2142748f6286edc6a50
  ```
- interpretation: equal to the premise of the wave brief (`1.10.0`, 131 / 148 / 432, head `0039_comparison_core`), so the lane did not STOP

### P-02 — the places the first six items change, at the base
- captured_at: 2026-10-29
- command: `grep -n 'UNCHECKED_CHANNEL' src/auditmanager/comparison/engine/child/status.py; grep -n '^ALGO_VERSION' src/auditmanager/comparison/engine/child/settings.py src/auditmanager/comparison/profile/limits.py; grep -n 'WireResponse(' src/auditmanager/api/routers/comparison_pair_tiles.py src/auditmanager/api/routers/version_pages.py; grep -n 'VersionPageAdapter(\|ComparisonPairTileAdapter(' src/auditmanager/bootstrap/composition.py; grep -n 'zlib.decompress\|decompressobj' src/auditmanager/comparison/engine/mask_codec.py`
- captured_output:
  ```text
  91:        kept.append(f"UNCHECKED_CHANNEL:{name}")
  src/auditmanager/comparison/engine/child/settings.py:17:ALGO_VERSION: Final[str] = "cmp-engine/1"
  src/auditmanager/comparison/profile/limits.py:55:ALGO_VERSION: Final[str] = "cmp-profile/1"
  src/auditmanager/api/routers/comparison_pair_tiles.py:62:        return WireResponse(
  src/auditmanager/api/routers/version_pages.py:42:    return WireResponse(
  498:        version_pages=VersionPageAdapter(sessions, blob_store=store),
  504:        comparison_pair_tiles=ComparisonPairTileAdapter(sessions, blob_store=store),
  26:refused after one small allocation, never inflated (an unbounded ``zlib.decompress`` of stored bytes is the failure
  191:    decompressor = zlib.decompressobj()
  ```
- interpretation: the engine's reason, the two algorithm versions, the headerless tile responses, the two adapter constructor lines and the decoder are where the reports say they are; the engine's `ALGO_VERSION` is in the content key (`engine/key.py`), so a bump recomputes stored results

### P-03 — the profile's Merkle and vector lines, at the base
- captured_at: 2026-10-29
- command: `grep -c OCProperties src/auditmanager/comparison/profile/child/page_merkle.py; grep -n 'page.lines\|"lines"' src/auditmanager/comparison/profile/child/extract_job.py`
- captured_output:
  ```text
  0
  77:        lines = page.lines
  103:            "lines": lines,
  113:            "lines": len(lines),
  ```
- interpretation: the Merkle names no `/OCProperties` (`CMP-ENGINE-01` section 9 item 4) and the extraction keeps `pdfplumber` `lines` only (section 11 item 4)

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/engine/**`
- `src/auditmanager/comparison/series/views.py`
- `src/auditmanager/comparison/profile/**`
- `src/auditmanager/comparison/tiles/**`
- `src/auditmanager/api/routers/comparison_pair_tiles.py`
- `src/auditmanager/api/routers/version_pages.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/bootstrap/adapters.py`
- `tests/unit/comparison/**`
- `tests/integration/comparison/**`
- `tests/integration/composition/**`
- `docs/program/CMP-C1-FIX-A.md`
- `docs/program/tasks/CMP-C1-FIX-A.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-c1-fix-a`
- postgres_port: `57900`
- s3_api_port: `61900`
- s3_console_port: `61901`
- postgres_db: `auditmanager_cmp_c1_fix_a`
- s3_bucket: `auditmanager-cmp-c1-fix-a`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `web/**`, `infra/**`, the `Makefile`, `scripts/**`
- `src/auditmanager/jobs/**`, `src/auditmanager/comparison/{work,matrix,overview,profile_queue}/**`, `src/auditmanager/comparison/public.py`
- `bootstrap/composition.py` outside the renderer lines (the one construction and the two constructor arguments); `bootstrap/adapters.py` outside the constructor parameters of the two tile adapters
- `src/auditmanager/api/routers/ports.py` and every router file but the two tile routers
- every `conftest.py` outside `tests/unit/comparison/` and `tests/integration/comparison/`

## Non-goals
- the decisions recorded by the integrator in the wave report: the matrix build stays in the worker process; the comparison operations answer whatever the module flag (only the worker and wave C2's AI commands are gated); `comparison_edits_limit` stays reachable only below the edge; the ZIP reader and `__MACOSX/` wait for wave C3
- a `304` answer to `If-None-Match` (the contract declares none): the two routes send headers only
- a contract, migration, dependency, web or `jobs/` change: a lane that needs one STOPs and reports
- the other items of the lanes' reports (the key disagreements of `CMP-ENGINE-01` section 5, stream-level overlay separation, the series reasons the seal did not register)

## Deliverables
- item 1: `engine/child/status.py` (the reason), `engine/child/settings.py` (`ALGO_VERSION`), `series/views.py` (the mapping stays as tolerance), tests
- item 2: the registration of a split part in `engine/child/{job,registration}.py` and `engine/service.py` as needed, tests against the corpus' answer key of E05
- item 3: fixtures in `tests/integration/comparison/` (every test ends the live work items it creates), one run of the whole directory
- item 4: `api/routers/version_pages.py` and `api/routers/comparison_pair_tiles.py` (the headers), tests
- item 5: `bootstrap/composition.py` (one renderer), `bootstrap/adapters.py` (a `tiles` parameter of `ComparisonPairTileAdapter`), tests
- item 6: `engine/mask_codec.py` (`decode_mask` into a preallocated buffer), tests, the peak before and after
- item 7: `profile/child/page_merkle.py`, `profile/limits.py` (`ALGO_VERSION`), tests
- item 8: `profile/child/extract_job.py` (rectangle edges and straight curve segments), `profile/limits.py` (`ALGO_VERSION`), tests, the extraction peak
- the report `docs/program/CMP-C1-FIX-A.md` and this file's Handoff

## Required tests
- command: `git diff --check`; `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q --basetemp=$PWD/.pytest-tmp tests/unit/comparison`; `.venv/bin/python -m pytest -q tests/integration/comparison` in ONE process (own containers, `.env` loaded); the whole `tests/integration/composition` directory; after the last code commit the whole `tests/unit` and `tests/contract` minus `tests/contract/test_cp00_candidate.py`, `test_validate_bootstrap.py`, `test_cp00_final_state.py` (`D-220`)
- expected: every command exits 0 with the counts in the report; every new guard is shown red under a quoted mutation

## Integration contract
- the engine's stored reasons are contract-shaped (`^[A-Z][A-Z0-9_]{2,63}$`); rows stored under `cmp-engine/1` are not touched (the key changes, so the pair is computed again on the next series), and the series view keeps mapping a stored colon form
- the profiles are recomputed by a new preparation under the new `cmp-profile` algorithm version; the old rows stay and the listing shows the current algorithm's only
- the two tile operations answer the same bytes and the status as before, with two more headers; no `304`
- the composition root builds one `TileRenderer` and hands it to both tile adapters (at most `TILE_SLOTS` tile children for the whole API process)
- `decode_mask` answers the same arrays and refuses the same blobs as before

## Failure/idempotency/security cases
- a hostile mask body is never inflated past its header (the existing bomb tests hold on the new decoder)
- a page whose optional-content configuration cannot be read is not hashed as if it had none (the Merkle refuses like its other budgets)
- a profile extraction that passes the ceiling ends `RENDER_FAILED` as before; the rectangle edges add to the lines, so the peak is measured

## Rollback / feature flag
The comparison modules are off by default (`AUDITMANAGER_COMPARISON_MODULES`, ADR-0025 decision 23). The algorithm-version bumps are the rollback boundary: stored rows of the old versions are untouched and a revert of the commits restores the old keys.

## Handoff
- changed files: (written at the end of the lane)
- commands/results: (written at the end of the lane)
- known limits: (written at the end of the lane)
- integration notes: (written at the end of the lane)
