# Task DESIGN-M04-RUN — dispatcher, run and review presentation

## Outcome

The dispatcher, run and expert review routes use the shared two-theme panel hierarchy with readable status, lists and actions at compact widths.

## Depends on

- `DESIGN-M03-PROJECT` (completed and published at `8011c3720250407f586779324862c478c820a625`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `8011c3720250407f586779324862c478c820a625`.
- Design contract: `docs/program/DESIGN-31-SCREEN-PLAN.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: The dispatcher has role-gated assignment sections, Run owns the existing progress component and polling, and Review already has a two-column list/detail layout and an export below it. Styling these mounts locally preserves those contracts.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/DESIGN-M04-RUN.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/_pages/dispatcher/ui/dispatcher-page.tsx`
- `web/src/_pages/dispatcher/ui/dispatcher-page.module.css`
- `web/src/_pages/run/ui/run-page.tsx`
- `web/src/_pages/run/ui/run-page.module.css`
- `web/src/_pages/review/ui/review-page.tsx`
- `web/src/_pages/review/ui/review-page.module.css`
- `web/src/widgets/run-progress/ui/run-progress.tsx`
- `web/src/widgets/run-progress/ui/run-progress.module.css`

## Forbidden hotspots

- Contracts, migrations, dependencies, backend, route registry, composition root, global styles and unrelated screens.
- `origin/main` and preserved AR v3 branch.

## Non-goals

- Changing assignment permissions, run polling, statuses, observations, evidence, verdicts, export or the AR v3 flow.

## Deliverables

- Responsive dispatcher cards, contained Run summary and stage presentation, Review list/detail/export cards.
- Updated plan/current-state record and basic focused checks.

## Required tests

- Frontend typecheck, lint, focused dispatcher/run/review render tests, CSS parse and diff/changed-path checks.

## Integration contract

The existing data and control components keep their order and conditional mounts. New classes use the shared semantic tokens; no new business state, API call or route is introduced.

## Failure/idempotency/security cases

- Pending/error/empty states remain in place. Review's finding admission and export position stay intact. The Run uses its existing polling loop.

## Rollback / feature flag

- Revert the single visual commit; no flag, contract or migration is involved.

## Handoff

- Typecheck, lint, CSS parse, diff check and 128 focused dispatcher, Run,
  Review and styling tests passed.
- No forbidden hotspot changed. Start M05 from this commit only after remote
  `origin/dev` confirms its exact SHA.
