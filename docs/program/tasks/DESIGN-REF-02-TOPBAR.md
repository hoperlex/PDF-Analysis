# Task DESIGN-REF-02-TOPBAR — контекстная строка

## Outcome

На всех экранах под боковой навигацией содержимое начинается с компактной верхней строки: текущая группа и экран, метка стенда, тема и аккаунт. Навигационный переход обновляет контекст без перезагрузки. На узкой ширине строка переносится без потери действий.

## Depends on

- `DESIGN-REF-01-NAV` (completed and published at `a5247aeed449672d9489d6762d55555d3acf0af2`).

## Frozen inputs

- Base: `a5247aeed449672d9489d6762d55555d3acf0af2` (`origin/dev`).
- API/contract: `1.14.0`; migration head `0043_stage_ai_generations`.
- Screen labels and groups: `SCREEN_REGISTRY` at base; read-only.
- Design reference: `docs/program/DESIGN-REF-FOLLOWUP-1030.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: existing registry owner; read-only
- totality_query: `rg --files web/src/app | rg '/page.tsx$'`

## Captured premise evidence

- `web/src/_app/app-frame.tsx` currently places the theme and account cluster below navigation inside `.am-app__bar`; no shared top utility row exists. `screenMatching` supplies the current route's registered label.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `web/src/_app/app-frame.tsx`
- `web/src/_app/app-frame.module.css`
- `web/src/_app/screen-context.tsx`
- `web/src/app/globals.css`
- `web/tests/unit/shell/frame.test.ts`
- `web/tests/unit/shell/screen-context.test.ts`
- `docs/program/tasks/DESIGN-REF-02-TOPBAR.md`
- `docs/program/DESIGN-REF-FOLLOWUP-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- Registry, routes, API, contracts, migrations, root dependencies, other composition roots, `origin/main`.

## Non-goals

- Global search, clock, new account actions, project-name reads or changes to each page's own title.

## Deliverables

- Context row driven by the existing screen registry and updated via pathname.
- Existing controls moved intact, with menu popup anchored correctly and both themes supported.
- Tests for guest, role session, nested route and unknown path.

## Required tests

- `npm run typecheck`; `npm run lint`; focused shell/theme/registry Vitest; CSS parse; `git diff --check`.
- No full gate or review window per owner instruction.

## Integration contract

- `AppFrame` remains a server component; the route context is a client island with no fetch. Existing control components are rendered once and retain their actions. This task owns the shell/global style slot sequentially.

## Failure/idempotency/security cases

- Unknown pathname displays neutral application context; no guessed project identity or link. Long labels truncate within the toolbar instead of widening it.

## Rollback / feature flag

- Revert this commit to restore the previous layout; no stored state or migration is added.

## Handoff

- Changed files are limited to allowed paths; registry, contracts, migrations, dependencies and other composition roots are untouched.
- Focused tests: 85 passed; typecheck, repository-wide lint, CSS parse and diff check passed. Live browser layout remains unverified in this environment.
- Integrator publishes the tested fast-forward SHA to `origin/dev`; no `origin/main` authority.
