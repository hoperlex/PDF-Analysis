# Task HOTFIX-SHELL-NAVIGATION-INT-20261030 — responsive presentation shell and navigation

## Outcome

On wide screens the application has a persistent left sidebar with directly visible role-allowed navigation groups; on narrow screens the existing compact disclosure menu remains. The brand, theme and account controls work in both appearances. All existing route and access decisions remain unchanged.

## Depends on

- `HOTFIX-DASHBOARD-SHOWCASE-INT-20261030` (completed and published at `ee436091835e12317699c1336ead747c496f73ce`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `ee436091835e12317699c1336ead747c496f73ce`.
- Reference: owner-supplied Hynex dashboard; the preceding dashboard task's two-theme token palette.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `AppFrame` owns the shared bar/main/footer; `FrameNavigationView` renders the role-filtered groups from `buildNavigation` in wide and compact states; `Disclosure` defaults closed. The former 960 px breakpoint switches navigation states, and the new sidebar needs a wider boundary so the content retains its usable width.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`, continuing the owner's development-only publication preference.
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/HOTFIX-SHELL-NAVIGATION-INT-20261030.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `web/src/app/globals.css`
- `web/src/_app/app-frame.tsx`
- `web/src/_app/frame-navigation.tsx`
- `web/src/_app/app-frame.module.css`
- `web/src/shared/ui/disclosure.tsx`
- `web/tests/unit/shell/frame.test.ts`
- `web/tests/unit/shell/navigation.test.ts`
- `web/tests/unit/ui/disclosure.test.ts`
- `web/tests/unit/styles/theme.test.ts`

## Forbidden hotspots

- `contracts/**`, migrations, dependency/lock files, composition roots, route registry, backend analysis/Run behavior and page-specific widgets.
- `origin/main` and the preserved AR v3 branch.

## Non-goals

- Changing which screen is offered to a role, adding routes, altering sign-in/out or menu semantics, or redesigning the 30 non-dashboard content screens.
- A new icon library, copied illustrations, fetched fonts or custom animation framework.

## Deliverables

- Responsive two-theme shell with a left desktop sidebar, current page indication, persistent visible grouped links, and compact disclosure navigation at smaller widths.
- Focused tests and updated plan/current-state record.

## Required tests

- `npm --prefix web run typecheck`
- `npm --prefix web run lint`
- Focused Vitest: shell frame/navigation, disclosure, theme and dashboard rendering.
- CSS parse, `git diff --check`, and allowed/forbidden path review.

## Integration contract

`buildNavigation(session)` stays the sole source of offered links. The desktop sidebar opens each group's inline disclosure by default; the mobile `Меню` remains closed until activated. Both render states still mark the active group and link from the pathname. The theme and account controls retain their existing behavior and labels. No data calls or route changes are added.

## Failure/idempotency/security cases

- Guests and incomplete/default-credential sessions still see no product navigation.
- Long account labels and grouped links wrap within the sidebar; the mobile header cannot widen a 390 px viewport.
- Keyboard focus, `aria-expanded`, `aria-current` and hidden-state behavior remain intact.

## Rollback / feature flag

- Revert the commit to restore the horizontal shell. No migration or stored-data rollback is needed; no runtime flag is introduced for presentation-only behavior.

## Handoff

- Changed files: this task, `docs/program/CURRENT_STATE.md`, `docs/program/DESIGN-31-SCREEN-PLAN.md`, `web/src/app/globals.css`, `web/src/_app/app-frame.tsx`, `frame-navigation.tsx`, `app-frame.module.css`, `web/src/shared/ui/disclosure.tsx`, `web/tests/unit/shell/frame.test.ts`, and `web/tests/unit/ui/disclosure.test.ts`.
- Checks: frontend typecheck and lint passed; 123 focused shell/navigation/disclosure/theme/avatar/dashboard tests passed; both edited stylesheets parsed with PostCSS; `git diff --check` passed. A browser screenshot pass was not started because `/tmp` had only 1.7 GB free (99% used) and Next/Firefox would write cache to that shared filesystem. The owner requested a short development-only window without a full gate. The comparison CSS's pre-existing style-test failures remain documented in the preceding task and the 31-screen plan.
- Contracts: unchanged at `1.13.0`; migration head remains `0043_stage_ai_generations`. `buildNavigation` and the route registry are unchanged; `Disclosure` gains only an optional `defaultOpen` presentation prop whose default remains closed.
- Limitation: the sidebar is proven by markup, styling rules and focused tests, not by a live browser at 390/768/1440 px. Page-specific content beyond `/dashboard` retains its prior visual treatment.
- Integrator: publish this exact clean candidate by fast-forward to `origin/dev` only. Revert the commit to restore the old top-bar layout; no stored data changes.
- Forbidden-hotspot proof: the diff contains only the `Allowed paths`; the global stylesheet and shared disclosure are explicitly owned here, with no contracts, migrations, dependencies, composition root, registry, backend or page widgets changed.
