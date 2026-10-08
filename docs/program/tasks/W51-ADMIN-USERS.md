# Task W51-ADMIN-USERS — administrator account management screens

task_id: W51-ADMIN-USERS

## Outcome

An administrator can list accounts, open one by opaque `user_uid`, edit its names and role set, archive, restore, purge eligible archived accounts, and reset a password. The screens render typed Russian refusals and refresh the affected account keys after writes. A non-administrator remains behind the already registered route guard and the API's own authorization.

## Depends on

- `W51-AUTH-01` — accepted and published in merge `ebe614dea0954dc54937955d494231a7d9443ccb` on `origin/dev`.

## Frozen inputs

- Exact code base `ebe614dea0954dc54937955d494231a7d9443ccb`. Start from the integrator's docs-only ADMIN-USERS dispatch SHA on `origin/dev`, named at dispatch; that commit changes only this task and `W51-PLAN.md`.
- Domain `1.0.0-draft.1` revision 9 / 29 opaque identities; API 27 paths / 34 operations / 77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`. No contract reseal.
- `W51-PLAN.md` §3/Stage B and §3.1, `W49-PLAN.md` §3.4–§3.5, `W51-FREEZE-01.md`, owner rulings R-55, R-59–R-61, R-66, R-70, and accepted `docs/program/W51-AUTH-01.md`.
- Generated `listUsers`, `getUser`, `updateUser`, `archiveUser`, `restoreUser`, `purgeUser`, `resetUserPassword`, existing `queryKeys.users.*`, `queryKeys.account.me()`, `queryKeys.dashboard.summary()`, and `routes.user(userUid)` are the only API/cache/route vocabulary. `user_uid` is identity; login/display name are presentation.
- Owner direction 2026-10-08: no temporary stand or end-of-wave gate; run focused basic tests and frontend lint only. Unrun checks are validation debt.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The Stage-A registry already enumerates both administrator user addresses. This task changes their content, never the screen set.

## Captured premise evidence

- premise: accepted AUTH base has two guarded admin user placeholders and generated account operations.

### P-01 — exact base and placeholders

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n 'RoutePlaceholder|requireScreen' web/src/_pages/admin-users/ui/admin-users-page.tsx web/src/_pages/admin-user/ui/admin-user-page.tsx web/src/app/admin/users/page.tsx web/src/app/admin/users/'[user_uid]'/page.tsx`
- captured_output:
  ```text
  ebe614dea0954dc54937955d494231a7d9443ccb
  web/src/app/admin/users/[user_uid]/page.tsx:5:import { requireScreen } from '../../../bff/session/screen-lock';
  web/src/app/admin/users/[user_uid]/page.tsx:16:  await requireScreen('/admin/users/[user_uid]', { params, searchParams });
  web/src/app/admin/users/page.tsx:4:import { requireScreen } from '../../bff/session/screen-lock';
  web/src/app/admin/users/page.tsx:9:  await requireScreen('/admin/users', { params, searchParams });
  web/src/_pages/admin-users/ui/admin-users-page.tsx:1:import { RoutePlaceholder } from '@/shared/ui';
  web/src/_pages/admin-users/ui/admin-users-page.tsx:5:    <RoutePlaceholder
  web/src/_pages/admin-user/ui/admin-user-page.tsx:2:import { RoutePlaceholder } from '@/shared/ui';
  web/src/_pages/admin-user/ui/admin-user-page.tsx:10:    <RoutePlaceholder
  ```
- interpretation: both routes exist and are guarded; only their page implementations are missing.

### P-02 — generated seam

- captured_at: 2026-10-08
- command: `rg -n '^export function (listUsers|getUser|updateUser|archiveUser|restoreUser|purgeUser|resetUserPassword)' web/src/shared/api/generated/client.gen.ts`
- captured_output:
  ```text
  121:export function archiveUser(
  229:export function getUser(
  349:export function listUsers(
  373:export function purgeUser(
  409:export function resetUserPassword(
  421:export function restoreUser(
  481:export function updateUser(
  ```
- interpretation: this lane consumes generated operations; it adds none.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/app/admin/users/**`; `web/src/_pages/admin-users/**`; `web/src/_pages/admin-user/**`
- `web/src/widgets/user-list/**`; `web/src/widgets/user-card/**`; `web/src/features/manage-user/**`; `web/src/entities/user/**`
- `web/tests/unit/screens/admin-users*.test.ts`; `web/tests/unit/widgets/user-*.test.ts`
- `web/tests/guards/dashboard-invalidation.guard.test.ts` — user mutation hooks only
- `web/tests/guards/rendered-language.guard.test.ts` — user states and roles only
- `web/tests/unit/styles/screens.ts` — user and confirmation states only
- `tests/e2e/pc01/journey/manifest.json` — the two admin-user entries only
- `docs/program/W51-ADMIN-USERS.md`

## Forbidden hotspots

Everything else, especially contracts, migration head, backend, infra, dependencies/lockfiles, composition root, global styles, shared API/config, BFF session/forwarder, AUTH and registration screens, registration queue, screen registry, `tests/e2e/pc01/journey/journey.mjs`, integration refs, tags and `origin/**`.

## Non-goals

- No registration queue or approval/rejection, new route, new API filter, admin-created account, password reset e-mail, upload, or contract change.
- No W50 debt repair or end-of-wave review/acceptance in this implementation lane.

## Deliverables

- List accounts with archived toggle, role filter, pagination and a detail link built from `user_uid`. Keep role filtering honest about whether it covers the current page or all loaded pages; the API itself has no role query parameter. A 60-character name fits the 780 px floor without widening the table.
- Detail shows login, name, roles, archive state and editable names/whole role set. Self-role removal, self-archive and last-admin refusal are explicit typed states; the API remains authoritative. After role change, warn that credentials for the changed account are revoked.
- Archive/restore, and purge only for an archived account with an explicit irreversible confirmation naming its login. `account_referenced`, `login_taken`, `last_admin` and invalid state transitions render typed Russian refusals. Successful writes refresh the exact `users` list/detail keys and any affected `account.me`/home count, without a stale detail card.
- Reset a temporary password entered twice. A mismatch stops before the generated operation, and the value is never echoed into markup, a log, or a success body. The account must change that password at its next sign-in.
- The two journey manifest entries describe the real reads on mount; no live write is claimed there.

## Required tests

- Focused basic tests for list/detail states, filters, actions and typed refusal mapping; self/last-admin and `account_referenced`, active purge unavailable, password mismatch, user cache invalidation, 60-character wrapping; `npm --prefix web run lint -- --quiet`; `git diff --check`.
- Deferred debt under the owner's instruction: full Vitest/typecheck, static PC-01 conformance, build, live/manual journey, mutation probes, temporary stand, R-70 acceptance, end-of-wave/full gate. Do not call an unrun check green.

## Integration contract

Hand back a clean `agent/w51-admin-users` branch at an exact SHA with only allowed paths, focused test/lint evidence and `docs/program/W51-ADMIN-USERS.md`. The integrator checks the grant, merges the exact candidate under the owner's basic-check direction and alone publishes `origin/dev`. `W51-ADMIN-REQUESTS` starts only from that accepted merge. No executor push, tag, checkpoint or deployment.

## Failure/idempotency/security cases

- Mutations use the generated API and opaque `user_uid`; no direct SQL, token, session or path-as-identity. Never infer permissions from UI role check; show API refusal.
- A failed write leaves displayed data and cache unchanged. Purge is unavailable for an active account. A reset value is held only for submission, never rendered back.

## Rollback / feature flag

Revert the lane commit. The lane changes screens and query caches only; no stored-data migration or feature flag is introduced. Administrator write actions themselves remain server-authorized.

## Handoff

- changed files, checks and results, contracts, risks, integration instructions, forbidden-hotspot proof.
