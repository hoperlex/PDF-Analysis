# Task DESIGN-REF-07-NORMS — аккуратные вкладки норм

## Outcome

«Поиск» и «Каталог» располагаются отдельной сегментированной полосой между блоком текущего снимка и содержимым. Они не касаются информационного блока, имеют ясное текущее состояние и не наезжают друг на друга на узком экране.

## Depends on

- `DESIGN-REF-06-CHROME` (completed and published at `209b48856b75ef2b5fa4780e11e222c34d335f1e`).

## Frozen inputs

- Base: `209b48856b75ef2b5fa4780e11e222c34d335f1e` (`origin/dev`).
- API/contract: `1.14.0`; migration head `0043_stage_ai_generations`.
- `NormViews` links, query parameters, snapshot/search/catalogue data and admin actions are frozen.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: existing registry owner; read-only
- totality_query: `rg -n 'inMenu: true' web/src/shared/config/screen-registry.ts`

## Captured premise evidence

- `NormsPage` renders a snapshot `.panel`, then `NormViews`, then a view `.panel`. `.views` has `margin: 0 0 1rem`, so no upper gap separates the buttons from the snapshot block; `.panel` itself has only top margin. The two links inherit full `am-button` borders and shadows.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `web/src/_pages/norms/ui/norms-page.tsx`
- `web/src/_pages/norms/ui/norms-page.module.css`
- `web/src/widgets/norm-catalogue/ui/norm-catalogue.module.css`
- `web/tests/unit/norms/catalogue.test.ts`
- `docs/program/tasks/DESIGN-REF-07-NORMS.md`
- `docs/program/DESIGN-REF-FOLLOWUP-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- Global styles, registry, APIs, contracts, migrations, dependencies, other screens, composition roots and `origin/main`.

## Non-goals

- Changing snapshot selection, search or catalogue behavior, tab addresses, permissions or data copy.

## Deliverables

- Responsive segmented view navigation, separated from snapshot and results panels.
- Clean two-theme card spacing and an explicit active/focus state.
- Focused checks and one fast-forward push to `origin/dev`.

## Required tests

- Focused norms/style tests; `npm run typecheck`; `npm run lint`; CSS parse; `git diff --check`.
- Basic checks only, no full gate or review window per owner instruction.

## Integration contract

- `NormViews` remains a navigation of two real links with `aria-current=page`; its route and query props are unchanged. Only local screen/widget presentation changes.

## Failure/idempotency/security cases

- Search and catalogue keep their current selection after navigation. On narrow widths each control remains touch-sized and readable; no horizontal overflow. Empty/refused snapshot content remains unmodified.

## Rollback / feature flag

- Revert the single commit; no flag or migration.

## Handoff

- Changed files are limited to this task's allowed paths. Global CSS, registry, contracts, migrations, dependencies, composition roots and `origin/main` remain untouched.
- Focused norms/style tests: 38 passed; typecheck, lint, CSS parse and diff check passed. Browser layout screenshots remain unavailable in this environment.
- No public contract changed. Publish the exact tested fast-forward commit to `origin/dev` only.
