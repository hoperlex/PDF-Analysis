# Task CMP-STAGE-UI-01 — usable stage sheet viewer and text evidence

## Outcome
An expert can inspect selected stage pages side by side, search each page, see proven text exclusions, request and follow durable text recomputation, inspect raw differences and turn a cross-sheet hint into an explicit unsaved map decision.

## Depends on
- CMP-STAGE-TEXT-RECOMPUTE-01
- CMP-STAGE-REPAIR-CORE-01

## Frozen inputs
- domain contract: ADR-0025 A-9; `COMPARE-MODULES-PLAN.md` §1.2 and C3/C4
- API contract: `1.12.0`, sealed stage link/text/run operations and generated client; no generated edit
- migration head: `0041_comparison_stage_core`; browser performs no direct persistence
- viewer: existing public `ComparisonViewerView`, reducer and profile tile client; root owns the structural view-data seam removing unused version-pair identities
- base commit: `74aa1928446a9fe5eb222adfb7ff69c014422690`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: stage map uses profile previews and the four text GETs/recompute POST now have runtime code; the viewer's pure public view is reusable without a version-pair request.

### P-01 — base and public viewer
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; rg -n 'export \{ ComparisonViewerView|export function StageSheetMap' web/src/widgets/comparison-viewer/index.ts web/src/widgets/stage-sheet-map/ui/stage-sheet-map.tsx`
- captured_output:
  ```text
  74aa1928446a9fe5eb222adfb7ff69c014422690
  web/src/widgets/comparison-viewer/index.ts:9:export { ComparisonViewerView } from './ui/comparison-viewer-view';
  web/src/widgets/stage-sheet-map/ui/stage-sheet-map.tsx:221:export function StageSheetMap({ projectUid, mayAct }: {
  ```
- interpretation: this lane owns a stage wrapper and evidence panel; root owns page mounts and the shared viewer prop type seam.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `web/src/widgets/stage-sheet-map/**`
- `web/src/widgets/stage-text-evidence/**`
- `web/tests/unit/stage-sheet-map/**`
- `web/tests/unit/stage-text-evidence/**`
- `docs/program/tasks/CMP-STAGE-UI-01.md`
- `docs/program/CMP-STAGE-UI-01.md`
- `web/node_modules`

## Forbidden hotspots
- page mounts, shared viewer implementation, generated client/contracts, migrations, root dependencies/locks, shared global styles, remote refs and deployment

## Non-goals
- no new canonical identity, comparison engine result, AI finding or automatic map act
- no C4 review cards or report export; no full gate/build

## Deliverables
1. Profile-tile two-pane wrapper around the public viewer view with fit, 1:1, pan/zoom and optional synchronised view.
2. Per-panel text search, provider seam for stored page words, proven-same grey boxes and focusable raw differences.
3. Keyed recompute POST, queued/running run polling, current/stale state and explicit recompute prompt when evidence is absent.
4. Nonbinding cross-sheet hint actions that only edit the unsaved draft and preserve displaced sheets and all existing move rules.

## Required tests
- short focused Vitest and web typecheck; `git diff --check`; full gates/heavy windows deferred by owner to tomorrow

## Integration contract
Root mounts/exports the owned widget as needed and narrows the public viewer data prop so no fake version-comparison IDs are required. The page text provider can later use `getStageProfileText`; until then the saved fragment collection supplies honest search or a recompute prompt. Stage chain run GET/list are root-owned runtime. Hints require an expert save before any map changes persist.

## Failure/idempotency/security cases
- profile and tile requests are abortable; object URLs are revoked on page change/unmount
- one recompute intent reuses its key on retry; changing revision creates a new intent
- failed or stale evidence never appears as a confirmed empty text result; dirty map drafts hide old proof masks

## Rollback / feature flag
The parent stage screen is already module-gated; remove these widget changes to restore its earlier previews. No data/schema rollback.

## Handoff
- changed files: task/report, owned `stage-sheet-map/**`, new `stage-text-evidence/**`, their focused unit suites
- commands/results: focused Vitest **16 passed**; web typecheck and `git diff --check` passed
- contracts: none
- known limits: root viewer seam/provider and C4 runtime are integration dependencies; one temporary expected type error marks the root-owned pure-view seam, remove on integration
- integration notes: root owns shared viewer/type and page mount changes
