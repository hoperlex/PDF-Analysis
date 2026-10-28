# CMP wave C1 — the version-comparison core after CMP-SEAL-C1

Integrator: the CMP integrator on `integration/compare-modules` (seal merged on top of `origin/dev` `038a1cea` and the
debt rows D-260..D-264). Plan `COMPARE-MODULES-PLAN.md` §1.1, §3.2, §4 wave C1, §4.0; ADR-0025 and its addendum;
the seal's report `docs/program/CMP-SEAL-C1.md` (operations, tables, the per-lane list in §9 — binding); the
original's version comparison: `docs/program/compare/ORIGINAL-VERSION-COMPARISON-INVENTORY.md`,
`ORIGINAL-UNREAD-SOURCES.md`; the corpus `fixtures/comparison/` with answer keys; the real measurement set
`.local/comparison-measure/13AV-RD-EM2-PA/` (numbers only, never to a model, never committed).

## 1. Common rules
The rules of `docs/program/dispatch/CMP-WAVE-C0.md` §1 apply unchanged (task file first, base facts printed — now
contract `1.10.0`, 131/148/432, head `0039_comparison_core`; shared `.venv` and `web/node_modules` read-only; own
containers; wiring hunks minimal; no contract or migration change — STOP to the FIX slot; ADR safety rules with
mutation proofs; light acceptance; never kill others' processes; no push, no merge). Additionally: **after your last
commit run the whole `tests/unit` and `tests/contract` minus `D-220`**, not only your directories.

## 2. Lanes

| Lane | Result | Own paths | Ports |
| --- | --- | --- | --- |
| CMP-MATRIX-01 | the effective matrix (seal §9): algorithmic build over page profiles (max-weight assignment, thresholds 0.55/0.35/0.20, rules v1.2, groups ▤, duplicates ⧉, splits ◫⇉ with parts coverage, bridges), manual edits with base revision and undo, AI-link layer read, staleness, orphaned edits; a work kind for preparation | `src/auditmanager/comparison/matrix/**`, its tests | 57840/61840/61841 |
| CMP-ENGINE-01 (XL) | per-sheet comparison in a ceilinged child (ADR-0025 decisions 8, 15 + addendum): registration on the downsampled raster (OpenCV), the eight channels, region classes, layers, text changes with numbers, statuses and forcing reasons, content-Merkle cache, bit-packed masks only for non-`same`; measured on the real set (time/RSS/bytes gate) | `src/auditmanager/comparison/engine/**`, its tests | 57850/61850/61851 |
| CMP-VIEWER-01 | `streamComparisonPairTile` and the `comparison-viewer` widget (§1.1 of the plan: «Наложение»/«Рядом», «шторка», zoom, layers, change boxes, «Совмещать блоки», difference list, channel strip) | `src/auditmanager/comparison/tiles/**`, `web/src/widgets/comparison-viewer/**`, their tests | 57860/61860/61861 |
| CMP-SERIES-01 (after MATRIX, ENGINE) | series of adjacent transitions as comparison work; sheet pairs and results; permit and parts post-phases; verdict strings; pause/resume/cancel/finish; stores `compare_after_preparation` and removes the adapter's refusal | `src/auditmanager/comparison/series/**`, `src/auditmanager/ingest/comparison_batch/**` and `src/auditmanager/ingest/comparison_pdf/**` (that flag only), `src/auditmanager/comparison/work/**` (series id only), tests | 57870/61870/61871 |
| CMP-VC-OVERVIEW-01 (after SERIES) | `getComparisonOverview`, `getComparisonQueueSummary` | `src/auditmanager/comparison/overview/**`, tests | 57880/61880/61881 |
| CMP-VC-UI-01 (after OVERVIEW) | screens «Проекты и этапы» (steps 1–3, 5) and «Сравнение листов» (transitions, matrix, «Порядок версий», upload dialogs), route, menu entry, A-12 edits of the version-scoped screen; Russian sentences for the new reasons; the new enums in `TRANSLATED_SCHEMAS`; the read-only «Сравнение» block in «Очередь» | the web paths of plan §4 C1 plus `web/src/widgets/execution-queue/**` (that block only) | none |
| CMP-MEASURE-01 (after ENGINE) | the engine on the real set: time, RSS, bytes per pair; statuses vs the original's for that set; then delete the set | `docs/program/compare/MEASURE-ENGINE-01.md`, `tools/measure/**` | none |

## 3. Order and merge order
SEAL-C1 (done) → (MATRIX ∥ ENGINE ∥ VIEWER) → SERIES → OVERVIEW → VC-UI-01; MEASURE-01 after ENGINE. Merge order for
wiring files: MATRIX, ENGINE, VIEWER, SERIES, OVERVIEW, VC-UI-01. A FIX lane closes the wave.

## 4. Pair evidence interface v1 (binding for ENGINE, VIEWER, SERIES)

ENGINE and VIEWER are developed in parallel; this section fixes what one writes and the other reads. A lane that finds
it wrong or insufficient STOPs and reports; it does not invent a second format.

1. **Mask blob, format 1** — one per non-`same` result (`comparison_sheet_pair_result.mask_blob_id`), written once by
   ENGINE in the worker. Bytes: a 16-byte little-endian header `struct.pack("<4sBBHII", b"AMCM", 1, 8, 0, width_px,
   height_px)`, then `zlib.compress(numpy.packbits(planes, axis=-1, bitorder="big").tobytes(), 6)`, where `planes` is
   a `bool` array of shape `(8, height_px, width_px)` in the order of the contract enum `ComparisonLayer`: `main`,
   `light_elements`, `color_change`, `line_style`, `moved`, `within_tolerance`, `noise`, `service_zones`. The grid
   covers the canvas of page A (`ComparisonCanvas`) at `how_compared.dpi`: `width_px = ceil(width_pt * dpi / 72)`,
   likewise height; pixel `(x, y)` is the canvas square from `(x, y) * 72 / dpi` points, origin top left. A plane is at
   most 40 Mpx (ADR-0025 decision 9); a decoder refuses a wrong magic, format, layer count, a size over the cap and a
   body whose length after decompression differs from `8 * height_px * ceil(width_px / 8)` (decompress with a limit
   — never an unbounded `zlib.decompress` of stored bytes).
2. **Codec ownership.** ENGINE owns `src/auditmanager/comparison/engine/mask_codec.py` (`MASK_FORMAT = 1`,
   `encode_mask`, `decode_mask`) and commits it, with its tests, as its **second commit** (after the task file).
   VIEWER writes its reader against this text, with tests that build blobs per this text; at its merge turn (after
   ENGINE has merged) VIEWER replaces its reader by `decode_mask` and adds one round-trip test across both.
3. **Result `jsonb`** (`comparison_sheet_pair_result.result`), written by ENGINE, copied verbatim by SERIES into
   `getComparisonSheetPair`: `{"format": 1, "canvas": ComparisonCanvas, "differences": [ComparisonDifference],
   "text_changes": [ComparisonTextChange], "service_notes": [ComparisonServiceNote], "how_compared":
   ComparisonHowCompared, "aligned_blocks": [{"box_a": [x0, y0, x1, y1], "dx_pt": float, "dy_pt": float}], "mask":
   {"format": 1, "dpi": int, "width_px": int, "height_px": int} | null}` — every member that has a contract schema is
   validated by the generated model of that schema before the row is written (the caps of the schema hold:
   2000 differences, 2000 text changes, 500 service notes). `how_compared.transform` is the affine `[a, b, c, d, e, f]`
   mapping page B points onto page A points. `aligned_blocks` is what «Совмещать блоки» uses: with `align_blocks=true`
   the viewer draws the part of page B inside `box_a` shifted by `(-dx_pt, -dy_pt)` after the transform. Status,
   reasons, confidence, flags and channels live in their own columns, as sealed.
4. **Entry points for SERIES** (ENGINE, exported from `src/auditmanager/comparison/engine/__init__.py`): a function
   that, for a project and two page profiles (either may be absent for `added`/`removed`), returns the result
   identity — from the cache when the content key exists, otherwise computed in the ceilinged child and written
   (blob first, then the row; a row never names a blob that was not written) — and a `comparison_work` handler of
   kind `pair_result` appended to `HANDLER_FACTORIES`, with an enqueue helper whose dedupe key is a function of the
   project and the two profile identities only. SERIES chooses which to use; ENGINE does not write
   `comparison_sheet_pair`.
5. **The real set** `.local/comparison-measure/13AV-RD-EM2-PA/` is measured by code only: no lane opens, reads or views
   its PDFs or any raster made from them with a tool that shows content to the model (no Read of those files or of
   images rendered from them); only numbers (time, RSS, bytes, counts, statuses) are recorded. Nothing from it is
   committed.

## 5. Integrator records (2026-10-28)

1. **`result.part` confirmed.** The result `jsonb` of brief §4 item 3 may carry `part` (`area_a_pt`, `coverage_a`,
   `reliable`) for a split sheet, as `CMP-ENGINE-01` writes it; `CMP-SERIES-01` uses it for parts coverage, the
   viewer ignores it.
2. **`CMP-VIEWER-01` merged `b399d102` (ENGINE) into its branch** at the integrator's instruction (brief §4 item 2)
   and switched to `decode_mask`.
3. **Order deviations.** ENGINE merged before MATRIX (MATRIX was still running; ENGINE touches no adapter or stub
   register). `CMP-VC-UI-01` was dispatched in parallel with SERIES from `9f5f4912`, against the sealed contract, with
   the SERIES notes sent by message (its report records them); `CMP-VC-OVERVIEW-01` from `c228cf2e`.
4. **Not dispatched:** `CMP-MEASURE-01` (the original never compared the real set — it is an audit project there —
   so «statuses vs the original» is not measurable; run the chain profiles → matrix → series for time, RSS and bytes,
   then delete `.local/comparison-measure/13AV-RD-EM2-PA/`) and the wave's FIX lane (items in the integrator handoff).
5. **Owner ruling, 2026-10-29 (poll answer «Эта сессия закрывает C1»).** The CMP integrator session pdf-analysis-13
   had spent its AGENTS §7.1 budget (it resumed from a context summary); the owner waived §7.1 for this wave only:
   the same session merges OVERVIEW and VC-UI-01, dispatches MEASURE-01 and the FIX lane, writes the wave report and
   then hands the role over (handoff `.local/handoff/integrator-2026-10-28-cmp.md`).
