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
