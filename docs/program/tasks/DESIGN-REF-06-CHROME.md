# Task DESIGN-REF-06-CHROME — боковая навигация и хедер

## Outcome

На десктопе боковая панель и верхняя строка воспринимаются как часть того же аккуратного интерфейса, что и рабочие карточки: скруглённая панель, тонкая иерархия разделов, ясный активный пункт и компактные элементы управления. Полная, узкая и мобильная навигация сохраняют поведение.

## Depends on

- `DESIGN-REF-05-MOTION` (completed and published at `cd4dc8ca8bf3c445476319d3c998b60a397186f8`).

## Frozen inputs

- Base: `cd4dc8ca8bf3c445476319d3c998b60a397186f8` (`origin/dev`).
- API/contract: `1.14.0`; migration head `0043_stage_ai_generations`.
- `SCREEN_REGISTRY`, role-filtered navigation, group disclosure state, theme choices and account actions are frozen.
- Visual reference: owner-supplied Hynex images at `https://me.muz.li/orbix-studio/hynex-healthcare-dashboard-design-2`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: existing registry owner; read-only
- totality_query: `rg -n 'inMenu: true' web/src/shared/config/screen-registry.ts`

## Captured premise evidence

- The current desktop sidebar in `web/src/app/globals.css` is a full-height rectangular strip with one strong right border; its 224/68 px widths are tested and stay fixed.
- `web/src/_app/app-frame.module.css` uses flat group labels and link rows. The header is one white strip with registry context, instance label, theme and account. The reference uses an inset rounded sidebar, fine navigation guides, quiet separators and separate top controls.

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
- `web/src/app/globals.css`
- `web/tests/unit/shell/frame.test.ts`
- `web/tests/unit/styles/styling-layer.test.ts`
- `docs/program/tasks/DESIGN-REF-06-CHROME.md`
- `docs/program/DESIGN-REF-FOLLOWUP-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- Registry, routes, APIs, contracts, migrations, root dependencies/lockfiles, other composition roots, feature screens and `origin/main`.

## Non-goals

- Fake search, new destinations, new account or theme actions, changes to access rules, redesign of content screens.

## Deliverables

- Original compact SVG brand mark, inset rounded sidebar, section guide lines and active/hover hierarchy.
- A quiet toolbar surface with tiered current-screen context and separate pills for the existing controls in both themes.
- Mobile and compact-state styling, checks and one fast-forward development push.

## Required tests

- Focused shell/theme/style tests; `npm run typecheck`; `npm run lint`; CSS parse; `git diff --check`.
- Basic checks only; no full gate or review window per owner instruction.

## Integration contract

- This task exclusively owns `web/src/app/globals.css` for its sequential UI commit. All navigation items come from `buildNavigation`, and account/theme controls keep their existing components. Only shell presentation markup and styles change.

## Failure/idempotency/security cases

- Long menu labels retain their full text; compact links retain their accessible labels and tooltips. Focus and active state remain visible in both themes. `prefers-reduced-motion` still reduces transitions; mobile widths reset the inset desktop shell.

## Rollback / feature flag

- Revert the single commit; no flag, migration or persisted data.

## Handoff

- Changed files are limited to the allowed paths: `app-frame.tsx`, its module, `globals.css`, this task, the design plan and current state. Registry, contracts, migrations, root dependencies, feature screens and `origin/main` are untouched.
- Focused shell/screen/style tests: 76 passed; typecheck, lint, production web build, CSS parse and diff check passed. Browser screenshots remain unavailable in this environment.
- No public contract changed. Publish the exact tested fast-forward commit to `origin/dev` only.
