# Task DESIGN-REF-03-CARDS — рабочая сетка карточек

## Outcome

Главная, проект и экран прогона на широком десктопе используют отдельные панели и доступную ширину; вложенная «карточка внутри карточки» удаляется. На узком экране порядок чтения остаётся линейным, все действия и данные доступны.

## Depends on

- `DESIGN-REF-02-TOPBAR` (completed and published at `81378e9b4f550605e7da64a1d6df09e8257dc58f`).
- `HOTFIX-AR-PIPELINE-INT-1030` (integrated from `29ccf9eb4390655c5470c3730300b649bbc01cfe` before publication; its run stage label and extended review props are preserved).

## Frozen inputs

- Frozen implementation base: `81378e9b4f550605e7da64a1d6df09e8257dc58f`; integration base: `29ccf9eb4390655c5470c3730300b649bbc01cfe` (`origin/dev`).
- API/contract: `1.14.0`; migration head `0043_stage_ai_generations`.
- Existing page contents, queries and role checks at base are frozen; layout only.
- Design reference: `docs/program/DESIGN-REF-FOLLOWUP-1030.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: existing registry owner; read-only
- totality_query: `rg --files web/src/app | rg '/page.tsx$'`

## Captured premise evidence

- The home `am-page__body`, project `PageShell` and run `PageShell` each wrap their own already bordered panels in a second paper card. Project documents and upload currently stack at every desktop width; home summary tiles stay at two columns.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `web/src/shared/ui/page-shell.tsx`
- `web/src/app/globals.css`
- `web/src/_pages/home/ui/home-page.tsx`
- `web/src/_pages/home/ui/home-page.module.css`
- `web/src/_pages/project-detail/ui/project-detail-page.tsx`
- `web/src/_pages/project-detail/ui/project-detail-page.module.css`
- `web/src/_pages/run/ui/run-page.tsx`
- `web/src/_pages/run/ui/run-page.module.css`
- `web/src/widgets/run-progress/ui/run-progress.tsx`
- `web/src/widgets/run-progress/ui/run-progress.module.css`
- `web/tests/unit/screens/home.test.ts`
- `web/tests/unit/screens/run-progress.test.ts`
- `web/tests/unit/screens/forms-and-pages.test.ts`
- `web/tests/unit/sections/project-structure.test.ts`
- `docs/program/tasks/DESIGN-REF-03-CARDS.md`
- `docs/program/DESIGN-REF-FOLLOWUP-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- APIs, contract/migration files, root dependencies, registry, route adapters, query/model code and other composition roots, `origin/main`.

## Non-goals

- Changing run polling, start/review actions, project uploads, optimisation reads or data meanings.

## Deliverables

- Shared opt-in canvas variant of PageShell; existing callers keep the previous card.
- Home overview and summary tiles use responsive grid; project documents and upload use an asymmetric desktop grid; run overview facts/result use distinct panels with full-width stages and details.

## Required tests

- `npm run typecheck`; `npm run lint`; focused home/project/run/style tests; CSS parse; `git diff --check`.
- Basic checks only, no full gate or review window per owner instruction.

## Integration contract

- DOM content and data sources stay the same except presentation wrappers. The `PageShell` canvas option is opt-in and defaults to the previous card. Global CSS has one owner in this sequential slot.
- Two older form/frame assertions are aligned with already published cost consent and brand markup; those runtime behaviors are unchanged here.

## Failure/idempotency/security cases

- Long project/run IDs remain breakable; tables stay contained, and visual card placement never changes query mount timing.

## Rollback / feature flag

- Revert this commit; no runtime flag or migration.

## Handoff

- Changed files are limited to allowed paths. Registry, contracts, migrations, root dependencies and API/query modules are untouched.
- Focused tests after integration: 195 passed; typecheck, repository-wide lint, CSS parse and diff check passed. Browser screenshots remain unverified in this workspace.
- `PageShell` canvas is opt-in. Integrator publishes the tested fast-forward SHA to `origin/dev` only.
