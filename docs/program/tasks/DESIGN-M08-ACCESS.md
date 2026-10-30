# Task DESIGN-M08-ACCESS — login, register, submitted and forbidden screens

## Outcome

The four public/access routes use the shared light/dark palette, centered form hierarchy and readable notice panels without changing exchange or guard behavior.

## Depends on

- `DESIGN-M07-SYSTEM` (completed and published at `0a4e664ab007b2d31b87f73ce7521e5b77357c5a`).

## Frozen inputs

- Domain/API/analysis/events contract: `1.13.0`.
- API surface: 230 paths / 256 operations / 619 schemas.
- Migration head: `0043_stage_ai_generations`.
- Base commit: `0a4e664ab007b2d31b87f73ce7521e5b77357c5a`.
- Design contract: `docs/program/DESIGN-31-SCREEN-PLAN.md`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: Login already has a guest card, register composes a server form, submitted shows a notice, and 403 presents the registry-derived requirement. The task styles these existing mounts only.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: `origin/dev`
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/DESIGN-M08-ACCESS.md`
- `docs/program/DESIGN-31-SCREEN-PLAN.md`
- `docs/program/CURRENT_STATE.md`
- `web/src/_pages/sign-in/ui/sign-in-page.module.css`
- `web/src/_pages/register/ui/register-page.tsx`
- `web/src/_pages/register/ui/register-page.module.css`
- `web/src/_pages/register-submitted/ui/register-submitted-page.tsx`
- `web/src/_pages/register-submitted/ui/register-submitted-page.module.css`
- `web/src/_pages/forbidden/ui/forbidden-page.tsx`
- `web/src/_pages/forbidden/ui/forbidden-page.module.css`

## Forbidden hotspots

- Contracts, migrations, dependencies, backend, route registry, auth form implementation, composition root, global styles and unrelated screens.
- `origin/main` and preserved AR v3 branch.

## Non-goals

- Changing credentials handling, registration exchange, guard redirects, role requirements or copy.

## Deliverables

- Centered access cards and notice panels with responsive spacing in both themes.
- Updated plan/current-state record and basic focused checks.

## Required tests

- Frontend typecheck, lint, focused login/registration/403 tests, CSS parse and diff/changed-path checks.

## Integration contract

Existing forms, links, refusal branches and route props stay intact. New wrappers/classes consume only shared semantic tokens.

## Failure/idempotency/security cases

- Unknown refusals and invalid role requirements retain the existing closed handling. No secret is read into page state.

## Rollback / feature flag

- Revert the single visual commit; no flag, contract or migration is involved.

## Handoff

- Typecheck, lint, CSS parse, diff check and 41 focused access and styling
  tests passed.
- No forbidden hotspot changed. Start M09 from this commit only after remote
  `origin/dev` confirms its exact SHA.
