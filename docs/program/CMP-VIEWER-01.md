# CMP-VIEWER-01 — the tiles of a sheet pair and the overlay viewer widget

Written 2026-10-28 by the Sonnet lane `CMP-VIEWER-01` (branch `agent/cmp-viewer-01`, base `d11c13fd` on `integration/compare-modules`, merged once with `b399d102` = `CMP-ENGINE-01` at the integrator's call; nothing pushed). Task file: [`tasks/CMP-VIEWER-01.md`](tasks/CMP-VIEWER-01.md). Decisions cited are those of [`ADR-0025`](../architecture/adr/ADR-0025-comparison-modules.md) (decisions 8, 9, 10, 16, 20, 23 and the addenda of 2026-10-27 and 2026-10-28); the plan is [`dispatch/COMPARE-MODULES-PLAN.md`](dispatch/COMPARE-MODULES-PLAN.md) sections 1.1, 3.2 and 4 wave C1; the binding interface is [`dispatch/CMP-WAVE-C1.md`](dispatch/CMP-WAVE-C1.md) section 4; the seal is [`CMP-SEAL-C1.md`](CMP-SEAL-C1.md) (section 9, row `CMP-VIEWER-01`); the page tiles it reads are [`CMP-PROFILE-01.md`](CMP-PROFILE-01.md)'s; the mask codec is [`CMP-ENGINE-01.md`](CMP-ENGINE-01.md)'s.

## 1. Result

`streamComparisonPairTile` is served. It answers one PNG of at most 512 x 512 pixels of a sheet pair: `mode=overlay` (page A and page B on A's canvas, the chosen mask layers painted over them), `mode=a` (page A's page-profile tile, byte for byte) or `mode=b` (page B warped onto A's canvas with `how_compared.transform`), at the pyramid `level`, `column` and `row`, with `layers` and `align_blocks`. The tiles of A and B come from the page-profile pyramid (stored levels 2 and up from the archive; levels 0 and 1 rendered on request by the page-profile reader in a ceilinged child), so **the API process never calls PDFium** and starts no process of its own. The mask is decoded with the engine's bounded `decode_mask` and reduced across levels by the **maximum**, so a one-pixel change is drawn at every level. A level, column or row outside the pyramid, a pair without a result, an overlay without a registration, and a mask the result names that the store does not hold are `404`; a mask or a result that is not what it says is `422 storage_integrity_error`; a request that needs more of page B than one request may read, or cannot get a compose slot, is `503 dependency_unavailable` (`comparison_pair_tiles`).

The widget `web/src/widgets/comparison-viewer` shows a `ComparisonSheetPair` (as `getComparisonSheetPair` answers it): «Наложение» / «Рядом», «шторка», zoom and pan over the tiles, the eight layer toggles under the Russian names of `ComparisonLayer`, «рамки отличий», «Совмещать блоки», «Отличия: N» (a click focuses the box; a click on the sheet picks one; ← and → walk the list), the channel strip, «Текст: N изменений» with the changed numbers marked, «Служебные зоны и пометки», «Как сравнивалось». It is exported from its index for `CMP-VC-UI-01` and mounted on no route.

## 2. Base facts, printed before any edit

`contract 1.10.0 131 paths 148 operations 432 schemas 27 error codes`, `VERSION` `0.9.0`, head `0039_comparison_core`, base `d11c13fd01f431bb081ad9f984fc6a3dc615b39e` (`P-01` of the task file). They equal the wave brief's premise, so the lane went on. The lane changed no contract, no migration, no dependency and no lock file. The sealed tile operation was a stub answering `503` (`P-02`).

The brief named the original's local clone `/root/projects/PDF-proverka`; it does not exist on this host (the handoff of 2026-10-27 records that it disappeared). The original was read read-only from `raw.githubusercontent.com/SU10KAZ/PDF-proverka/23f379fd2d5aeb7e7bddb735650e7393c68d4e42/<path>` into the session's scratch directory (no write to any clone, nothing executed); the line numbers in section 6 are those files'.

## 3. What was built

Own paths: `src/auditmanager/comparison/tiles/**`, `web/src/widgets/comparison-viewer/**`, their tests, the census block of `web/tests/unit/styles/screens.ts`, and the wiring hunks of the brief.

| File | What it holds |
| --- | --- |
| `tiles/reader.py` | `PairTileReader.read_tile`: the plan (which pages, which grid, which `404`), the compose slot, the warp of B, the overlay, the layer masks, the encode |
| `tiles/masks.py`, `tiles/cache.py` | `MaskStore`: the engine's `decode_mask`, one decode at a time, single-flight, inflated planes kept within a byte budget (`ByteCache`) |
| `tiles/reduction.py` | the **maximum** reduction of a bit-packed plane to a tile: the rows of a block OR-ed as bytes first, only the strip left is unpacked; any ratio between the mask grid and the raster |
| `tiles/grid.py` | `PageGrid` (the pyramid of page A's profile) and `Affine` (the transform, PDF order) |
| `tiles/warp.py` | page B laid onto A's tile grid: source level, source tiles counted before any is fetched, `cv2.warpAffine` bilinear |
| `tiles/aligned.py` | «Совмещать блоки»: erase the old place, paste the shifted block, the pixels the layers are withheld from |
| `tiles/compose.py` | the darker of the two pages, the layers in solid colour, the hatch of `service_zones`, PNG decode (size read from the header first) and encode |
| `tiles/source.py` | `ProfileTiles`: page A/B tiles as arrays, from the cached archive or the page-profile reader (which owns the child); bounded caches of decoded tiles, archives and profile rows |
| `tiles/repository.py`, `tiles/result_view.py` | the one query (pair + result) and the strict reading of the result `jsonb` |
| `tiles/errors.py`, `tiles/limits.py` | the typed refusals and every number with the decision that sets it |
| `bootstrap/adapters.py`, `composition.py`, `comparison/public.py` | `ComparisonPairTileAdapter(session_factory, *, blob_store)` replaces the stub body; **one line** of `composition.py`; `PairTileReader` appended to `public.py` |
| three composition enumerators | the tile leaves `SEALED_STUB_GETS` and `SEALED_STUB_ADDRESSED` and joins `WIRED`; `SEALED_STUB_QUERY` keeps its query (it makes the 5xx sweep reach the handler, as the page tile's does since `CMP-PROFILE-01`; the brief said to remove it, this is the one deviation); the one assertion that read `503` for an absent pair reads `404` |
| `web/src/widgets/comparison-viewer/` | `model/` (pyramid arithmetic equal to the server's, view state reducer, difference filters, tile loader, request planning, Russian labels, number marks), `ui/` (island, view, pane, difference list, evidence panels, one `*.module.css`) |

## 4. The pair-evidence interface as implemented

Conventions the other lanes should know; each is held by a test.

1. **Grid.** A tile of any mode at one `(level, column, row)` covers the same canvas square: the pyramid of page A's page profile (512 px tiles; level `n + 1` is level `n` reduced by two). `mode=b` is B *on A's canvas*, as the original's (`sheet_tile`, `version_comparison.py:437-441`); a pair with no older page or no transform has no canvas, and its `b` is B's own tile (the widget's `rasterSize` prop supplies B's size).
2. **Transform.** `[a, b, c, d, e, f]` is the PDF order: `x' = a*x + c*y + e`, `y' = b*x + d*y + f`, B points onto A points (`tiles/grid.py`; ENGINE's note 3 says the same). B is sampled at the source level whose pixels are one to two per output pixel, bilinear.
3. **Aligned blocks** (ENGINE's note 4, brief section 4 item 3): with `align_blocks=true` B's part inside `box_a` (the block's place on A after the transform) is drawn moved by `(-dx_pt, -dy_pt)`; the old place is erased, the new place takes the darker pixel, and the layers are withheld from both places (the mask describes the unaligned pages).
4. **Mask.** Decoded by `decode_mask`; the grid is checked against the result's own `mask` description and against the canvas (a pixel of slack); any ratio between the mask's dpi and the raster's is handled (a tile pixel covers `2**level * mask_dpi / raster_dpi` mask pixels; every mask pixel falls in exactly one block, so the maximum loses none). `layers` empty means no layer. A result **without a mask blob** (a `same` pair, or an annotation-only or fields-only difference, ENGINE's note 2) is drawn without layers, never an error; a blob the result names and the store does not hold is `404`.
5. **Result members read:** `canvas`, `how_compared.{dpi, transform}`, `aligned_blocks`, `mask`; the others, and the extra member `part`, are ignored. A present member that is wrong is `422`; an absent `transform` means no overlay (`404`), never an identity.

## 5. What one tile request costs

Per request: one indexed query (pair + result); page A's tile (one decode, 512 x 512 x 3); page B's source tiles, **at most 16 and usually 1 to 4** (counted before any is fetched; an identity transform reads one), each read at most once from the cached archive or rendered once in a child (two at a time, by the page-profile reader); one warp; per selected layer one reduction over a window of the packed plane; one PNG encode. At most 4 tiles are composed at once in the process, a request that cannot get a slot in 30 s answers `503`; at most one mask is inflated at a time; the caches hold 96 MiB of inflated masks, 48 MiB of decoded tiles, 32 MiB of archives.

**Measured on one 2A0-sized synthetic mask** (`PYTHONPATH=src .venv/bin/python tests/unit/comparison/tiles/measure_pair_tile_cost.py`; 1682 x 1189 mm at the 113 dpi of the registration rule = 7483 x 5290 px, 39.59 Mpx a plane; rectangles in every layer, 5 000 and 20 000 lone pixels in `within_tolerance` and `noise`, the stamp zone in `service_zones`; the blob is 187 352 bytes, the inflated body 39 611 520 bytes; Python 3.12.3, numpy 2.5.4, host load 2 to 18 on 8 vCPU):

| What | Figure |
| --- | --- |
| cold decode of the blob (engine's `decode_mask`) | 0.08 s; resident memory 100 MiB before, 139 MiB after, **peak 176 MiB** (+75 MiB: the engine inflates in one call, so the 40 MB body is held twice for a moment; the viewer's own streaming reader, replaced at the integrator's call, peaked at +41 MiB — hence `DECODE_SLOTS = 1`) |
| reducing all eight layers to the tile, worst of three tiles | level 0: 11 ms; level 1: 19 ms; level 2: 24 ms; level 3: 36 ms; level 4 (the whole sheet): 51 ms (earlier runs on a busier host: 9 to 138 ms) |
| the rest of a 512 x 512 tile (warp from four source tiles, overlay, paint, encode) | warp 0.8 ms, overlay and paint 10 ms, PNG encode 6 ms (34 KB) |
| one tile unpacked the naive way | a 40 Mpx plane is 39.6 MB; `test_pair_tile_cost_bounds.py` holds the reduction under 8 MiB of allocation at the top of the pyramid (a mutation that unpacks the plane first allocates 40 MB) |

**End to end on the A1 world of the integration tests** (VS-1 page 5, 6623 x 4678 px, host load about 18; `PairTileReader` in process, the lane's PostgreSQL and MinIO, a mask with 200 lone pixels in each of the eight layers): overlay level 3 cold (profile rows, A and B archives, mask decode, compose) **623 ms**, the same level warm **60 ms** (median of four tiles), level 2 first tile 96 ms; overlay level 0 cold, with A and B tiles rendered on request in children, **1 893 ms**, the same tile again 18 ms; `mode=a` level 3 (a stored tile) 3 ms, level 0 (one child render) 137 ms. The level 0 and 1 cost is the children (about 0.45 s each under that load, two at a time); before the lane read only the source tiles a transform needs, an identity-transform `b` at level 0 rendered four.

## 6. The original's behaviours ported, with `file:line` at `23f379fd`

Files: `V` = `frontend/static/js/version-comparison-viewer.js`, `Z` = `frontend/static/js/version-comparison-zoom.js`, `T` = `backend/app/services/version_comparison/tiles.py`, `R` = `backend/app/api/routers/version_comparison.py`, `E` = `backend/app/services/version_comparison/engine.py`.

| Behaviour | Original | Here |
| --- | --- | --- |
| reduction takes the maximum so a small change survives zooming out | `T:1-8`, `_reduce` `T:55-65`, `overlay_tile` `T:75-92` | `tiles/reduction.py` |
| tile 512 px, level = reduction by `2**L` | `T:21`, `T:29-30` | `tiles/grid.py`, `model/pyramid.ts` |
| the overlay: unchanged ink keeps its colour (the darker of A and B), difference layers painted over | `source_overlay_tile` `T:250-289` (min at `T:258`) | `tiles/compose.py` |
| layer palette; later layers over earlier; zone hatch | `E:30-42`, `compose` `E:410-423` | `tiles/compose.py` (`main` is one plane here, so one colour where the original had `a_only` red and `b_only` blue) |
| `b` is B on A's canvas by the stored matrix; `a` is A | `sheet_tile` `R:408-445` (`R:437-441`) | `mode=a`, `mode=b` |
| `align_blocks` redraws B and does not paint the stale layers over the moved blocks | `R:432-433`, `R:439-440`; `T:241-246`, `T:270-275` | `tiles/aligned.py`, `reader._compose` |
| modes «Наложение» / «Рядом»; a second click on the chosen mode returns to the previous one | `modes` `V:278`, `setMode` `V:261-267`, buttons `V:77` | `model/viewer-state.ts` `mode` |
| «шторка» is a checkbox over a mode, off in «Рядом»; the divider starts at the left edge, dragging it right opens the lower sheet; the top layer is clipped left of it | `V:79-80`, `V:281-304`, `V:99`, `V:118-121` | reducer `swipe`, `ui/sheet-pane.tsx` (`clip-path: inset(0 0 0 p%)`), a range input |
| eight layers, defaults: five on, «Перемещено», «В пределах допуска», «Шум» off | `LAYERS` `V:15-24` | `model/labels.ts` `DEFAULT_LAYERS` |
| «рамки отличий» off by default; «Совмещать блоки (N)» | `V:268`, `V:89-90` | toolbar, the count in the label |
| «Отличия: N», ← and →, the shifts and the look of lines hidden behind two toggles with their counts | `V:134-144`, `SHIFT_CLASSES` `V:9`, `onKey` `V:575-578` | `model/differences.ts`, `ui/difference-list.tsx` |
| region class labels | `CLASS_LABELS` `V:10-14`, `classLabel` `V:605` | `REGION_CLASS_LABELS` (the contract's class words) |
| a click on the sheet picks the change under it | `pickChangeAt` `V:528-560` | `differenceAt`, action `pick` |
| channel strip «Проверено / Не проверено / причины»; scan note | `V:62-73` | `ChannelStrip`, `SCAN_NOTE` |
| «Текст: N изменений»; «Служебные зоны и пометки» and the warning sentence; «Как сравнивалось» | `V:188`, `V:201`, `V:210`, `V:227` | `evidence-panels.tsx` |
| Ctrl/Cmd + wheel zooms about the pointer (×1.15), the wheel alone pans (Shift sideways), drag pans, double click fits | `Z:103-125`, `Z:11` | `ui/comparison-viewer.tsx` |
| fit leaves 2 %; zoom from a quarter of the fit to 64 times it | `Z:37`, `Z:67` | `model/pyramid.ts` |
| the tile level follows the zoom: `floor(log2(1 / zoom))` | `Z:86-90` | `levelForZoom` |

**Deviations, on purpose.** The viewer opens on the overlay, the swipe off and «Совмещать блоки» off; the original opens on B with the swipe on and parked at the left edge (`V:257`, `V:281`) and alignment on (`V:256`). An overlay that hid a moved block by default is not what an engineer should find unasked. Not ported: the text tint `text_color` (not in the contract), the AI panel «Изменения в листе» and its evidence banner (wave C2), «Спецификация по позициям», «Только изменённые листы» (the page that lists the pairs owns it; the widget takes `navigation`), the `identical_content` shortcut (a `same` pair draws the two pages with no layers).

## 7. Safety rules and mutation proofs

ADR-0025 decision 8 (nothing heavy in the API process, ceilinged children), 9 (40 Mpx, bounded decode, the API never calls PDFium, no eviction), 10 (nothing written; no process killed), 16 (any one role: the router's, unchanged), 20 (the viewer draws raw deterministic evidence only; no AI text rewrites it), 23 (the module flag governs the screens that will mount the widget). Each guard below was shown red under the quoted mutation and the file restored with `git checkout` (the runner printed `restored: clean` every time).

| # | Guard | Mutation | Red |
| --- | --- | --- | --- |
| M1, M19, I1 | the maximum: a one-pixel change survives every level | the rows OR replaced by the first row; the columns max replaced by a nearest pixel | 1 + 9 unit failures (A1-sized lone pixels at six positions, the definition at every level, the ratio and edge cases); the integration test of the pixel at levels 0 to 4 |
| MB1 | bounded decode: a hostile body is never inflated past its header | `decode_mask`'s bounded call replaced by `zlib.decompress` (the engine's file, restored) | 4 failures, among them `test_a_hostile_body_is_never_inflated_beyond_what_the_header_declares` (64 MiB of zeros in 60 KB behind a 64-byte header: allocation under 4 MiB) |
| MB2, MB4 | the 40 Mpx cap and the header fields each refuse for their own reason | the cap raised to 4e12; the magic check removed | `[over_cap]`, `[magic]` |
| M3 | no PDFium in the API process | `import pypdfium2` in `reader.py` | the static scan and the fresh-interpreter proof (`LOADED []`) |
| M4, I4 | out-of-range level, column, row is `404` | `tile_box` stops checking column and row | the grid test; `test_what_does_not_exist_is_not_found` |
| I5b | a pair never compared has no overlay (`404`) | both guards removed (each alone stays green: one stands behind the other) | `test_what_does_not_exist_is_not_found` |
| MB5 | a result without a mask draws no layers, never an error | a missing blob raises `404` | the same test |
| I13b, I14 | a mask that is not the sheet's grid, or has a wrong header field, is `422` | the size check and the grid check removed together; (on the lane's first reader) the magic check | `test_a_damaged_result_or_mask_is_an_integrity_error_not_a_picture` (10 cases, one header field or one member wrong each) |
| I7 | only the chosen layers are painted | all eight reduced | the pixel test (the unchosen layer's pixel appears) |
| M6, I6, I9 | `align_blocks`: the old place erased; layers withheld over both places | the erase removed; the suppression removed | unit and integration alignment tests |
| M8 | the transform order is the PDF's | `apply` swaps `b` and `c` | the convention test and the inverse test |
| M12, I12 | a request reads at most 16 source tiles of B | the budget stops counting | the unit bound test; the strip-shaped transform answers `503`, not a picture |
| I11 | a request that cannot get a compose slot is refused | the refusal removed | `test_a_request_that_cannot_get_a_compose_slot_...` |
| I15, M10 | one decode of a mask for a dozen concurrent tiles | the cache bypassed; single-flight removed | the counting-store test; the thread test |
| M16, M18, M20, M21 | byte budget of the caches; tile size check; source level; layer order | each removed or changed | one or more unit failures each |
| W1 to W10 | the reducer, the filters, the loader, the markup | swipe in «Рядом»; a default layer; shifts shown; the request cap; layer order; the revoke on eviction; the retry bound; the aligned control; the warning sentence; number marks | each red in `web/tests/unit/comparison/viewer` |
| W11, W12, W13 | the style rules | the census block disabled; a colour literal in the module; `:not()` added | `names every colour-bearing rule that NO rendered screen reaches`; the colour-literal test of `styling-layer.test.ts`; `names every selector it declined to evaluate` |

Three guards first survived their mutation and were repaired in the same commits: the 40 Mpx test took its side from the constant it was supposed to hold (`MAX_PLANE_PIXELS` is a literal in the test now); the overlay-without-result and mask-size guards each have a second guard behind them (so the proof removes both), and the three header cases of the integration test were built from an otherwise good A1 blob so that only the field under test can refuse them.

## 8. Commands and results

Run in the worktree with `AUDITMANAGER_LEGACY_PROMPTS_REPO=/nonexistent PYTHONPATH=$PWD/src`; the lane's `.env` loaded for the container suites (`set -a; . ./.env`; a first attempt of the composition files without it ended in errors of `this suite needs the lane's .env loaded`, was stopped by its own PID and is not counted).

| Run | Result |
| --- | --- |
| `git diff --check d11c13fd..HEAD` | clean |
| `pytest -q tests/unit/comparison/tiles` | **83 passed** |
| `pytest -q tests/integration/comparison/tiles` (lane PostgreSQL and MinIO, the real children) | **14 passed** |
| `pytest -q tests/integration/comparison/tiles tests/integration/composition`, whole directory, tree `c17fa4df` before the merge | **1984 passed, 4 skipped, 0 failed** in 52 min 15 s |
| the same tiles directory and the five wired composition files, tree after the last change before the merge | 195 passed, 2 skipped |
| `pytest -q tests/integration/comparison/tiles` and the six composition files the lane edits or depends on (`test_router_answers`, `test_an_absent_parent_is_not_an_empty_page`, `test_comparison_core_stub_operations`, `test_comparison_stub_operations`, `test_every_port_implementation_is_whole`, `test_composition_root`), merged tree `5d6e57c9` | **217 passed, 2 skipped** in 24 min 57 s |
| `pytest -q tests/unit`, whole, merged tree `5d6e57c9` | **4665 passed, 76 skipped** in 4 min 43 s |
| `pytest -q tests/contract` minus the three `D-220` files, merged tree | **1310 passed, 19283 subtests passed** in 2 min 27 s |
| `npm --prefix web run lint -- --quiet` | exit 0 |
| `npm --prefix web run typecheck` | exit 0 |
| `npm --prefix web run test -- --run tests/unit/comparison/viewer tests/unit/styles tests/guards` | **32 files, 440 tests passed** (the viewer's 56, the style census and layer tests, all 22 guard files including `rendered-language`) in 4 min |

The whole `tests/integration/composition` was **not** re-run after the merge of `b399d102` (52 minutes on this host; the merge touched no composition file); the five files the lane edits or depends on were, with the lane's tiles directory.

## 9. Contracts and hotspots

* **New or changed contracts: none.** `git diff --name-only b399d102..HEAD -- contracts db pyproject.toml uv.lock docs/program/P02_LOCK.json web/package.json web/package-lock.json web/FRONTEND_LOCK.json web/src/shared web/src/app web/src/_app` prints nothing.
* **Outside the lane's own paths, by the brief's wiring rule:** `bootstrap/adapters.py` (the body of `ComparisonPairTileAdapter`), `bootstrap/composition.py` (**one line**), `comparison/public.py` (two appended lines), the three composition enumerators.
* The merge commit `c5f52b2b` brings `b399d102` (ENGINE) in without a conflict; no file of the lane was resolved by hand.
* `web/node_modules` is the shared read-only symlink; vitest and the Vite config bundler write their transient files to its `.vite-temp` and `.vite` directories (the tool's own cache, no package changed); the link is removed before the last commit.

## 10. Limits and risks

1. **The viewer's grid is derived** from `canvas` and `how_compared.dpi` (`ceil(points * dpi / 72)`), which equals the server's pyramid only while the engine compares at the registration dpi of page A (both come from `registration_dpi`). The server does not assume it (it resamples a mask of another dpi), the widget does: a pair compared at another dpi shows missing tiles (`404`, counted as absent). `rasterSize` overrides it.
2. **A transform that needs more than 16 source tiles of B** (a strong anisotropic squeeze, a large rotation with a strong shrink) answers `503`; registration by anchors and phase correlation does not produce one. More than 64 aligned blocks on one tile do the same.
3. **Levels 0 and 1 cost children**: about 2 s for a cold overlay tile on a loaded host, up to four B tiles at two children at a time; neighbouring tiles share B's source tiles through the cache.
4. **The engine's `decode_mask` peaks at +75 MiB** for a 2A0 mask (it inflates in one call); one decode at a time keeps that to one such peak. A streaming decode (the lane's first reader, +41 MiB) is a change in ENGINE's file.
5. **Bilinear sampling** of B when its pixels are one to two per output pixel; a rotated or scaled B is slightly softer than the page profile's own tile, which is why `mode=a` is passed through untouched.
6. **The reduction is exact for the mask, not for the pages**: levels 0 and 1 of A and B come from clip renders that differ from the whole raster's cut in 0.13 % of the pixels (`CMP-PROFILE-01` §3.6); the mask is the engine's evidence and is exact.
7. **Not run:** the live journey (`e2e:pc01`) — no screen was added or changed; the full `make gate` — `R-135`; a browser: the pointer, wheel and resize handlers of the island are code the static render harness cannot fire (the reducer, the loader and the markup they drive are tested; the handlers are not).
8. The widget does not persist tile bytes (no `localStorage`, `sessionStorage` or IndexedDB); object URLs are revoked on eviction and on unmount.

## 11. Notes for the next lanes

**`CMP-SERIES-01`** copies the engine's result into `getComparisonSheetPair` verbatim; the tile reads `result.canvas`, `how_compared.{dpi, transform}`, `aligned_blocks`, `mask` from the `jsonb` and the pages from the **pair's own** `page_a_profile_id` / `page_b_profile_id` (a result is shared by pairs of equal content, so its pages may be another content-equal page's). A pair with a result must carry both profile ids.

**`CMP-VC-UI-01`** mounts `ComparisonViewer` (`pair`, optional `rasterSize` from `getVersionPageProfile` for an added or removed sheet, optional `navigation` for «‹ лист / лист ›» and «✕ Закрыть»). When it renders the widget on a screen it must register `ComparisonLayer`, `ComparisonSheetStatus` and `ComparisonChannelState` in `TRANSLATED_SCHEMAS` of `rendered-language.guard.test.ts` with their markers; the widget itself renders the Russian words and no enum value (a test holds that). `REASON_WORDS` in `evidence-panels.tsx` is a stopgap for the eight forcing reasons the original lists; unknown codes show «причина без описания (КОД)». The widget uses no shared state block (`EmptyState` would be a "branch" that guard requires one of its own screens to render). The island is `'use client'`; the view is pure, so a screen test can render it.

**Integrator.** Merge order MATRIX, ENGINE, VIEWER: the lane's `adapters.py`, `composition.py`, `public.py` and enumerator hunks are line-local. `npm --prefix web run api:verify` needs no re-run for this lane (the generated client is untouched).

## 12. Items for the FIX slot

1. `streamComparisonPairTile` (and `streamVersionPageTile`) send no `Cache-Control` or `ETag`; the original sends `private, max-age=3600` (`R:446`). A tile of a pair is immutable; the router is not this lane's.
2. `VersionPageAdapter` and `ComparisonPairTileAdapter` each build a `TileRenderer` (two children at a time each): the host-level bound is four, not two. One shared renderer needs a second constructor line in `composition.py`.
3. `decode_mask` could stream its inflation into a preallocated buffer (the lane's first reader did, peak +41 MiB instead of +75 MiB for 2A0).
4. The contract could carry the raster size of A's pyramid (`ComparisonCanvas` or `ComparisonPairPage`), so the widget need not derive it.
5. The text of the brief says the stub tile row leaves `SEALED_STUB_QUERY`; it was kept (section 3).

## 13. Resources

Lane containers `auditmanager-cmp-viewer-01-{postgres,s3}` on ports 57860 / 61860 / 61861, brought up with `make up FOUNDATION_PYTHON=/usr/bin/python3.12` and migrated with `make migrate`; `df -h /` was read before every container start and every long run (1.8 to 3.1 GiB free, above the 1.5 GiB stop). The containers and the two volumes were removed at the end (below).
