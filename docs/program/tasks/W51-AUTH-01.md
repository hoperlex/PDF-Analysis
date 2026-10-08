# Task W51-AUTH-01 — complete the public and account screens

task_id: W51-AUTH-01

## Outcome

A guest can submit a registration request and read the six typed refusals; a pending
applicant sees only the pending sign-in sentence. A signed-in account can finish its
profile, read and edit its names, and change its password. A protected address carried
through sign-in, forced password change and profile completion is opened after those
steps, with `next` validated at each redirect. The existing five AUTH addresses stay
registered and guarded; no administrator screen is implemented in this lane.

## Depends on

- `W51-ROUTES-01` — accepted and merged as
  `bc5d443e54b58044b8a8697eb4f27cfac17cc828` on `origin/dev`.

## Frozen inputs

- Code base: exact clean Stage-A merge
  `bc5d443e54b58044b8a8697eb4f27cfac17cc828`. The executor starts from the
  integrator's exact docs-only AUTH dispatch SHA on `origin/dev`, named at dispatch;
  that commit changes only this task, `W51-PLAN.md` and `PORT_REGISTRY.md`.
- Domain `1.0.0-draft.1` revision 9 / 29 opaque identities; API 27 paths / 34
  operations / 77 schemas; error catalog 23; migration head
  `0015_accounts_roles_registration`. No contract reseal is granted.
- `W51-PLAN.md` §3, §3.1 and Stage B; `W49-PLAN.md` §3.2–§3.5;
  `W51-FREEZE-01.md`; owner rulings `R-48`, `R-55`–`R-60`, `R-63`, `R-66`,
  `R-70`, including `R-56`'s 2026-10-06 addendum. The accepted Stage-A report is
  `docs/program/W51-ROUTES-01.md`.
- Existing BFF doors own the credential and password exchange. `getMe`,
  `updateMyProfile`, `submitRegistration` and `changePassword` are sealed operations;
  the browser never receives a credential or posts a password through a client component.
- Owner direction of 2026-10-08 temporarily defers temporary-stand checks and
  end-of-wave gates to a later separately designed wave. Current implementation
  runs focused basic tests and frontend lint; unrun checks are debt, not passes.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

The five addresses are already in the Stage-A screen registry, route seed list and
journey manifest. This lane changes their rendering and manifest expectations, not
the screen set. Closed refusal values are already declared by the BFF; the AUTH
screens render them without widening the BFF or API vocabulary.

## Captured premise evidence

- premise: Stage A is the exact accepted base, the AUTH screens are present, and the
  existing BFF loses a validated `next` on refusal and forced password change.

### P-01 — accepted base and AUTH route seeds

- captured_at: 2026-10-08
- command: `git rev-parse HEAD && rg -n "address: '/(account|account/password|register|register/submitted|login)'" web/tests/unit/screens/route-screens.ts`
- captured_output:
  ```text
  bc5d443e54b58044b8a8697eb4f27cfac17cc828
  260:    address: '/account',
  266:    address: '/account/password',
  272:    address: '/register',
  278:    address: '/register/submitted',
  326:    address: '/login',
  ```
- interpretation: AUTH changes existing addresses and their five rendering seeds;
  the registry and admin seeds have no new owner here.

### P-02 — current redirect gap

- captured_at: 2026-10-08
- command: `rg -n 'function refuseSignIn|function reportChange|safeReturnPath\(credentials.next\)|return seeOther\(' web/src/app/bff/v1/'[...path]'/route.ts`
- captured_output:
  ```text
  477:function refuseSignIn(refusal: Refusal): Response {
  478:  return seeOther(`${SIGN_IN_SCREEN}?${REFUSAL_PARAM}=${refusal}`);
  483:  return seeOther(`${REGISTER_SCREEN}?${REFUSAL_PARAM}=${refusal}`);
  584:function reportChange(outcome: ChangeOutcome, cookie?: string): Response {
  585:  return seeOther(`${CHANGE_PASSWORD_SCREEN}?${OUTCOME_PARAM}=${outcome}`, cookie);
  721:  return seeOther(
  724:      : (safeReturnPath(credentials.next) ?? AFTER_SIGN_IN),
  779:    return seeOther(SIGN_IN_SCREEN, clearedSessionCookie(requestIsSecure(request)));
  782:  if (subject === null) return seeOther(SIGN_IN_SCREEN, clearedSessionCookie(requestIsSecure(request)));
  861:    return seeOther(SIGN_IN_SCREEN, clearedSessionCookie(requestIsSecure(request)));
  884:    return seeOther(SIGN_IN_SCREEN, clearedSessionCookie(requestIsSecure(request)));
  898:  return seeOther(SIGN_IN_SCREEN, clearedSessionCookie(requestIsSecure(request)));
  1031:  if (answer.status === 201) return seeOther(REGISTER_SUBMITTED_SCREEN);
  ```
- interpretation: a successful ordinary sign-in validates `next`; refusal and
  password outcomes currently drop it. The grant below is limited to preserving
  that validated destination through this flow, not changing credential handling.

### P-03 — account read key and missing profile/registration features

- captured_at: 2026-10-08
- command: `rg -n 'account:|me:|queryKeys.account.me' web/src/shared/api/query-keys.ts web/src/entities/account/api/use-me.ts && rg --files web/src/features | rg '/(register|edit-profile)/' || true`
- captured_output:
  ```text
  web/src/entities/account/api/use-me.ts:4: * `getMe` — the signed-in account, as the API describes it, under `queryKeys.account.me`.
  web/src/entities/account/api/use-me.ts:24:    queryKey: queryKeys.account.me(),
  web/src/shared/api/query-keys.ts:219:  account: {
  web/src/shared/api/query-keys.ts:221:    me: () => ['account', 'me'] as const,
  ```
- interpretation: AUTH reuses the existing `account.me` key and adds feature
  slices for registration and profile editing. `query-keys.ts` stays frozen.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

Stage-A and W49/W50 reports remain immutable. Their live tests may be updated only
inside the exact test paths below; a new needed path is a finding to the integrator.

## Publication authority

- development_target: none
- origin_main_authority: none

## Allowed paths

- `web/src/app/login/**`, `web/src/app/register/**`, `web/src/app/account/**` —
  existing route files and new AUTH route-local files only; retain `requireScreen`
  and the registry's access levels
- `web/src/app/bff/v1/[...path]/route.ts` — validated `next` propagation through
  sign-in refusal, successful sign-in requiring a password change, password
  outcomes and incomplete-profile handoff only; no credential, forwarding,
  throttle or closed-refusal-set changes
- `web/src/_pages/sign-in/**`, `web/src/_pages/register/**`,
  `web/src/_pages/register-submitted/**`, `web/src/_pages/account/**`,
  `web/src/_pages/change-password/**` — the five AUTH screen bodies only
- `web/src/features/sign-in/**`, `web/src/features/register/**`,
  `web/src/features/change-password/**`, `web/src/features/edit-profile/**` —
  public form, typed states, password form and profile mutation; no business rule
  copied from the API
- `web/tests/unit/screens/sign-in*.test.ts`,
  `web/tests/unit/screens/register*.test.ts`,
  `web/tests/unit/screens/account*.test.ts`,
  `web/tests/unit/screens/change-password*.test.ts`, `web/tests/unit/session/**`
- `web/tests/unit/screens/route-screens.ts` — existing `/login`, `/register`,
  `/register/submitted`, `/account`, `/account/password` seeds only; preserve their
  names and route addresses
- `web/tests/unit/styles/screens.ts` — AUTH screen/state contrast seeds only
- `web/tests/guards/dashboard-invalidation.guard.test.ts` — AUTH's profile hook
  entry only; separately assert invalidation of `queryKeys.account.me()` after a
  successful edit
- `web/tests/guards/rendered-language.guard.test.ts` — AUTH screen/state rows and
  translated refusal vocabulary only, with reachable seeds for every new branch
- `tests/e2e/pc01/journey/manifest.json` — expectations/comments of the five AUTH
  routes only; keep the other 22 route entries and all write/refusal steps intact
- `docs/program/W51-AUTH-01.md` — executor completion report

## Forbidden hotspots

Everything else, especially `contracts/**`, migrations, backend, `infra/**`,
Makefile, dependencies/locks, composition roots, global styles, shared UI,
`web/src/shared/config/screen-registry.ts`,
`web/src/shared/api/query-keys.ts`, `web/src/app/bff/session/screen-lock.ts`,
`web/src/app/admin/**`, all administrator seeds and manifest entries,
`tests/e2e/pc01/journey/journey.mjs`, `tests/**/conftest.py`, W49/W50/Stage-A
reports, planning worktrees, integration refs, `origin/**`, tags and deployment.

## Non-goals

- No administrator list, user detail or registration queue behavior; those two
  lanes start only after AUTH is accepted.
- No mail, avatar upload, password reset by link, new API, client-side role or
  password policy, registry rewrite or admin `loading.tsx`.
- No W50 debt repair (`D-134`–`D-136`) and no Stage-C journey or manual-pack rewrite.

## Deliverables

- `/login` explains e-mail sign-in while still accepting the legacy seeded login
  until its one-time `R-59` profile completion. It renders the closed sign-in
  refusal set in Russian, distinguishes only a proven pending request, and shows
  a typed fault for an unknown refusal rather than an empty success state. A
  forged `?refusal=pending` can show only the pending sentence, never a request
  identity, a decision or a reason.
- `/register` is a plain HTML POST to the existing reserved BFF door: surname,
  name, optional patronymic, e-mail, password twice; each name at most 60
  characters and the R-48 password policy explained before submission. The BFF
  remains authoritative; a mismatch is refused before an upstream request. All
  six registration refusals have typed Russian states. `/register/submitted`
  explains the administrator decision and sign-in status without promising mail
  or asserting that a direct visitor actually submitted a request.
- `/account` reads `getMe`, shows names, e-mail, read-only roles and the generated
  avatar preview, and links to `/account/password`. An incomplete legacy account
  submits e-mail and names in one `updateMyProfile` save. Once complete, only
  names are editable and the e-mail control is disabled. The API's typed
  validation/authentication/permission faults remain visible. Successful save
  invalidates `queryKeys.account.me()` and updates the view without another
  sign-in; an unknown role is still a typed fault.
- The validated destination survives sign-in refusal, forced password change,
  its refusal retry, and incomplete-profile completion, then opens that address.
  Invalid or external `next` values are dropped without echo or redirect. The
  password and token stay outside client JavaScript and browser-visible bodies.
  Existing no-`next` password behavior and R-50 forced-change controls remain.

## Required tests

- Focused route/form/BFF tests under the granted paths cover all closed refusal
  members, an unknown member, pending versus rejected/unknown generic sign-in,
  direct `/register/submitted`, legacy profile completion, complete-profile
  e-mail lock, read-only roles, account cache refresh and every `next` hop.
- Deferred mutation probes: drop the validated `next` on one hop; accept an
  external `next`; remove a registration/password mismatch check; silently
  ignore an unknown refusal; enable e-mail editing after completion; remove
  the `account.me` invalidation. Preserve the W49 BFF and W50 R-66 controls
  in the focused tests run now; record the unrun red probes as debt.
- Run focused tests for changed AUTH screens, forms, BFF redirects and cache
  invalidation with `npm --prefix web test -- --run <named test files>`, plus
  `npm --prefix web run lint -- --quiet` and `git diff --check`. Name every
  test file and result in the hand-back. Do not call an unrun check green.
- Deferred debt: full Vitest/typecheck, static PC-01 conformance, production
  build, live registration/profile journey, R-70 light acceptance and the
  end-of-wave/full gate. A later wave will own their design and execution.
  The previous stand-based instructions are withdrawn for this lane by the
  owner's 2026-10-08 direction; no temporary stand is started.

## Integration contract

Hand back a clean `agent/w51-auth-01` branch at an exact SHA with only the paths
above, focused test evidence and `docs/program/W51-AUTH-01.md`. Mutation and
stand evidence not run under the temporary direction is stated as debt. The
integrator checks the grant, accepts and merges that exact tree under the
owner's basic-tests-and-lint direction, and alone may publish `origin/dev`.
`W51-ADMIN-USERS` is written from
the accepted AUTH merge and starts only then; `W51-ADMIN-REQUESTS` follows it.
The executor does not merge, push, tag or deploy. An extra path or a needed new
API/contract rule is a stop and a written finding, not a silent edit.

## Failure/idempotency/security cases

- No temporary stand for this lane under the 2026-10-08 owner direction.
  The former `gate-w51auth` reservation is released in `PORT_REGISTRY.md`.
  No credential enters tracked files, reports or messages.
- Repeating an invalid form submission creates no registration or profile
  mutation; a second successful registration of the same e-mail receives the
  API's conflict state. A forged status query cannot reveal a rejected request.
- Passwords stay in server-handled HTML forms and BFF memory; token and session
  subject stay on their existing sides of the seam. A failure cannot silently
  become a success or a permissive default.

## Rollback / feature flag

Revert the AUTH lane commit. It changes browser screens and BFF redirects, not
stored data or sealed contracts; no new feature flag is introduced.

## Handoff

- changed files and exact allowed-path diff
- focused tests/lint results; unrun acceptance, stand and mutations named as debt
- new/changed contracts: none expected
- known limits, stand cleanup and integrator merge instructions
- forbidden-hotspot proof and open questions as a list, never executor rulings
