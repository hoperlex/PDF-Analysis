# Task DESIGN-M09-ACCOUNT — profile, password and administration

## Outcome

The profile, password, users list, user detail and registration queue routes share the two-theme card rhythm with responsive forms and tables.

## Depends on

- `DESIGN-M08-ACCESS` (completed and published at `5f604db11388248782fc9aae5043f0ca2cbc286e`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `5f604db11388248782fc9aae5043f0ca2cbc286e`.
- Design contract: `docs/program/DESIGN-31-SCREEN-PLAN.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: These five routes already compose the profile/password and admin list/detail/queue widgets. Styling local mounts and existing table/queue CSS preserves their access and command behavior.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/DESIGN-M09-ACCOUNT.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/_pages/account/ui/account-page.tsx`
- `web/src/_pages/account/ui/account-page.module.css`
- `web/src/_pages/change-password/ui/change-password-page.tsx`
- `web/src/_pages/change-password/ui/change-password-page.module.css`
- `web/src/_pages/admin-users/ui/admin-users-page.tsx`
- `web/src/_pages/admin-users/ui/admin-users-page.module.css`
- `web/src/_pages/admin-user/ui/admin-user-page.tsx`
- `web/src/_pages/admin-user/ui/admin-user-page.module.css`
- `web/src/_pages/admin-registrations/ui/admin-registrations-page.tsx`
- `web/src/_pages/admin-registrations/ui/admin-registrations-page.module.css`
- `web/src/widgets/user-list/ui/user-list.module.css`
- `web/src/widgets/registration-queue/ui/registration-queue.module.css`

## Forbidden hotspots

- Contracts, migrations, dependencies, backend, route registry, auth forms, composition root, global styles and unrelated screens.
- `origin/main` and preserved AR v3 branch.

## Non-goals

- Changing profile/password submissions, account roles, user commands, registration decisions or permissions.

## Deliverables

- Responsive account/admin cards, contained tables and registration rows.
- Updated plan/current-state record and basic focused checks.

## Required tests

- Frontend typecheck, lint, focused account/password/admin tests, CSS parse and diff/changed-path checks.

## Integration contract

Existing widgets, actions, props and state branches retain behavior. New wrappers and CSS consume shared tokens in both themes.

## Failure/idempotency/security cases

- Loading/error states and unknown outcome/confirmation controls stay in their existing branches; no sensitive value is newly rendered.

## Rollback / feature flag

- Revert the single visual commit; no flag, contract or migration is involved.

## Handoff

- Typecheck, lint, CSS parse, diff check and 61 focused account, password,
  admin and styling tests passed.
- No forbidden hotspot changed. Start M10 from this commit only after remote
  `origin/dev` confirms its exact SHA.
