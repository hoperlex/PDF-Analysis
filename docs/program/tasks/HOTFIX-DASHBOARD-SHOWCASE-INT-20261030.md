# Task HOTFIX-DASHBOARD-SHOWCASE-INT-20261030 — two-theme dashboard showcase and 31-screen design plan

## Outcome

The working `/dashboard` has a distinct, modern presentation in both existing light and dark appearances; the `system` choice still follows the operating system. A written implementation plan covers every current route without claiming those routes are already restyled.

## Depends on

- `HOTFIX-SECTION-PRESENTATION-INT-20261030` (completed and published at `ee90c6a50214c335c241cd4cb6d7dbf55a1cf2cd`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `ee90c6a50214c335c241cd4cb6d7dbf55a1cf2cd`.
- Visual reference: Hynex Healthcare Dashboard Design by Orbix Studio, Muzli, supplied by the owner on 2026-10-30.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the application has 31 `web/src/app/**/page.tsx` routes, 67 collocated CSS modules and a 2,539-line `web/src/app/globals.css` with light, system-dark and explicit-dark token blocks. The existing dashboard has four panels and one `getDashboardSummary` read. Its data and failure states must remain unchanged.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`, as the owner's standing development-only publication preference.
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/HOTFIX-DASHBOARD-SHOWCASE-INT-20261030.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/app/globals.css`
- `web/src/_pages/dashboard/ui/dashboard-page.tsx`
- `web/src/widgets/dashboard/ui/dashboard.tsx`
- `web/src/widgets/dashboard/ui/dashboard.module.css`
- `web/src/widgets/dashboard/ui/sections-panel.module.css`
- `web/tests/unit/widgets/dashboard.test.ts`
- `web/tests/unit/styles/**`

## Forbidden hotspots

- `contracts/**`, migrations, root/web dependencies and locks, composition roots, route registry, backend analysis/Run behavior, other widgets and all other pages.
- `origin/main` and the preserved AR v3 branch.

## Non-goals

- Changing dashboard API data, adding computed business metrics, or styling all 31 screens in this task.
- Replacing the existing theme control or making dark mode the default for every user.
- Copying the reference's healthcare data, illustrations, charts or AI claims.

## Deliverables

- Dashboard-specific visual tokens and a coherent light/dark treatment of `/dashboard` including its section list and responsive layout.
- A screen-by-screen future design plan with stages, acceptance criteria, dependencies and time estimates.
- Focused rendering and style verification plus an updated current-state record.

## Required tests

- `npm --prefix web run typecheck`
- `npm --prefix web run lint`
- `npm --prefix web test -- tests/unit/widgets/dashboard.test.ts tests/unit/styles/theme.test.ts tests/unit/styles/tokens-defined.test.ts tests/unit/styles/contrast.test.ts`
- `git diff --check` and allowed/forbidden path review.

## Integration contract

Only the dashboard's visual layer changes. The dashboard still consumes the existing one-read summary and renders the same source-backed data, error states and navigation. New colour tokens are declared in `:root`, the system-dark block and the explicit-dark block with equal dark values; only the dashboard uses them. Existing roles, themes, routes and actions are retained.

## Failure/idempotency/security cases

- If summary loading or retrieval fails, the existing loading and error state remains visible.
- Long project/section names and narrow viewports cannot widen the page.
- Decorative visual elements expose no fabricated metric or interactive action.

## Rollback / feature flag

- Reverting this commit restores the prior dashboard appearance and removes the design plan; no data or API migration is involved. No runtime flag is needed for a presentation-only change.

## Handoff

- Changed files: `docs/program/CURRENT_STATE.md`, `docs/program/DESIGN-31-SCREEN-PLAN.md`, this task, `web/src/app/globals.css`, `web/src/_pages/dashboard/ui/dashboard-page.tsx`, `web/src/widgets/dashboard/ui/dashboard.tsx`, `dashboard.module.css`, `sections-panel.module.css`, `web/tests/unit/widgets/dashboard.test.ts`, and `web/tests/unit/styles/dashboard-showcase.test.ts`.
- Checks: typecheck and lint passed; 43 focused dashboard/theme/showcase tests passed; all three edited stylesheets parsed with PostCSS; the plan inventory matched 31 route files exactly (missing/extra both empty); `git diff --check` passed. The full rendered-screen contrast census was attempted but interrupted after a long run without a result; the new palette-specific test measured readable ink/accent and visible borders in both themes.
- Existing style-test failures on this `origin/dev` base: `styling-layer.test.ts` has two literal colours in the unowned stage-upload panel (10/11 passed); `tokens-defined.test.ts` has 16 undefined token reads in comparison modules (5/6 passed). Neither source file is changed here. They are assigned to stage A of the future design plan.
- Contracts: unchanged at `1.13.0`; migration head remains `0043_stage_ai_generations`. No route, backend, evidence, profile or analysis behavior changed.
- Limitations: the showcase is visually scoped to `/dashboard`; the other 30 routes retain their existing styling. Browser screenshot review was unavailable in this lane; a visual check in both themes at 390/768/1440 px is the next presentation check.
- Integrator: publish this clean, focused candidate as a fast-forward to `origin/dev` only. Revert the commit to restore the old dashboard; no migration or stored-data rollback is involved.
- Forbidden-hotspot proof: the diff consists only of the `Allowed paths`. The `web/src/app/globals.css` change is explicitly owned by this integration task; no contract, migration, dependency, composition root, route registry, backend or other page was touched.
