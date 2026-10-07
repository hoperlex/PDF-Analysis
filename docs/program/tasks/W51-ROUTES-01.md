# Task W51-ROUTES-01 — register and guard five W51 screen addresses

## Outcome

The W51 route tree, one screen registry, journey manifest, renderer seeds and dynamic route
builder agree on all **27** real screens. Three administrator routes are role-gated; an expert
cannot open or see them in the menu. New routes render typed placeholders only, so Stage-B
owners can fill them without changing the registry or seed names.

## Depends on

- `W51-FREEZE-01` — the published freeze commit named by the integrator at dispatch.

## Frozen inputs

- Code base: W50 close `75dd70843b7c3a2a7451368da28376abb899cf26`; dispatch starts
  from the exact `W51-FREEZE-01` SHA on `origin/dev`, which changes programme docs only.
- W50 counts: 22 registered screens, 23 production-build page rows including synthetic
  `/_not-found`; this task adds five real addresses. W50 guards and shell are unchanged.
- Domain `1.0.0-draft.1` revision 9 / 29 opaque identities; API 27 paths / 34 operations /
  77 schemas; error catalog 23; migration head `0015_accounts_roles_registration`.
- `W51-PLAN.md` §3.1/§4 as reconciled by `W51-FREEZE-01`, owner rulings `R-60`, `R-66`,
  `R-70`, and the planning-owned `W51-PRESWEEP.md` at `2b45a11` (read-only).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `web/src/shared/config/screen-registry.ts`
- enumerator_owner: `W51-ROUTES-01`
- totality_query: `npm --prefix web test -- --run tests/guards/screen-registry.guard.test.ts tests/guards/screen-set.guard.test.ts`

The registry owns the set; the guard compares it both ways with `page.tsx`, while the screen
set guard compares every address with a rendering seed. The PC-01 conformance test compares
the journey manifest with the route tree separately.

## Captured premise evidence

- premise: the W50 base has 22 real routes and several tests pin the W50-only empty admin set

### P-01 — current real route count

- captured_at: 2026-10-07
- command: `rg --files web/src/app -g 'page.tsx' | wc -l`
- captured_output:
  ```text
  22
  ```
- interpretation: the real W51 target is 27; a Next build's `/_not-found` row is synthetic.

### P-02 — the guard pin that a new admin row must move

- captured_at: 2026-10-07
- command: `rg -n 'admin: \[\]|role-gated set|links nowhere in W50' web/tests/guards/screen-registry.guard.test.ts web/tests/unit/screens/home.test.ts`
- captured_output:
  ```text
  web/tests/guards/screen-registry.guard.test.ts:129:  admin: [],
  web/tests/guards/screen-registry.guard.test.ts:206:  it('R-60: the role-gated set is as measured — empty in W50, W51 adds the administrator rows', () => {
  web/tests/unit/screens/home.test.ts:313:  it('links nowhere in W50, because the registry has no row for the registration screen', () => {
  ```
- interpretation: the grant covers these exact tests and the other live-registry pins listed
  below; the tests must change with the enumerated set, not be deleted or weakened.

### P-03 — the new dynamic address needs a builder and a QA identifier

- captured_at: 2026-10-07
- command: `rg -n "it\('D-94: every address with a dynamic segment|^  project_uid:" web/tests/unit/screens/routes.test.ts web/tests/unit/qa_w50/guest-redirects.test.ts`
- captured_output:
  ```text
  web/tests/unit/qa_w50/guest-redirects.test.ts:86:  project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
  web/tests/unit/screens/routes.test.ts:497:  it('D-94: every address with a dynamic segment is built by a builder', () => {
  ```
- interpretation: Stage A adds a user-detail route builder and a well-formed `user_uid`
  fixture before the dynamic route enters the live enumeration.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

The W50 QA reports stay immutable. Their tests may be updated to measure the expanded live
registry while retaining the W50 synthetic role controls.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/shared/config/screen-registry.ts` — exactly five rows; the three admin rows use
  `roles: ['admin']`, the two registration rows are `public`/`account`/out of menu; menu order
  is `/admin/users` «Пользователи», then `/admin/registrations` «Заявки на регистрацию»
- `web/src/app/register/page.tsx`
- `web/src/app/register/submitted/page.tsx`
- `web/src/app/admin/users/page.tsx`
- `web/src/app/admin/users/[user_uid]/page.tsx`
- `web/src/app/admin/registrations/page.tsx`
- `web/src/_pages/register/**`, `web/src/_pages/register-submitted/**`,
  `web/src/_pages/admin-users/**`, `web/src/_pages/admin-user/**`,
  `web/src/_pages/admin-registrations/**` — named `RegisterPage`,
  `RegisterSubmittedPage`, `AdminUsersPage`, `AdminUserPage(userUid)`,
  `AdminRegistrationsPage` exports with `RoutePlaceholder` bodies
- `web/src/shared/lib/routes.ts` — `routes.user(userUid)` only
- `web/src/shared/api/index.ts` — re-export existing `UserListFilters` and
  `RegistrationListFilters` only; `query-keys.ts` is frozen
- `tests/e2e/pc01/journey/manifest.json` — five route entries with placeholder-accurate
  no-call expectations; role-aware redirects and a well-formed `user_uid` sample; the W51
  journey account holds `admin`, as the freeze decides
- `tests/e2e/pc01/journey/journey.mjs` — `W51-ROUTES-01-G1` only: resolve the
  manifest-declared `user_uid` sample for the placeholder detail route when no earlier
  screen provides an actual identity; preserve captured-link precedence, cold loads and
  all request/response checks
- `tests/e2e/test_pc01_journey_conformance.py` — `W51-ROUTES-01-G1` only: statically
  validate that the sample is a well-formed `usr_<ULID>`, names exactly the route's
  dynamic segment, and is allowed only while that detail route has no API expectations
- `web/tests/unit/screens/route-screens.ts` — one seed per new address, preserving existing
  names/props; Stage B keeps those export names and props
- `web/tests/guards/screen-registry.guard.test.ts`,
  `web/tests/guards/screen-guard.guard.test.ts`
- `web/tests/unit/screens/home.test.ts`, `web/tests/unit/screens/routes.test.ts`
- `web/tests/unit/session/return-path.test.ts`
- `web/tests/unit/shell/navigation.test.ts`,
  `web/tests/unit/shell/screen-decision.test.ts`, `web/tests/unit/shell/frame.test.ts`
- `web/tests/unit/qa_w50/guest-redirects.test.ts`,
  `web/tests/unit/qa_w50/role-gated.test.ts`,
  `web/tests/unit/qa_w50/r66-navigation.test.ts`
- `docs/program/W51-ROUTES-01.md` — completion report

## Forbidden hotspots

- Everything else, especially `contracts/**`, migrations, backend, `infra/**`, Makefile,
  dependency/lock files, `web/src/app/admin/loading.tsx`, composition roots, global styles,
  `web/src/shared/api/query-keys.ts`, W50 reports, planning worktrees, integration refs,
  `origin/**`, tags and deployment.

## Non-goals

- No registration, account or administrator feature behavior yet; placeholders perform no
  API call and invent no data. Stage-B lanes own screen implementations.
- No new API, role rule in a component, admin segment `loading.tsx`, dependency or styling
  change. Do not repair W50's open D-134…D-136 under this grant.

## Deliverables

- Five guarded placeholder pages and exactly matching registry rows/renderer seeds/manifest.
- A typed user-detail builder and filter type exports through existing public barrels.
- Tests updated to assert the **live** admin-gated set and role-specific menu, preserving
  W50's R-66 and synthetic role controls. A guest receives a real 307 with validated `next`.
- A report with changed files, acceptance and mutation results, contracts, known limits,
  resource cleanup, integration handoff and forbidden-hotspot proof.

## Required tests

- Registry/page/seed/manifest equality, guard sweep, builder totality, home tile link,
  W50 QA live rows and dynamic `user_uid`, frontend lint/typecheck/full Vitest suite.
- `W51-ROUTES-01-G1`: conformance must reject a missing, malformed or misnamed
  `user_uid` sample, and a mutation removing its use from the journey must go red.
- Mutations: remove a new registry row; omit a guard call; offer an admin row to an expert;
  break `routes.user` or remove its well-formed QA sample. Each controlling check must go red.
- On the clean committed lane tree, `make light-acceptance
  BASE=d8ea61351489fcf08c7ebfe8ff90045b2127b559` with literal
  `LIGHT ACCEPTANCE OK`. It selects the live PC-01 journey for these screen changes, so run
  the lane's own production stand with an administrator journey account and
  `E2E_PC01_ORIGIN`, `E2E_PC01_LOGIN` and `E2E_PC01_PASSWORD`. `git diff --check` is
  included. A changed R-70 risk path instead
  requires a complete `make gate` on that lane.

## Integration contract

Hand back a clean `agent/w51-routes-01` branch at an exact SHA with only the paths above.
The integrator checks the grant, accepts and merges the exact tree, runs post-merge R-70
acceptance and alone may publish `origin/dev`. Stage-B AUTH begins from the accepted Stage-A
merge; ADMIN-USERS and ADMIN-REQUESTS follow sequentially. An extra needed path is a finding,
not a silent edit.

### Integrator written grant `W51-ROUTES-01-G1`, 2026-10-07

The executor stopped before an out-of-grant edit: `journey.mjs` fills
`/admin/users/{user_uid}` only from earlier rendered links, while the Stage-A
`/admin/users` placeholder has no API call and cannot provide a real user link. A
fabricated product link would violate this task's no-invented-data rule. The two test
instrument paths above are granted solely for a manifest-declared sample on the
no-call placeholder route. It must never substitute for a captured real identifier or
make a later `getUser` call appear covered. When ADMIN-USERS makes the list and detail
real, it replaces this sample with link capture and restores the journey's real-ID
rule. This grant does not change the frozen base, contracts, migrations or product scope.
The executor names this grant in its report; the integrator merges its lane onto the
grant-bearing `integration/w51` tip.

## Failure/idempotency/security cases

- Dedicated `gate-w51routes`: PostgreSQL `56760`, MinIO `60360/60361`, API `56860`, Next
  `31360`, unique database/bucket. Check all ports free immediately before starting. Operate
  only this lane's containers/processes and remove its volumes and temporary credentials on
  hand-back. No secret enters tracked files or reports.
- No protected `loading.tsx`; an admin guest must receive HTTP 307, not a streamed 200.
- A role-gated route refuses an expert, empty roles and unknown roles; a complete admin opens
  it. Dynamic `user_uid` is opaque and remains an identity, never a display number or path
  inferred from a filename.
- A stand/setup failure is void evidence, not a green result. Keep the measured tree clean
  while checks run.

## Rollback / feature flag

Revert the Stage-A commit. These are guarded placeholders and registry entries, with no new
feature flag or persisted data.

## Handoff

- changed files and exact grant diff
- commands/results including the literal acceptance sentinel and red mutations
- new/changed contracts: none expected
- known limits, cleanup and integrator merge instructions
