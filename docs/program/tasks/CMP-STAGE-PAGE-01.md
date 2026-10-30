# Task CMP-STAGE-PAGE-01 — mount the complete stage workspace

## Outcome
The stage comparison page exposes documentation, sheet map, change cards and journal tabs with one coherent pair/run selection. Evidence and raw-difference actions open their actual profiles/boxes; stored page words drive search; accepted high-confidence AI sameness adds nonmutating grey overlays.

## Depends on
- CMP-STAGE-REVIEW-UI-01
- CMP-SEAL-C4
- CMP-STAGE-RUN-01

## Frozen inputs
- domain: ADR-0025 and comparison roadmap §1.2/A-9/A-10
- API: `1.13.0`, C4 generated clients and root-integrated runtime
- migration: `0042_comparison_stage_review`
- assigned lane: existing journey worktree/branch, root advanced before dispatch
- integration baseline: `f24f09e75712f10ad6c30e876de952f2f801b34f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: root runtime and connected widgets exist; the stage page still mounts only the first two tabs.

### P-01 — page mounting gap
- captured_at: 2026-10-30
- command: `git rev-parse HEAD; rg -n 'role="tab"' web/src/_pages/stage-compare/ui/stage-compare-page.tsx`
- captured_output:
  ```text
  f24f09e75712f10ad6c30e876de952f2f801b34f
  50: 1. Загрузка документации
  51: 2. Сопоставление листов
  ```
- interpretation: compose already connected public widgets and add controlled viewer navigation within the owned page/map.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `web/src/_pages/stage-compare/**`
- `web/src/widgets/stage-sheet-map/**`
- `web/src/widgets/stage-text-evidence/**` (root followup grant for nonmutating AI masks if needed)
- scoped `web/tests/unit/stage-compare/**`, `web/tests/unit/stage-sheet-map/**`, `web/tests/unit/stage-text-evidence/**`, `web/tests/unit/screens/stage-compare.test.ts`
- `docs/program/tasks/CMP-STAGE-PAGE-01.md`
- `docs/program/CMP-STAGE-PAGE-01.md`
- `web/node_modules` local ignored symlink for focused checks

## Forbidden hotspots
- stage-changes/run-controls polling, shared viewer, contracts/generated code, migrations, dependency/lock files, root wiring/registries, global styles and remote refs

## Non-goals
- no inferred per-card importance/materiality, canonical IDs or mock success
- no browser/build/full gate/heavy windows; journey followup is separate

## Deliverables
1. Four mounted tabs with pair/full-run selectors, catalog/run callbacks and visible run/repair controls.
2. Controlled map pair/focus and evidence navigation to actual source profiles, map row and anchors.
3. Stored word provider and immutable accepted SAME/MOVED overlay policy.
4. Focused tests/typecheck and root handoff.

## Required tests
- focused Vitest, web typecheck, scoped ESLint and `git diff --check`

## Integration contract
Root has integrated backend/polling. This lane consumes public generated clients/widgets, preserves existing draft move rules and exports backwards-compatible optional map props. Pair/project/run consistency is verified before mounting evidence. No endpoint or shared polling contract changes.

## Failure/idempotency/security cases
- pair/project or run/pair mismatch refuses display; changing project/pair clears unrelated run/focus state
- missing/foreign profiles or anchors show a clear navigation failure instead of a wrong page
- AI overlays require current matching run/revision, accepted SAME/MOVED/high confidence and known fragment IDs; raw differences are never rewritten
- page-word reads use the stored-profile endpoint and propagate abort/failure

## Rollback / feature flag
Existing module flag gates the whole workspace. Removing new mounts restores the two-tab page; optional map props preserve previous callers. No persisted data changes.

## Handoff
- changed files: owned stage page, controlled sheet-map/navigation/AI overlay modules, optional derived overlay field in stage-text-evidence, scoped tests and this task/report
- checks: 29 focused Vitest passed; web typecheck, scoped ESLint and diff-check clean
- known limits: browser interaction remains unexecuted; historical raw fragment text may be absent from the current fragment endpoint, but evidence opens its saved profile/box directly
- contracts: none
- integration: public optional `StageMapFocus`/pair/run props; root owns publication; C4 journey/static refresh transferred to the seal agent; expert promotion/detail metadata is the next authorised UI followup
