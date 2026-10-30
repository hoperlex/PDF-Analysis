# Task DESIGN-REF-01-NAV — узнаваемая навигация

## Outcome

На десктопе полная боковая панель показывает понятные иконки рядом с названиями, компактная — иконки с полными подсказками при наведении и фокусе. Ролевой состав и текущий пункт остаются прежними.

## Depends on

- `DESIGN-DESKTOP-SHELL-1030` (published at `85ab8c1edc7313bec379949ba9e6ffbeba5325fa`).

## Frozen inputs

- Base: `ce9b86fdeddeda024039ae3cc573a78b6ee36b22` (`origin/dev`).
- API/contract: `1.14.0`; migration head `0043_stage_ai_generations`.
- Menu rows: `buildNavigation` and `SCREEN_REGISTRY` at the frozen base; no registry edit.
- Design reference: `docs/program/DESIGN-REF-FOLLOWUP-1030.md` and owner supplied Hynex images.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: existing registry owner; read-only here
- totality_query: `rg -n 'inMenu: true' web/src/shared/config/screen-registry.ts`

## Captured premise evidence

- `web/src/_app/frame-navigation.tsx` renders the compact rail as two-letter labels and uses `title` for the full name; the shared disclosure renders text-only links. The 31-screen route set remains unchanged.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `web/src/_app/frame-navigation.tsx`
- `web/src/_app/navigation-glyph.tsx`
- `web/src/_app/app-frame.module.css`
- `web/src/shared/ui/disclosure.tsx`
- `web/src/app/globals.css`
- `web/tests/unit/shell/navigation.test.ts`
- `web/tests/unit/ui/disclosure.test.ts`
- `docs/program/DESIGN-REF-FOLLOWUP-1030.md`
- `docs/program/tasks/DESIGN-REF-01-NAV.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- Screen registry, all feature routes, API, contracts, migrations, root dependencies, other composition roots and `origin/main`.

## Non-goals

- New navigation destinations, search, access changes, or a redesign of screen content.

## Deliverables

- Original local line icons mapped to existing menu labels; clearly visible fallback for a future unmapped row.
- Compact tooltip outside the sidebar scroll clipping, visible on hover and keyboard focus.
- Checks for all current menu labels, active item and accessibility text.

## Required tests

- `npm run typecheck`; `npm run lint`; focused shell/UI/style Vitest; CSS parse; `git diff --check`.
- Owner requested basic checks and no full gate or review window.

## Integration contract

- Only presentation props are added to the existing disclosure primitive; callers without an icon keep their previous output. All links still come from `buildNavigation` and use the same current marker.
- This task owns global CSS for this sequential slot; no simultaneous owner.

## Failure/idempotency/security cases

- Missing icon mapping renders visible initials without changing the link; no missing link or role fallback. Tooltip text is the existing safe React label.

## Rollback / feature flag

- Revert this one commit to restore text rail; no migration or runtime flag.

## Handoff

- Changed files are the allowed paths above except the untouched disclosure unit test. No forbidden hotspot was edited.
- Focused tests: 90 passed; typecheck, lint, CSS parse and diff check passed. Browser screenshots and live pointer checks remain unverified in this environment.
- No contract changed. Integrator publishes the exact tested SHA to `origin/dev` after a fast-forward remote check.
