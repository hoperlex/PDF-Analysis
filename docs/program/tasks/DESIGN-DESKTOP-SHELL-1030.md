# Task DESIGN-DESKTOP-SHELL-1030 — compact desktop shell

## Outcome

The 31-screen application uses a denser desktop frame, a narrower sidebar that can collapse to a persistent link rail, a readable Cyrillic font, and restrained transitions in both themes. The user can verify the expanded and collapsed layouts at desktop widths.

## Depends on

- `DESIGN-M10-ACCEPTANCE` (completed at `ad82d215e3f807693b312c2332ca465533c173ec`).
- `HOTFIX-PRESENTATION-INT-1030` (completed at `3037749df82191a1d265c05229d5e5788707cbc3`).
- `CMP-ACTIVATE-1030` (completed at `a0c1050af173e6ed50282caabd5b2226fb2d2c06`; added the stage comparison menu row before publication).

## Frozen inputs

- Frozen implementation base: `3037749df82191a1d265c05229d5e5788707cbc3`; integration incorporated `CMP-ACTIVATE-1030` at `a0c1050af173e6ed50282caabd5b2226fb2d2c06` and was rebased onto `6e8e5b69865a5dfe738bc9c9c9eefa4fbc8aca` before publication.
- API/contract version: `1.14.0`; 233 paths / 259 operations / 620 schemas.
- Migration head: `0043_stage_ai_generations`.
- Design reference: `docs/program/DESIGN-31-SCREEN-PLAN.md` and the Hynex visual references supplied by the owner.
- Navigation set and role gates: the existing `buildNavigation` output; screen registry is read-only.

## Ownership and allowed paths

This is the single integration/style slot for the shared desktop shell, `web/src/app/globals.css`, and its self-hosted font in this wave. Allowed paths:

- `web/src/_app/app-frame.tsx`
- `web/src/_app/frame-navigation.tsx`
- `web/src/_app/app-frame.module.css`
- `web/src/_app/sidebar-toggle.tsx`
- `web/src/shared/ui/disclosure.tsx`
- `web/src/app/globals.css`
- `web/public/fonts/**`
- `web/tests/unit/shell/frame.test.ts`
- `web/tests/unit/shell/navigation.test.ts`
- `web/tests/unit/shell/sidebar-toggle.test.ts`
- `web/tests/unit/ui/disclosure.test.ts`
- `docs/program/tasks/DESIGN-DESKTOP-SHELL-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- `contracts/**`, migrations, root dependencies and lockfiles, API client, screen registry, feature routes, backend, other application composition roots, `origin/main`.

## Non-goals

- Changing permissions, navigation destinations, analysis behavior, API contracts, or deploying to production.
- Reworking all 31 screen contents independently; their shared frame and type scale are the scope here.

## Deliverables

- A desktop sidebar with expanded and compact states, keyboard-accessible toggle, stored preference and current-link marking.
- Navigation groups that remain open after selecting a child link; desktop groups also stay open during work in the content area.
- Reduced desktop whitespace, two-theme hover/focus states and reduced-motion support.
- Self-hosted Cyrillic UI font with license notice and responsive fallback.

## Checks

- Focused shell, navigation, theme/style and registry unit/guard tests; frontend typecheck and lint; CSS parse and changed-path review.
- The owner requested basic checks only, without a full gate or review window.

## Integration contract

- One owner edits the shared CSS and frame. Both nav presentations read the same role-filtered navigation; hidden variants leave the accessibility tree through `display:none`.
- Existing server-side session and route composition remain unchanged. Publish only to `origin/dev` after a fast-forward check; no `origin/main` authority.

## Rollback / feature flag

- Revert the commit to restore the previous frame. The persisted sidebar value is cosmetic and ignored by the old frame; no migration is needed.

## Known limits

- A stored compact choice is applied after hydration, like the existing theme choice, so one expanded frame may appear briefly on a cold load.
- Browser screenshots and pointer interaction on a live stand were not available in this workspace; static rendering, CSS parse and focused behavior checks cover the implementation.
- Repository-wide lint passed after integration with `CMP-ACTIVATE-1030`; this task did not edit the comparison feature file.

## Handoff

- Expected changed paths are exactly the allowed paths above; no contract, migration, dependency, screen registry or other composition root is edited.
- The design change is cosmetic; the only new browser state is `auditmanager.sidebar` (`full` by default, `compact` when chosen).
- Run the focused commands in Checks and publish the tested fast-forward commit to `origin/dev` only.
