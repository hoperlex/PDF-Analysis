# CMP wave C1 — the version-comparison core: report

Integrator of the CMP waves: `pdf-analysis-70` (formerly `pdf-analysis-13`, `-12`, planner `4d`). Branch
`integration/compare-modules`, published tip the branch `publish/cmp-c1` (wave C1 without the C2 seal), fast-forwarded onto `origin/dev` (`origin/dev` before it: `f774cdde`, merged at `e01c7835`). Plan
`docs/program/dispatch/COMPARE-MODULES-PLAN.md`, ADR `docs/architecture/adr/ADR-0025-comparison-modules.md` (both
addenda), wave brief `docs/program/dispatch/CMP-WAVE-C1.md` (§4 the pair evidence interface, §5 the integrator's
records and the owner's waiver of AGENTS §7.1 for this wave).

## Facts after the wave
- Contract `1.10.0`, 131 paths / 148 operations / 432 schemas, 27 error codes (no new code); migration head
  `0039_comparison_core` (the first migration of the project with a data step: every active `0035` sheet-pair approval
  becomes a manual matrix edit, `source = 'migrated_sheet_link'`); `VERSION` unchanged (`0.9.0`).
- No new dependency. The module flag `ProductVersion.comparison_modules` stays `none` by default; with it off the
  three `0035` operations behave as before, the C1 operations answer (they are reads and deterministic commands, no
  model call), and the worker runs no comparison item.
- What a user gets when the flag names `versions`: the menu item «Сравнение версий» with the tabs «Проекты и этапы»
  (steps 1, 2, 3, 5 of the original; 4, 6, 7 are wave C2) and «Сравнение листов» (the transition summary, the sheet
  matrix with drafts, «Порядок версий», the upload dialogs), the overlay viewer, and the read-only «Сравнение» block in
  «Очередь».

## Lanes merged (each report under `docs/program/<ID>.md`)
| Lane | Merge | What it built |
| --- | --- | --- |
| CMP-SEAL-C1 | `3e41ffc8` | contract 1.10.0, 18 sealed operations, migration 0039 with the 0035 data step, carried prose and reasons |
| CMP-ENGINE-01 | `b399d102` | per-sheet comparison in a 768 MiB child: registration, eight channels, layers, region classes, forcing reasons, statuses; content-keyed cache; mask format 1; `pair_result` work kind |
| CMP-MATRIX-01 | `40c3ee12` | the sheet matrix: max-weight assignment, thresholds 0.55/0.35/0.20, rules v1.2, groups, duplicates, splits, bridges; effective read model with manual edits and undo; `matrix_build` work kind; six operations |
| CMP-VIEWER-01 | `9f5f4912` | `streamComparisonPairTile` from the profile pyramid and the mask (max reduction across levels), the `comparison-viewer` widget |
| CMP-SERIES-01 | `c228cf2e` | series of adjacent transitions, verdict codes, parts and permit post-phases, three work kinds, nine operations, `compare_after_preparation` |
| CMP-VC-OVERVIEW-01 | `cd3afcd7` | `getComparisonOverview` (set-based, bounded: 14 statements for 1…100 sets) and `getComparisonQueueSummary` |
| CMP-VC-UI-01 | `0e867b12` | the screens of «Сравнение версий», upload dialogs, A-12 edit of the version-scoped screen, the «Очередь» block |
| CMP-C1-FIX-A | `9861c9f9` | contract reason form `UNCHECKED_CHANNEL_<CHANNEL>`, split-part registration, one-process comparison tests, tile `Cache-Control`/`ETag`, one shared tile renderer, streamed mask decode (+75 → +41 MiB on 2A0), optional content in the page Merkle, rectangle and path segments in the profile; `cmp-engine/3`, `cmp-profile/3` |
| CMP-C1-FIX-B | `6db7db23` | the overview's group rule, words, chip and actions on the screens; the viewer's Russian words, reason words and markers; the «Очередь» block mounted on its page |
| CMP-MEASURE-01 | `00afbc21` | the whole chain on the real set (`docs/program/compare/MEASURE-ENGINE-01.md`, ADR-0025 addendum 2026-10-29): ceilings and caps hold; it found that a plain-PDF upload could not be profiled (FIX-C); the real set is deleted |
| CMP-C1-FIX-C | `fde32fe6` | a plain-PDF upload is profiled (both manifest roles; an ambiguous manifest refused); a page-profile attempt builds at most 30 pages and yields; a byte-identical version reuses its pages; the end-to-end test upload → profile → matrix → series → tile through the product's own path |

Integrator commits: `8443042d` (a dev unit double lacked the SEAL-C1 flag), `576da4a1` (the engine's handler-tuple pin
after MATRIX's kind), register conflict resolutions in the merges of MATRIX and VIEWER, `d11c13fd` and `49c8479f`
(brief §4, §5).

## Verification (light acceptance, R-70)
Light acceptance (R-70) on the publication candidate, all on own stacks, commands in `.local/handoff/compare-modules-2026-10-27.md`:
- `9861c9f9` (all C1 lanes + FIX-A + FIX-B): unit + contract (minus `D-220`) + journey conformance + p02 figures 6409 passed; web lint, typecheck, `api:verify` exit 0; whole vitest 3560 passed; `tests/integration/comparison` in one process 554 passed; composition, db, documents, ingest, recovery, storage, executors 4893 passed / 21 skipped / 0 failed.
- The whole `tests/integration` in two halves on `e01c7835` (before the FIX lanes): every red was environment or test isolation — 17 stand-copy and deploy-script tests refuse a pytest base temp inside the repo, one norms test needs `.local/norms` in the worktree (both green on rerun: 258 passed), 15 comparison tests failed in one process (closed by FIX-A, 554 passed), one stale storage pin (`353cfac4`).
- FIX-C on its tree (the publication commit differs by the ADR addendum only): unit 4985, contract 1310, comparison in one process 566, ingest comparison 298, composition 1955 / 5 skipped.
- The `0035` → matrix data step of migration `0039` is rehearsed by `tests/integration/db/test_comparison_core_migration.py` (approvals seeded at `0038`, upgrade, count of `migrated_sheet_link` edits equals the active approvals, downgrade refusal) — green in the first half; no copy of a populated production database was available.
- Not run: `make gate` and the live journey (`D-255`, `R-135`: the complete gate is the one before beta).

## Decisions the integrator took in the owner's 12-hour window (for the owner's review)
1. ENGINE merged before MATRIX; VC-UI-01 and OVERVIEW dispatched in parallel with SERIES (brief §5 item 3).
2. The engine's extra result member `part` (split sheets) is confirmed (brief §5 item 1).
3. The matrix build stays in the worker process without a ceilinged child: measured 12 × 100 pages 16 s / 230 MiB,
   12 × 400 pages 198 s / 541 MiB (MATRIX §9 item 1) — below the 768 MiB child ceiling even at the extreme.
4. The comparison operations answer whatever the module flag; only the worker and the C2 AI commands are gated
   (MATRIX §9 item 6, OVERVIEW §9 item 14). The menu entry stays visible with the flag off; the screens show «Модуль
   ещё недоступен».
5. `comparison_edits_limit` is reachable only below the edge (the schema's `maxItems` answers first).
6. The ZIP reader's security review (D-262) and `__MACOSX/` wait for wave C3, where ZIP sets are first used.
7. Stream-level overlay separation (stamps and warnings inside the content stream) is not built: it needs a PDF editor
   and PyMuPDF is excluded (`OD-01`); the engine treats a release mark as a compared zone and a baked-in warning as
   `warnings` unchecked + `PARTIAL_COVERAGE` (ENGINE §4.2). Owner decision owed.
8. Auto-mode refused deleting other lanes' dangling `auditmanager-*` test volumes (≈ 0.3 GB); not retried.

## Open items
- To SEAL-C2 (contract-shaped): `algorithm_changed` stale reason; the matrix column label; registered reasons
  `comparison_matrix_stale` on start and `comparison_versions_few`; the pyramid raster size on the pair; «sealed as a
  stub» prose of the C1 routers.
- Owner: stream-level separation (decision 7); the ZIP review path (D-262); who integrates `origin/dev` after the
  window.
- Production: a deploy of `0039` runs the `0035` data step on the production database — R-146n item 3 asks for a
  manual dump first (pdf-analysis-43's note; deploy-auto for `94d3dc46` failed at deploy.sh's guards on 10-27 and the
  host was cut over by hand).
- Debt opened in this wave: `D-265` (the start note's wording on pass and read screens). FIX items left for C2's FIX slot: the upload proposal split the real set in two and the join needs `existing_document_uid` offered on the screen (MEASURE FIX-2); the claim cadence idles the worker 0.8 s per item (MEASURE FIX-5); a pair without a result answers `mode=b` with B's own tile, now cacheable for an hour (FIX-A note).
