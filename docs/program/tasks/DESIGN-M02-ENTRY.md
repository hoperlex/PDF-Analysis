# Task DESIGN-M02-ENTRY — home, projects and section optimisation presentation

## Outcome

The `/`, `/projects` and `/section-optimisation` routes use the shared two-theme design language with clear hero/section hierarchy, contained cards and responsive filters. Their reads, links, forms and states remain unchanged.

## Depends on

- `DESIGN-M01-FOUNDATION` (completed and published at `36330cf0ad79b64c114e607204806923e5acf9df`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `36330cf0ad79b64c114e607204806923e5acf9df`.
- Design contract: `docs/program/DESIGN-31-SCREEN-PLAN.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: home already renders role-filtered overview/tiles, projects page composes create/list without local layout, and section optimisation already has a scroll frame for its wide table. Their current presentation is mostly ungrouped shared primitives.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`.
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/DESIGN-M02-ENTRY.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/_pages/home/ui/home-page.tsx`
- `web/src/_pages/home/ui/home-page.module.css`
- `web/src/widgets/home-tiles/ui/home-tiles.module.css`
- `web/src/_pages/projects/ui/projects-page.tsx`
- `web/src/_pages/projects/ui/projects-page.module.css`
- `web/src/widgets/section-specification/ui/section-specification.module.css`

## Forbidden hotspots

- Contracts, migrations, dependencies, composition/global styles, backend, route registry and other screen widgets.
- `origin/main` and preserved AR v3 branch.

## Non-goals

- Changing project creation, permission decisions, section specification computation, prices or result data.
- Redesigning project detail, version, Run or comparison routes owned by later mini-tasks.

## Deliverables

- Home hero and card rhythm; projects create/list hierarchy; specification filters and project/table cards.
- Updated plan/current-state record and focused checks.

## Required tests

- Frontend typecheck and lint.
- Focused home, project route and section specification rendering tests.
- CSS parse, `git diff --check`, changed-path review.

## Integration contract

All three routes keep the same React data and action components. This task only adds layout wrappers/classes and token-based local CSS. No extra reads, numbers, links or controls are introduced.

## Failure/idempotency/security cases

- Empty/error/loading states retain their existing components and labels.
- A long project name and wide form table remain contained at narrow widths.
- Role filtering for home tiles remains exactly as before.

## Rollback / feature flag

- Revert this visual commit; no flag or migration is involved.

## Handoff

- Typecheck and lint passed; focused home, specification and styling tests passed
  after restoring the existing media-rule ordering; CSS modules parse and the
  changed-path/diff checks pass. The first focused test run had one failure caused
  by that ordering and was corrected before publication. Broad legacy screen
  files still have two unrelated assertions in untouched code: a start-run
  control now renders a second button, and the route census expects a
  stage-comparison link. The scoped `/projects` assertions pass.
- No contract, migration, dependency, global CSS or backend path is changed.
- The next task may start from this commit only after `origin/dev` confirms its SHA.
