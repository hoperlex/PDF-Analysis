# Task DESIGN-M07-SYSTEM — logs, workers, analysis settings and queue

## Outcome

System routes use a consistent two-theme hierarchy for filters, tabs, data lists and command confirmation. `/optimisation` continues to redirect to projects.

## Depends on

- `DESIGN-M06-KNOWLEDGE` (completed and published at `1778662fd51a008c6d7d5d133a8334b8a3348d85`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `1778662fd51a008c6d7d5d133a8334b8a3348d85`.
- Design contract: `docs/program/DESIGN-31-SCREEN-PLAN.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: Logs owns a run filter, workers owns three tabs, analysis settings composes existing read-only and gated widgets, queue owns the list/commands, and optimisation redirects to `/projects` after its guard. Presentation can be local to these pages.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/DESIGN-M07-SYSTEM.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/_pages/logs/ui/logs-page.tsx`
- `web/src/_pages/logs/ui/logs-page.module.css`
- `web/src/_pages/workers/ui/workers-page.module.css`
- `web/src/_pages/analysis-settings/ui/analysis-settings-page.tsx`
- `web/src/_pages/analysis-settings/ui/analysis-settings-page.module.css`
- `web/src/_pages/queue/ui/queue-page.tsx`
- `web/src/_pages/queue/ui/queue-page.module.css`

## Forbidden hotspots

- Contracts, migrations, dependencies, backend, route registry, composition root, global styles, optimisation redirect and unrelated screens.
- `origin/main` and preserved AR v3 branch.

## Non-goals

- Changing journal filters, worker permissions, analysis profiles, cost consent, queue commands, or redirect destination.

## Deliverables

- Responsive system panels, tab/list hierarchy and confirmation surface; redirect verified by focused test.
- Updated plan/current-state record and basic focused checks.

## Required tests

- Frontend typecheck, lint, focused logs/workers/settings/queue/redirect tests, CSS parse and diff/changed-path checks.

## Integration contract

Existing widgets, commands, conditions and read order remain unchanged. Styling is local and token-based. The `/optimisation` redirect stays `routes.projects()`.

## Failure/idempotency/security cases

- Error/unknown-outcome states and cost approval remain visible; no gated action is newly enabled.

## Rollback / feature flag

- Revert the single visual commit; no flag, contract or migration is involved.

## Handoff

- Typecheck, lint, CSS parse, diff check and 94 focused system, redirect and
  styling tests passed.
- No forbidden hotspot changed. Start M08 from this commit only after remote
  `origin/dev` confirms its exact SHA.
