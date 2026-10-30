# Task DESIGN-REF-04-DENSITY — плотные рабочие списки

## Outcome

Проекты, диспетчер и база знаний показывают больше полезных записей в первом экране на десктопе. Формы и фильтры занимают ровно нужную ширину; длинные тексты, статусы и действия не теряются.

## Depends on

- `DESIGN-REF-03-CARDS` (completed and published at `20193e053371e610fc0ef8c52d97cb4304326da6`).

## Frozen inputs

- Base: `20193e053371e610fc0ef8c52d97cb4304326da6` (`origin/dev`).
- API/contract: `1.14.0`; migration head `0043_stage_ai_generations`.
- Existing list reads, filter choices, roles, paging and mutations at base are frozen.
- Design reference: `docs/program/DESIGN-REF-FOLLOWUP-1030.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: existing registry owner; read-only
- totality_query: `rg --files web/src/app | rg '/page.tsx$'`

## Captured premise evidence

- `/projects` and `/knowledge-base` already have bordered child panels inside the `PageShell` card. `/dispatcher` has bordered form/list panels inside its own card. Assignment rows and knowledge records use broad vertical gaps at the frozen base.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `web/src/_pages/projects/ui/projects-page.tsx`
- `web/src/_pages/projects/ui/projects-page.module.css`
- `web/src/widgets/project-list/ui/project-list.tsx`
- `web/src/_pages/dispatcher/ui/dispatcher-page.tsx`
- `web/src/_pages/dispatcher/ui/dispatcher-page.module.css`
- `web/src/widgets/assignment-board/ui/assignment-board.module.css`
- `web/src/_pages/knowledge-base/ui/knowledge-base-page.tsx`
- `web/src/_pages/knowledge-base/ui/knowledge-base-page.module.css`
- `web/tests/unit/screens/forms-and-pages.test.ts`
- `web/tests/unit/dispatcher/dispatcher.test.ts`
- `web/tests/unit/screens/knowledge-base.test.ts`
- `docs/program/tasks/DESIGN-REF-04-DENSITY.md`
- `docs/program/DESIGN-REF-FOLLOWUP-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- Registry, APIs, contracts, migrations, root dependencies, entity/feature behavior, other screen modules, global CSS and `origin/main`.

## Non-goals

- Adding search, changing filters or paging, hiding columns or truncating evidence text.

## Deliverables

- Project list with adjacent create form on wide desktops; assignment form/list cards with compact table and contained scrolling; knowledge filters/results with tighter spacing.
- Mobile stacking and existing role conditions remain.

## Required tests

- `npm run typecheck`; `npm run lint`; focused project/dispatcher/knowledge/style Vitest; CSS parse; `git diff --check`.
- Basic checks only, no full gate or review window per owner instruction.

## Integration contract

- All queries, mutations, filter state and navigation stay inside their current components. Only layout wrappers and CSS modules change; global styles have no owner in this task.

## Failure/idempotency/security cases

- Long notes, names and finding texts continue wrapping inside cells/panels. Role-specific controls retain the existing conditions. Table scroll never removes actions from the DOM.

## Rollback / feature flag

- Revert one commit; no flag or migration.

## Handoff

- Changed files are limited to the allowed paths. Registry, contracts, migrations, dependencies, APIs, global CSS and other composition roots are untouched.
- Focused tests: 75 passed; typecheck, repository-wide lint, CSS parse and diff check passed. Browser screenshot verification remains unavailable in this workspace.
- Integrator publishes the tested fast-forward SHA to `origin/dev` only.
