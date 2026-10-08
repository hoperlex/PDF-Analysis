# Task W51-ADMIN-REQUESTS — administrator registration queue

task_id: W51-ADMIN-REQUESTS

## Outcome

An administrator sees pending and decided registration requests, the global pending total, and can approve a pending request with at least one role or reject it with a reason. Decisions refresh the queue and home count, show typed Russian failures and never expose an applicant's password.

## Depends on

- `W51-ADMIN-USERS` — accepted and published in merge `c88e794c6565a03aad59d894676216c54e3af99f` on `origin/dev`.

## Frozen inputs

- Exact code base `c88e794c6565a03aad59d894676216c54e3af99f`. Start from the integrator's docs-only ADMIN-REQUESTS dispatch SHA on `origin/dev`, named at dispatch; that commit changes only this task and `W51-PLAN.md`.
- Domain `1.0.0-draft.1` revision 9 / 29 opaque identities; API 27 paths / 34 operations / 77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`. No reseal.
- `W51-PLAN.md` §3 and Stage B, `W49-PLAN.md` §3.4–§3.5, `W51-FREEZE-01.md`, owner rulings R-55–R-61, R-66, R-70; accepted `docs/program/W51-ADMIN-USERS.md`.
- Generated `listRegistrations`, `approveRegistration`, `rejectRegistration`, `RegistrationRequestPage`, `REGISTRATION_STATUS_VALUES`, `ROLE_VALUES`, existing `queryKeys.registrations.*` and `queryKeys.users.all()` are the only contract/cache vocabulary. `request_id` is identity; login/display name are presentation.
- Owner direction 2026-10-08: no temporary stand/end-of-wave gate; focused basic tests and frontend lint only. Unrun checks and known rendered-language branch coverage are debt.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The Stage-A registry already enumerates `/admin/registrations`; this task replaces only its placeholder.

## Captured premise evidence

- premise: accepted ADMIN-USERS base has a guarded registration placeholder and generated operations.

### P-01 — base and placeholder

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n 'RoutePlaceholder|requireScreen' web/src/_pages/admin-registrations/ui/admin-registrations-page.tsx web/src/app/admin/registrations/page.tsx`
- captured_output:
  ```text
  c88e794c6565a03aad59d894676216c54e3af99f
  web/src/app/admin/registrations/page.tsx:4:import { requireScreen } from '../../bff/session/screen-lock';
  web/src/app/admin/registrations/page.tsx:9:  await requireScreen('/admin/registrations', { params, searchParams });
  web/src/_pages/admin-registrations/ui/admin-registrations-page.tsx:1:import { RoutePlaceholder } from '@/shared/ui';
  web/src/_pages/admin-registrations/ui/admin-registrations-page.tsx:5:    <RoutePlaceholder
  ```
- interpretation: the route and guard exist; the queue content is absent.

### P-02 — generated operations

- captured_at: 2026-10-08
- command: `rg -n '^export function (listRegistrations|approveRegistration|rejectRegistration)' web/src/shared/api/generated/client.gen.ts`
- captured_output:
  ```text
  109:export function approveRegistration(
  313:export function listRegistrations(
  397:export function rejectRegistration(
  ```
- interpretation: this lane consumes the published operations and adds none.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/app/admin/registrations/**`; `web/src/_pages/admin-registrations/**`
- `web/src/widgets/registration-queue/**`; `web/src/features/decide-registration/**`; `web/src/entities/registration-request/**`
- `web/tests/unit/screens/admin-registrations*.test.ts`; `web/tests/unit/widgets/registration-*.test.ts`
- `web/tests/guards/dashboard-invalidation.guard.test.ts` — request mutation hook entry only
- `web/tests/guards/rendered-language.guard.test.ts` — request states/statuses/reasons only
- `web/tests/unit/styles/screens.ts` — queue and role-picker states only
- `tests/e2e/pc01/journey/manifest.json` — `/admin/registrations` entry only
- `docs/program/W51-ADMIN-REQUESTS.md`

## Forbidden hotspots

Everything else, especially contracts, migrations, backend, infra, dependencies/lockfiles, composition root, global styles, shared API/config, BFF session/forwarder, AUTH and admin-user screens, screen registry, `tests/e2e/pc01/journey/journey.mjs`, integration refs, tags and `origin/**`.

## Non-goals

- No public registration edits, mail, password disclosure, new API, queue count operation, account-management action or journey/manual-pack rewrite.
- No W50/earlier W51 correction work in this implementation lane. The existing language-guard branch debt is recorded, not silently marked green.

## Deliverables

- List requests oldest first, with `pending_total`, status filter (`pending`, `approved`, `rejected`), opaque cursor paging and explicit loading/empty/error states. A decided request shows its decision/read-only reason; a pending request offers approve/reject controls only to the guarded administrator.
- Approval requires at least one role before any API call and mints one idempotency key per intent. The same key is reused for retry of that intent. Rejection requires 1–256 characters after trim and never submits a 257-character reason. Server `validation_failed`, `permission_denied`, `state_transition_not_allowed`, conflict and idempotency refusals stay typed and visible.
- Successful decision updates the request row and invalidates `registrations.all()` (including the home tile's pending total). Approval also invalidates `users.all()` because it creates an account. The request identity remains `request_id` throughout.
- The journey manifest's registration entry declares its `listRegistrations` read, with no write claimed on mount.

## Required tests

- Focused basic tests for queue states/status translations, pending-only controls, zero roles, 257-character reason, idempotency key reuse per intent, typed API refusals and exact cache invalidation; `npm --prefix web run lint -- --quiet`; `git diff --check`.
- Deferred under the owner's direction: full Vitest/typecheck, static PC-01 conformance, build, live/manual journey, temporary stand, mutation probes, R-70 acceptance, end-of-wave/full gate. Do not report unrun checks as passed.

## Integration contract

Hand back a clean `agent/w51-admin-requests` branch at an exact SHA with only allowed paths, focused test/lint evidence and `docs/program/W51-ADMIN-REQUESTS.md`. The integrator reviews the grant and merges under the owner's basic-check direction, then alone may publish `origin/dev`. Stage C starts only from the accepted merge. No executor push, tag, checkpoint or deployment.

## Failure/idempotency/security cases

- The API decides authorization and legal transitions. UI controls are affordances, never a bypass. Unknown status/role is a typed fault, never a fallback.
- Approval retries retain the exact idempotency key and payload; a new decision intent gets a new key. The applicant password is absent from queue responses and UI state.

## Rollback / feature flag

Revert the lane commit. No stored-data migration or feature flag; decisions already committed by the API are not undone by UI rollback.

## Handoff

- changed files, checks/results, contracts, risks, integration instructions, forbidden-hotspot proof.
