# Task DESIGN-M05-COMPARISON — three comparison routes

## Outcome

The global version and stage comparison routes and the version-specific comparison route use consistent two-theme controls, tab surfaces, readable evidence panels and contained wide tables.

## Depends on

- `DESIGN-M04-RUN` (completed and published at `077d2124c20ba15dff4904f73f672b8ddfab91e6`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `077d2124c20ba15dff4904f73f672b8ddfab91e6`.
- Design contract: `docs/program/DESIGN-31-SCREEN-PLAN.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `/version-comparison` uses CompareTabs; `/stage-comparison` uses StageWorkspace with four tabs; the version-specific comparison composes VersionComparison and lazy Run comparison. Their selectors and evidence widgets already own data behavior.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/DESIGN-M05-COMPARISON.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/_pages/version-compare/ui/version-compare-page.tsx`
- `web/src/_pages/version-compare/ui/version-compare-page.module.css`
- `web/src/_pages/stage-compare/ui/stage-compare-page.tsx`
- `web/src/_pages/stage-compare/ui/stage-compare-page.module.css`
- `web/src/_pages/stage-compare/ui/stage-workspace.tsx`
- `web/src/_pages/stage-compare/ui/stage-workspace.module.css`
- `web/src/_pages/stage-comparison/ui/stage-comparison-page.tsx`
- `web/src/_pages/stage-comparison/ui/stage-comparison-page.module.css`
- `web/src/widgets/version-comparison/ui/version-comparison.module.css`
- `web/src/widgets/stage-comparison/ui/stage-comparison.module.css`

## Forbidden hotspots

- Contracts, migrations, dependencies, backend, route registry, composition root, global styles and unrelated screens.
- `origin/main` and preserved AR v3 branch.

## Non-goals

- Changing pair selection, AI review, sheet evidence, comparison calculation, permissions, export or lazy loading.

## Deliverables

- Contained project selectors and tab panels, stage workspace controls, version/run comparison cards and scrollable tables.
- Updated plan/current-state record and basic focused checks.

## Required tests

- Frontend typecheck, lint, focused version/stage comparison tests, CSS parse and diff/changed-path checks.

## Integration contract

Existing widgets, selected tabs, query keys and commands retain their behavior. New page wrappers/classes and widget CSS use the shared semantic tokens. Wide evidence remains horizontally scrollable.

## Failure/idempotency/security cases

- Loading/error/refusal states and read-only permissions remain visible. No action is newly enabled.

## Rollback / feature flag

- Revert the single visual commit; no flag, contract or migration is involved.

## Handoff

- Typecheck, lint, CSS parse, diff check, 122 focused version/stage
  comparison and styling tests, and six defined-token tests passed. The
  full-screen contrast census was started but stopped after it exceeded the
  lightweight-check budget; M10 still owns browser and full contrast review.
- No forbidden hotspot changed. Start M06 from this commit only after remote
  `origin/dev` confirms its exact SHA.
