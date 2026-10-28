# Task CMP-VIEWER-01 — the tiles of a sheet pair (overlay, A, B) and the overlay viewer widget

## Outcome
`streamComparisonPairTile` answers a PNG tile of one sheet pair: `mode` `overlay` (page A and page B warped onto A's
canvas with `how_compared.transform`, the selected mask layers drawn over them), `a` or `b` (one page alone), at the
pyramid `level`, `column` and `row`, with `layers` and `align_blocks`. The A and B tiles come from the page-profile
pyramid through the existing page-profile reader (stored levels 2 and up; levels 0 and 1 rendered on request in a
ceilinged child), so **the API process never calls PDFium**. The mask is one bit-packed blob per non-`same` result
(wave brief C1 section 4, format 1), decoded with a bound, reduced across levels by the **maximum** (a one-pixel
change never disappears when the sheet is zoomed out), and cached within a byte budget. A level, column or row outside
the pyramid, a pair without a result and a mask that does not exist answer `404`; every request costs a bounded amount
of work. The web widget `comparison-viewer` (plan 1.1: «Наложение» / «Рядом», «шторка», zoom and pan over tiles, layer
toggles, change boxes, «Совмещать блоки», «Отличия: N», the channel strip) is exported from its index for
CMP-VC-UI-01 and is not mounted on a route.

## Depends on
- CMP-SEAL-C1 (merged on `integration/compare-modules`; the operation, the schemas and the tables), CMP-PROFILE-01
  (page profiles, the stored pyramid, `PageProfileReader`, `TileRenderer`), CMP-VERSION-MARK-01 (merged; no dependency of
  substance). Parallel with CMP-MATRIX-01 and CMP-ENGINE-01 (the mask codec is ENGINE's, wave brief C1 section 4 item 2)

## Frozen inputs
- domain contract: `contracts/domain/v1/**` at the wave base (prefixes `ctp`, `ctn`, `csp`, `cpr` are in the catalogue)
- API contract: `contracts/api/v1/openapi.json` `1.10.0`, 131 paths / 148 operations / 432 schemas
- analysis/comparison/event contract: ADR-0025 decisions 8, 9, 10, 16, 20, 23 and the addenda of 2026-10-27 and
  2026-10-28; wave brief `docs/program/dispatch/CMP-WAVE-C1.md` section 4 (mask format 1, the result `jsonb`, the
  transform, `aligned_blocks`); `docs/program/CMP-SEAL-C1.md` sections 3, 4 and 9
- migration head: `0039_comparison_core`
- base commit: `d11c13fd` on `integration/compare-modules`

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: `tests/integration/composition/test_router_answers.py` (`SEALED_STUB_GETS`, `SEALED_STUB_QUERY`), `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py` (`SEALED_STUB_ADDRESSED`) and `tests/integration/composition/test_comparison_core_stub_operations.py` (`WIRED`); `web/tests/unit/styles/screens.ts` (the census block of the widget's module stylesheet)
- enumerator_owner: CMP-VIEWER-01 for the row of `streamComparisonPairTile` only and for the block of `comparison-viewer` only (wave brief section 1, plan 4.0 rules 1 and 2); merge order MATRIX, ENGINE, VIEWER
- totality_query: `grep -n "comparison-sheet-pairs\|STUB_PAIR}/tile\|streamComparisonPairTile" tests/integration/composition/test_router_answers.py tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py tests/integration/composition/test_comparison_core_stub_operations.py` prints no stub row of the tile; `grep -n "comparison-viewer\|ComparisonViewer" web/tests/unit/styles/screens.ts` prints the block

## Captured premise evidence
- premise: contract `1.10.0`, 131 paths / 148 operations / 432 schemas, head `0039_comparison_core`; the lane printed them before any edit and would have STOPPED if they differed. The tile operation is a sealed stub on the base.

### P-01 — the base facts the lane re-read before any edit
- captured_at: 2026-10-28
- command: `.venv/bin/python -c "import json;d=json.load(open('contracts/api/v1/openapi.json'));print('contract',d['info']['version'],len(d['paths']),'paths',sum(1 for p in d['paths'].values() for m in p if m in('get','post','put','patch','delete')),'operations',len(d['components']['schemas']),'schemas',len(d['components']['schemas']['ErrorCode']['enum']),'error codes')"; cat VERSION; grep -n '^revision: str' db/migrations/versions/20261028_0039_comparison_core.py; git rev-parse HEAD`
- captured_output:
  ```text
  contract 1.10.0 131 paths 148 operations 432 schemas 27 error codes
  0.9.0
  79:revision: str = "0039_comparison_core"
  d11c13fd01f431bb081ad9f984fc6a3dc615b39e
  ```
- interpretation: equal to the premise of the wave brief (`1.10.0`, 131 / 148 / 432, head `0039_comparison_core`), so the lane did not STOP

### P-02 — the tile operation is a sealed stub and its adapter is one class of `adapters.py`
- captured_at: 2026-10-28
- command: `grep -n "class ComparisonPairTileAdapter" -A8 src/auditmanager/bootstrap/adapters.py; grep -n "comparison_pair_tiles" src/auditmanager/bootstrap/composition.py`
- captured_output:
  ```text
  5807:class ComparisonPairTileAdapter:
  5808-    """`CMP-VIEWER-01` replaces the body."""
  5809-
  5810-    _DEPENDENCY = "comparison_pair_tiles"
  5811-
  5812-    def read_tile(
  5813-        self, *, sheet_pair_id: str, mode: models.ComparisonPairTileMode, level: int, column: int, row: int, layers: Sequence[models.ComparisonLayer], align_blocks: bool
  5814-    ) -> bytes:
  5815-        return _comparison_unavailable(self._DEPENDENCY)
  504:        comparison_pair_tiles=ComparisonPairTileAdapter(),
  ```
- interpretation: the adapter has no state and no dependency; the lane gives it the session factory and the object store the way `VersionPageAdapter(sessions, blob_store=store)` has them (one constructor line, `composition.py:504`), and the router (`api/routers/comparison_pair_tiles.py`) already parses `layers` into `ComparisonLayer` values and bounds `level` 0..12, `column` and `row` 0..4095

### P-03 — the page-profile pyramid the pair tiles read (CMP-PROFILE-01)
- captured_at: 2026-10-28
- command: `grep -n "FIRST_STORED_TILE_LEVEL\|MAX_ON_REQUEST_TILE_LEVEL\|TILE_PX\|^TILE_LIMITS\|TILE_SLOTS\|SLOT_WAIT_SECONDS" src/auditmanager/comparison/profile/limits.py src/auditmanager/comparison/profile/tiles.py`
- captured_output:
  ```text
  src/auditmanager/comparison/profile/limits.py:25:    "FIRST_STORED_TILE_LEVEL",
  src/auditmanager/comparison/profile/limits.py:28:    "MAX_ON_REQUEST_TILE_LEVEL",
  src/auditmanager/comparison/profile/limits.py:43:    "TILE_PX",
  src/auditmanager/comparison/profile/limits.py:81:TILE_PX: Final[int] = 512
  src/auditmanager/comparison/profile/limits.py:84:FIRST_STORED_TILE_LEVEL: Final[int] = 2
  src/auditmanager/comparison/profile/limits.py:85:MAX_ON_REQUEST_TILE_LEVEL: Final[int] = FIRST_STORED_TILE_LEVEL - 1
  src/auditmanager/comparison/profile/limits.py:110:TILE_LIMITS: Final[ChildLimits] = ChildLimits(768 * MIB, 300, 120.0)
  src/auditmanager/comparison/profile/limits.py:121:        "tile_px": TILE_PX,
  src/auditmanager/comparison/profile/limits.py:122:        "first_stored_level": FIRST_STORED_TILE_LEVEL,
  src/auditmanager/comparison/profile/tiles.py:11:**Bounded.** At most :data:`TILE_SLOTS` children run at once (the production host has 4 GiB beside the
  src/auditmanager/comparison/profile/tiles.py:12:API, the database and the object store); a request that cannot get a slot within :data:`SLOT_WAIT_SECONDS`
  src/auditmanager/comparison/profile/tiles.py:32:__all__ = ["DEPENDENCY", "SLOT_WAIT_SECONDS", "TILE_SLOTS", "TileRenderer"]
  src/auditmanager/comparison/profile/tiles.py:35:TILE_SLOTS: Final[int] = 2
  src/auditmanager/comparison/profile/tiles.py:36:SLOT_WAIT_SECONDS: Final[float] = 30.0
  src/auditmanager/comparison/profile/tiles.py:48:        slots: int = TILE_SLOTS,
  src/auditmanager/comparison/profile/tiles.py:49:        slot_wait_seconds: float = SLOT_WAIT_SECONDS,
  ```
- interpretation: tiles are 512 px; levels 2 and up are stored in the archive of `profile_blob_id`; levels 0 and 1 are rendered on request by a ceilinged child, two at a time; the pair tile is a client of that reader and adds no PDFium call to the API process

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/comparison/tiles/**`
- `src/auditmanager/comparison/public.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/api/routers/ports.py`
- `tests/unit/comparison/tiles/**`
- `tests/integration/comparison/tiles/**`
- `tests/integration/composition/test_router_answers.py`
- `tests/integration/composition/test_an_absent_parent_is_not_an_empty_page.py`
- `tests/integration/composition/test_comparison_core_stub_operations.py`
- `web/src/widgets/comparison-viewer/**`
- `web/tests/unit/comparison/viewer/**`
- `web/tests/unit/styles/screens.ts`
- `docs/program/CMP-VIEWER-01.md`
- `docs/program/tasks/CMP-VIEWER-01.md`

## Lane resources
- foundation_instance: `auditmanager-cmp-viewer-01`
- postgres_port: `57860`
- s3_api_port: `61860`
- s3_console_port: `61861`
- postgres_db: `auditmanager_cmp_viewer_01`
- s3_bucket: `auditmanager-cmp-viewer-01`

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `pyproject.toml`, `uv.lock`, `docs/program/P02_LOCK.json`, `web/package.json`, `web/package-lock.json`, `web/FRONTEND_LOCK.json`
- `web/src/shared/api/**` (the generated client is read, never edited), global styles (`web/src/app/globals.css`), `web/src/_app/**`, routes, `screen-registry.ts`, the journey manifest
- `src/auditmanager/comparison/profile/**`, `src/auditmanager/comparison/engine/**`, `src/auditmanager/comparison/matrix/**`, `src/auditmanager/comparison/series/**`, `src/auditmanager/comparison/work/**`, `src/auditmanager/storage/**`, `src/auditmanager/jobs/**`, `src/auditmanager/api/routers/comparison_pair_tiles.py` (the lane reads them; a needed change is a STOP to the FIX slot)
- `bootstrap/adapters.py` outside the body of `ComparisonPairTileAdapter` (and the imports it needs); `bootstrap/composition.py` outside the one constructor line of that adapter (and its import)

## Non-goals
- the codec of the mask (`comparison/engine/mask_codec.py` is ENGINE's); the reader written here follows the text of wave brief section 4 item 1 and is replaced by `decode_mask` at the integrator's call
- the pair rows and the results (SERIES and ENGINE write them; the tests insert the rows they need directly), the text tint of the original (`text_color`, not in the contract), the AI panel «Изменения в листе», the «Спецификация по позициям» view, the evidence banner
- the screens that mount the widget, its route, the menu entry and the Russian sentences for the new refusal reasons (CMP-VC-UI-01); the pair data is a prop of the widget, read by the page
- any eviction or deletion of a stored blob (ADR-0025 decision 9)

## Deliverables
- `src/auditmanager/comparison/tiles/**`: the bounded mask reader, the max-reduction, the tile geometry, the transform and the warp of page B, the aligned blocks, the layer palette, the composition, the source of page tiles with its bounded caches, the repository of the pair and its result, the reader behind the operation
- `ComparisonPairTileAdapter` (replaces the stub body), one constructor line in `composition.py`, the rows of the three composition enumerators, the appended names of `comparison/public.py`
- `web/src/widgets/comparison-viewer/**` (index, `ui/*.tsx`, one `*.module.css`, `model/*.ts`) and its census block in `web/tests/unit/styles/screens.ts`
- unit tests (mask reader, reduction, geometry, warp, composition, widget logic and markup), integration tests (database, object store, the composed application over HTTP), mutation proofs, the measured cost of one tile request on a 2A0-sized synthetic mask
- the report `docs/program/CMP-VIEWER-01.md`

## Required tests
- command: `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src .venv/bin/python -m pytest -q tests/unit/comparison/tiles tests/integration/comparison/tiles tests/integration/composition`
- expected: all pass; the tile operation answers `404` for an absent pair and no stub row of it remains
- command: `npm --prefix web run lint -- --quiet && npm --prefix web run typecheck && npm --prefix web run test -- --run tests/unit/comparison/viewer tests/unit/styles tests/guards`
- expected: exit 0; every rule of the widget's stylesheet is reached by a census screen

## Integration contract
The integrator can rely on: `GET /comparison-sheet-pairs/{id}/tile` returns `image/png` of at most 512 x 512 pixels (smaller at the right and bottom edges of the level); `mode=a` is the page-profile tile of the pair's older page, `mode=b` is the newer page warped onto the older page's canvas (its own pyramid when the pair has no older page or no transform), `mode=overlay` needs a result with a transform and answers `404` without one; the grid of a tile is the pyramid of page A's page profile, so a tile of any mode at one `(level, column, row)` covers the same canvas square; `layers` empty means no difference layer; the reader never starts a process of its own (levels 0 and 1 go through the page-profile `TileRenderer`). The mask reader is the single seam to replace by `decode_mask`; the transform convention is `x' = a x + c y + e`, `y' = b x + d y + f` for `[a, b, c, d, e, f]`. The widget takes a `ComparisonSheetPair` (from `getComparisonSheetPair`) and fetches tiles through the generated client.

## Failure/idempotency/security cases
- a mask with a wrong magic, format, layer count, a plane over 40 Mpx or a body whose inflated length differs from `8 * h * ceil(w / 8)` is refused (`storage_integrity_error`), and an oversized body is never inflated beyond the declared length
- a level, column or row outside the page's pyramid, an absent pair, a pair without a result or without a page for the mode, a result without a transform asked for as an overlay, a missing mask where the status needs one: `404 not_found`
- the work of one request is bounded: at most 16 source tiles of page B, at most 4 composes at once, a mask cache of a fixed byte budget with one decode per mask at a time
- the API process imports no PDF library (a static scan and a fresh interpreter)
- the tile is read-only: no write, no blob published, no process killed

## Rollback / feature flag
The module flag (`comparison/modules.py`) governs the screens that will mount the widget; the lane adds no flag. Rollback is not merging the lane: the operation then answers the sealed `503` and the widget is not imported by any route.

## Handoff
- changed files: (written in the last commit)
- commands/results: (written in the last commit)
- known limits: (written in the last commit)
- integration notes: (written in the last commit)
