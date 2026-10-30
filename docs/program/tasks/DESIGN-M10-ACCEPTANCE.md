# Task DESIGN-M10-ACCEPTANCE — 31-route lightweight acceptance record

## Outcome

The 31-route design rollout has a checked route inventory, two-theme token/style checks, focused screen render checks and an explicit record of remaining visual limits under the owner's lightweight/dev-only instruction.

## Depends on

- `DESIGN-M09-ACCOUNT` (completed and published at `c3e05a13db2d488d988418455fe0072d66732462`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `c3e05a13db2d488d988418455fe0072d66732462`.
- Design contract: `docs/program/DESIGN-31-SCREEN-PLAN.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: existing registry owner (this task is read-only for the enumerator)
- totality_query: `rg --files web/src/app | rg '/page.tsx$'` and `tests/guards/screen-registry.guard.test.ts`

## Captured premise evidence

- premise: `rg --files web/src/app | rg '/page.tsx$'` lists 31 page files, including the retained `/optimisation` redirect. The design slices M01–M09 already cover their presentation.
- premise: A usable browser runner is unavailable in this workspace. `firefox --version` fails because the snap tries to create `/run/user/0/snap.firefox` on a read-only file system; no Chromium binary is installed, and only 1.3 GB remain on the filesystem. The owner requested basic checks and `dev`, without gates or review windows.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/DESIGN-M10-ACCEPTANCE.md`
- `docs/program/reviews/DESIGN-M10-ACCEPTANCE.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- All application/runtime code, tests, contracts, migrations, dependencies, composition root and global styles.
- `origin/main` and preserved AR v3 branch.

## Non-goals

- Full backend gate, production deployment, live AI spend, browser screenshots or any behavior change.

## Deliverables

- Acceptance record mapping 31 routes to the completed mini-tasks, with checks and known limits.
- Updated plan/current-state status.

## Required tests

- Route registry/set guards, theme/token/styling checks, typecheck, lint, CSS module parse, diff and changed-path checks.

## Integration contract

Documentation only. No runtime, API, contract, migration or behavior change. `origin/dev` advances by one report commit after checks.

## Failure/idempotency/security cases

- The report states precisely which tests failed or were not run. No failed browser/contrast result is presented as passed.

## Rollback / feature flag

- Revert the report commit if needed; runtime has no flag or migration.

## Handoff

- Route/set, theme/token/styling/avatar checks passed (68 tests); typecheck,
  lint and PostCSS parse of 89 modules passed. Full browser and contrast
  acceptance remains explicitly unverified under this lightweight task.
- Changed files are this task, its review report, current state and design
  plan only. No forbidden hotspot changed. This report can be published to
  `origin/dev` after exact remote-SHA verification.
