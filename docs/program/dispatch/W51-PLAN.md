# Wave 51 — screens: sign-in, registration, account; administration of users and requests; identity in the acceptance pack

**Status:** W50 is closed on `origin/dev`; Stage A dispatches from the exact verified
`W51-FREEZE-01` development candidate and its task. **Controlling rulings:** `R-55`, `R-56`,
`R-59`, `R-60`, `R-61`, `R-66`, `R-70`.
**Roles:** lanes, QA, judges and FIX are the executor's; freeze, merges and publication are the
integrator's (`IDENTITY-WAVES.md` §8, as amended by later `R-70`/`AGENTS.md` §8).
**Exit:** the screens are accepted on `origin/dev` under `R-70`; the PC-01 journey and the manual
acceptance pack cover registration, approval, roles, archive and purge. A tag or publication to
`origin/main` requires separate direct owner authority and a full gate on its exact candidate.
No contract change.

## 1. Objective

A person can request an account, learn its status, sign in with an e-mail, complete and edit a
profile, and change a password. An administrator can see the queue, approve with roles or reject
with a reason, list and edit users, archive, restore and purge them, and reset a password. Every
refusal the API gives is shown as a typed state in Russian; no rule is computed in the browser.

## 2. Entry conditions

| Condition | Evidence |
| --- | --- |
| `W50-INT-CLOSE` done: registry, `requireScreen`, primitives, `entities/account`, `/account` placeholder | `origin/dev` |
| W49 operations in the generated client | `operations.gen.ts` names §3.4 of `W49-PLAN.md` |
| alpha acceptance pack baseline | `scripts/manual-alpha-check.sh`, `docs/program/ALPHA-MANUAL-01.md`, `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` at the base |

## 3. Screens

| Address | Access / roles | Group | Lane |
| --- | --- | --- | --- |
| `/login` (reworked) | public; a session redirects home | account, out of menu | AUTH |
| `/register` | public | account, out of menu | AUTH |
| `/register/submitted` | public | account, out of menu | AUTH |
| `/account` (replaces the W50 placeholder) | open-to-default-credential (profile completion) | account | AUTH |
| `/account/password` (existing) | open-to-default-credential | account | AUTH |
| `/admin/users` | session, admin | admin; «Пользователи» | ADMIN-USERS |
| `/admin/users/[user_uid]` | session, admin | admin, out of menu | ADMIN-USERS |
| `/admin/registrations` | session, admin | admin; «Заявки на регистрацию» | ADMIN-REQUESTS |

Behaviour:

- **Sign-in:** e-mail and password; the validated `next` in a hidden field (W50); refusals
  `credentials`, `validation`, `unconfigured`, `upstream`, `pending`, `throttled` each a
  sentence. One generic sentence for a wrong pair — and for a rejected applicant, who sees
  nothing more at sign-in (`R-56` addendum, 2026-10-06; mail will tell them later).
- **Registration:** a plain HTML form posted to the W49 reserved handler, like sign-in: surname,
  name, patronymic (optional), e-mail, password twice; each name ≤ 60 characters; the R-48
  policy explained before submission; the handler's closed refusal set `{validation,
  login_taken, request_pending, queue_full, throttled, upstream}` rendered as six sentences;
  `/register/submitted` says what happens next (an administrator decides; the status is shown at
  sign-in) — no mail is promised (`R-56`).
- **Account:** completion for a legacy account (names and e-mail, one save; `R-59`), then
  profile view/edit (names only), the avatar preview, roles read-only, a link to the password
  screen. Order for the seeded account: password first (`/account/password`), then `/account`,
  as the W50 guard decides.
- **Users:** list with filters (role, archived), the card with names/roles/state, actions edit,
  archive (the API's refusals for self and last admin shown verbatim as typed states), restore,
  purge (offered only for an archived account; the API's `account_referenced` refusal is a typed
  state; a confirmation names the e-mail and says it is irreversible), reset password (temporary
  password entered twice, shown nowhere afterwards).
- **Requests:** queue with `pending_total`, approve with a role picker (at least one), reject
  with a reason of 1–256 characters; decided requests visible read-only with a filter.

Query invalidation after every mutation follows the pattern `dashboard-invalidation.guard.test.ts`
enforces for the dashboard key. W51 also asserts the exact `users` and `registrations` keys in
each owning lane's unit tests; removing an invalidation must make its test red.

### 3.1 Freeze reconciliation from the read-only W51 presweep

`plan/roadmap-to-beta` at `2b45a11` records `W51-PRESWEEP.md` P-1…P-18, including the
SHELL-FRAME re-check. `W51-FREEZE-01` re-measures its path premises on W50's accepted
`75dd708` and resolves the grants here. A further direct sweep found W50 QA and route-builder
pins that presweep did not list; Stage A owns them too.

- AUTH owns the two BFF redirects in `web/src/app/bff/v1/[...path]/route.ts`, the password
  form under `web/src/_pages/change-password/**`, and their tests. Every hop preserves a
  `safeReturnPath`-validated `next`: sign-in refusal, forced password change, incomplete
  profile, then the requested address. No unchecked query value becomes a redirect target.
- A protected `web/src/app/admin/loading.tsx` is **not** created: it would stream a guarded
  redirect as HTTP 200, which `lazy-boundary.guard.test.ts` forbids. Any inner loading state
  belongs to the later screen's widget and its corresponding guard grant.
- `queryKeys.users.*` and `queryKeys.registrations.*` already exist in
  `web/src/shared/api/query-keys.ts`. Stage-B lanes consume them; they do not define duplicate
  factories or edit that frozen file. Stage A re-exports `UserListFilters` and
  `RegistrationListFilters` through `web/src/shared/api/index.ts` so the ADMIN lanes need no
  deep import.
- The new dynamic `/admin/users/[user_uid]` address gets one `routes.user(userUid)` builder
  in `web/src/shared/lib/routes.ts`, with the route-builder totality test updated in Stage A.
  W50's guest-redirect QA needs a well-formed `user_uid` fixture.
- The screen registry, rendered frame, `/403` and return-path tests that assert the W50-only
  empty role-gated set are revised in Stage A to assert the real W51 administrator rows while
  preserving their synthetic role cases. The R-66 work/knowledge/system order remains pinned;
  administrator menu entries are tested separately and remain absent for an expert.
- Stage B is **sequential**: AUTH, then ADMIN-USERS, then ADMIN-REQUESTS, each from the prior
  accepted merge. Each receives only its own entries in the shared
  `dashboard-invalidation.guard.test.ts`, `rendered-language.guard.test.ts`, contrast census
  `web/tests/unit/styles/screens.ts` and journey manifest. The rendered-language matrix
  covers each new widget branch or records why one pass cannot reach it. Identity role,
  registration-status and conflict-reason vocabularies enter its translated-schema markers
  with a seed for every rendered member.
- `W51-E2E-01` uses an administrator journey account. Its runbook grant covers A09's route
  list, the stale home sentence, A01–A20 range wording and the new A13–A20 steps. Its
  `tests/e2e/pc01/**` grant excludes every `conftest.py`; needing one invokes `R-70`'s full
  gate on that lane. A live provider is not required for this journey.

## 4. Tasks

Each task lists `Depends on`; standard forms are in `IDENTITY-WAVES.md` §10.

### `W51-FREEZE-01` (integrator)
Depends on: `W50-INT-CLOSE`. Standard form.

### `W51-ROUTES-01` — Stage A, alone (executor)
- **Depends on:** `W51-FREEZE-01`.
- **Allowed paths:** `web/src/shared/config/screen-registry.ts`, the five new `page.tsx` of §3
  (`/register`, `/register/submitted`, `/admin/users`, `/admin/users/[user_uid]`,
  `/admin/registrations`; `/account` exists since W50) as `RoutePlaceholder` pages with
  `requireScreen`, the placeholder modules `web/src/_pages/register/**`,
  `web/src/_pages/register-submitted/**`, `web/src/_pages/admin-users/**`,
  `web/src/_pages/admin-user/**`, `web/src/_pages/admin-registrations/**` (each exporting a named
  `<Screen>Page` that renders `RoutePlaceholder`; `AdminUserPage` takes `userUid`),
  `tests/e2e/pc01/journey/manifest.json`, `web/tests/unit/screens/route-screens.ts` (seeds),
  `tests/e2e/pc01/journey/journey.mjs` and
  `tests/e2e/test_pc01_journey_conformance.py` (`W51-ROUTES-01-G1`: only a validated
  manifest-declared `user_uid` sample for the no-call detail placeholder),
  `web/src/shared/api/index.ts` (two filter re-exports),
  `web/src/shared/lib/routes.ts` (user-detail builder),
  `web/tests/unit/screens/routes.test.ts` (builder totality),
  `web/tests/guards/screen-guard.guard.test.ts`,
  `web/tests/guards/screen-registry.guard.test.ts`,
  `web/tests/guards/lazy-boundary.guard.test.ts` (`W51-ROUTES-01-G2`: extend only the
  W50-only exact public-route expectation with the two registration addresses),
  `web/tests/unit/screens/home.test.ts`,
  `web/tests/unit/session/return-path.test.ts`,
  `web/tests/unit/shell/navigation.test.ts`,
  `web/tests/unit/shell/screen-decision.test.ts`,
  `web/tests/unit/shell/frame.test.ts`,
  `web/tests/unit/qa_w50/guest-redirects.test.ts`,
  `web/tests/unit/qa_w50/role-gated.test.ts`,
  `web/tests/unit/qa_w50/r66-navigation.test.ts`,
  `docs/program/W51-ROUTES-01.md`. The query namespaces `users` and `registrations` exist since
  W50; the Stage-B lanes use the existing factories, so `query-keys.ts` is not touched.
- **Seed convention:** as `route-screens.ts` does today, every seed renders the named
  `<Screen>Page` export of its `_pages` module and passes only the identities of its dynamic
  segments (`userUid` for `/admin/users/[user_uid]`), never state; AUTH and the ADMIN lanes
  replace the module's content and keep the export name and its props, so the seeds are never
  edited again in this wave.
- **Required tests:** registry completeness both directions; manifest equality; guard sweep,
  including the W50 QA live-row cases and dynamic route builder; `npm --prefix web test --
  --run`; `make light-acceptance` from the last full-gate ancestor, including the live PC-01
  journey on the lane stand. Mutations of an omitted guard, a missing registry row, a wrong
  `user_uid` builder, an expert-offered admin row and a missing or ignored placeholder
  `user_uid` sample must make the owning checks red. ADMIN-USERS replaces the sample
  with a real link capture once the list and detail make API calls.

### Stage B — `W51-AUTH-01` → `W51-ADMIN-USERS` → `W51-ADMIN-REQUESTS` (executor; sequential)
- **Depends on:** ROUTES for AUTH, AUTH for ADMIN-USERS, ADMIN-USERS for ADMIN-REQUESTS.
  Each task file is finalized after its predecessor is accepted, so its `depends_on` names a
  completed task and its frozen base is exact. The order gives shared test/manifest files one
  writer at a time.
- **AUTH allowed paths:** `web/src/app/login/**`, `web/src/app/register/**`,
  `web/src/app/account/**`, `web/src/_pages/sign-in/**`, `web/src/_pages/register/**`,
  `web/src/_pages/account/**`, `web/src/_pages/change-password/**`,
  `web/src/app/bff/v1/[...path]/route.ts` (validated `next` redirects only),
  `web/src/features/sign-in/**`, `web/src/features/register/**`,
  `web/src/features/change-password/**`, `web/src/features/edit-profile/**`,
  `web/tests/unit/screens/{sign-in,register,account}*.test.ts`, `web/tests/unit/session/**`,
  `web/tests/guards/dashboard-invalidation.guard.test.ts` (AUTH hook entry),
  `web/tests/guards/rendered-language.guard.test.ts` (AUTH states),
  `tests/e2e/pc01/journey/manifest.json` (AUTH routes only),
  `docs/program/W51-AUTH-01.md`. Mutations: an unknown refusal value is a typed fault, not a
  blank; the password mismatch is caught before the request; the e-mail field is disabled once
  the profile is complete; a forged `?refusal=pending` shows only the pending sentence.
- **ADMIN-USERS allowed paths:** `web/src/app/admin/users/**`, `web/src/_pages/admin-users/**`,
  `web/src/widgets/user-list/**`, `web/src/widgets/user-card/**`,
  `web/src/features/manage-user/**`, `web/src/entities/user/**`,
  `web/src/_pages/admin-user/**`, `web/tests/unit/screens/admin-users*.test.ts`,
  `web/tests/unit/widgets/user-*.test.ts`,
  `web/tests/guards/dashboard-invalidation.guard.test.ts` (user hooks),
  `web/tests/guards/rendered-language.guard.test.ts` (user states and roles),
  `web/tests/unit/styles/screens.ts` (user/dialog states),
  `tests/e2e/pc01/journey/manifest.json` (user routes only),
  `docs/program/W51-ADMIN-USERS.md`. Mutations: the self-archive and last-admin refusals from the
  API render as typed states; purge is not offered for an active account; a maximum-length name
  (60 characters) in the list does not widen the table at 780 px; after archive, the list is
  refetched (invalidation guard red if removed).
- **ADMIN-REQUESTS allowed paths:** `web/src/app/admin/registrations/**`,
  `web/src/_pages/admin-registrations/**`, `web/src/widgets/registration-queue/**`,
  `web/src/features/decide-registration/**`, `web/src/entities/registration-request/**`,
  `web/tests/unit/screens/admin-registrations*.test.ts`,
  `web/tests/unit/widgets/registration-*.test.ts`,
  `web/tests/guards/dashboard-invalidation.guard.test.ts` (request hooks),
  `web/tests/guards/rendered-language.guard.test.ts` (request states and statuses/reasons),
  `web/tests/unit/styles/screens.ts` (queue/picker states),
  `tests/e2e/pc01/journey/manifest.json` (request route only),
  `docs/program/W51-ADMIN-REQUESTS.md`.
  Mutations: approve with zero roles is refused client-side and the server's refusal is a typed
  state; a reason of 257 characters is refused before the request; after approve, the queue and
  the home tile key are invalidated (guard red if removed).

### `W51-E2E-01` — Stage C (executor)
- **Depends on:** the three Stage-B lanes merged.
- **Allowed paths:** `tests/e2e/pc01/**`, `tests/e2e/test_pc01_journey_conformance.py`,
  `scripts/manual-alpha-check.sh`, `docs/program/ALPHA-MANUAL-01.md`,
  `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` (A09 routes/home, A01–A20 ranges and new steps;
  **the prose guard scans this
  directory** for migration-head and surface claims — state them by command, never by number),
  `docs/program/W51-E2E-01.md`. `tests/e2e/pc01/**` excludes `conftest.py` under the default
  R-70 light path; an explicitly granted fixture edit requires a full lane gate.
- **Deliverables:** journey: register → admin approves with `expert` → the new account signs in
  (its profile came from the request), records a verdict whose author label is "Фамилия И. О."
  → admin removes `expert` → the account's next BFF call answers the 401 envelope, the session
  row is gone and the screen shows the signed-out state with the sign-in link → it signs in again
  → the next mutation is `permission_denied` → archive → sign-in is the generic refusal → purge is
  refused (`account_referenced`, it authored a decision). Refusal cases: a pending applicant sees the pending
  sentence; a rejected applicant's sign-in equals the generic refusal byte-for-byte; self-archive,
  last admin, zero roles. Manual steps A13–A20 added to the pack
  with expected sentences.
- **Required tests:** the journey against a built stand with `provider_mode=recorded` and an
  administrator account; the
  conformance test; `shellcheck scripts/manual-alpha-check.sh`.

### `W51-QA-01`, `W51-JUDGE-X`, `W51-JUDGE-Y` (executor, fresh contexts), `W51-FIX` (executor), `W51-INT-CLOSE` (integrator)
- QA: standard form, files under `web/tests/unit/qa_w51/**`: every screen with every role set,
  profile state and the guest; every API refusal of W49 §3.2–§3.3 rendered.
- X (built stand, black-box first): enumeration through registration; flooding to the cap from
  the form and from `/api/v1/` directly; open redirect via `next` and `from`; a rejected
  applicant learns nothing at sign-in and the reason is visible only to administrators; role removal takes
  effect on the next request as a closed session; keyboard-only completion of registration and
  approval; 780 × 900 with maximum-length names and a 256-character reason; console clean.
- Y: no business rule in a component (`rg -n 'roles.length|isLastAdmin|=== me' web/src` finds
  only presentation); FSD boundaries; typed states for every closed vocabulary (`role`, `status`,
  `conflict_reason`, refusal); invalidation after each mutation; registry, manifest and seeds
  complete; lock bytes unchanged.
- INT-CLOSE: standard form; the alpha acceptance pack is the release evidence for `alpha-w51`.

## 5. Integration order

1. `W51-FREEZE-01`.
2. Stage A: `W51-ROUTES-01`.
3. Stage B: `W51-AUTH-01` → `W51-ADMIN-USERS` → `W51-ADMIN-REQUESTS`, each from the prior
   accepted merge, with shared guard and manifest files updated by one owner at a time.
4. Stage C: `W51-E2E-01`.
5. `W51-QA-01`; judges X and Y; cross-examination; `W51-FIX`.
6. `W51-INT-CLOSE`.

## 6. Ownership matrix

| Hotspot / path family | Owner | Role | Parallel writer |
| --- | --- | --- | --- |
| `contracts/**`, migrations, backend, root locks, `globals.css`, `_app/**`, `shared/ui/**`, `screen-lock.ts` | frozen | — | none |
| `screen-registry.ts`, `route-screens.ts`, screen/frame/W50-QA pins, route builder, API filter exports, `manifest.json`, five placeholder `_pages` modules | `W51-ROUTES-01` (Stage A) | executor | none |
| `shared/api/query-keys.ts` | frozen (namespaces entered in W50) | — | none |
| `app/{login,register,account}/**`, BFF validated redirects, `_pages/{sign-in,register,account,change-password}/**`, `features/{sign-in,register,change-password,edit-profile}/**` | `W51-AUTH-01` | executor | none; before ADMIN-USERS |
| `app/admin/users/**`, `_pages/{admin-users,admin-user}/**`, `widgets/{user-list,user-card}/**`, `features/manage-user/**`, `entities/user/**` | `W51-ADMIN-USERS` | executor | none; after AUTH, before ADMIN-REQUESTS |
| `app/admin/registrations/**`, `_pages/admin-registrations/**`, `widgets/registration-queue/**`, `features/decide-registration/**`, `entities/registration-request/**` | `W51-ADMIN-REQUESTS` | executor | none; after ADMIN-USERS |
| `dashboard-invalidation.guard.test.ts`, `rendered-language.guard.test.ts`, `styles/screens.ts`, journey manifest's Stage-B route entries | Stage-B lane currently executing | executor | sequential ownership only |
| `tests/e2e/**`, `scripts/manual-alpha-check.sh`, acceptance docs | `W51-E2E-01` (Stage C) | executor | none |
| `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `origin/dev` | `W51-INT-CLOSE` | integrator | none |

## 7. Stop conditions

`W48-PLAN.md` §14, plus: a screen needs an operation or a detail W49 did not seal; a rule has to
be computed in the browser because the API does not refuse it; a global style or a primitive is
missing and would have to be added outside W50's ownership (then a bounded `W51-SHELL-FIX`
grant, not a silent edit); the journey needs a live provider (it must not).

## 8. Non-goals

Mail; captcha; avatar upload; password reset by link; bulk user import or bulk rejection; an
audit log of administrator actions beyond what `decided_by`/`archived_by`/`granted_by` record;
any API change.

## 9. After W51

Candidates for the next planning round, registered rather than scheduled: SMTP and
notifications; avatar upload; a deployed-revision endpoint; bulk rejection and request retention;
the normative corpus plane withdrawn with the old W49; retiring `display_name`; renaming
`is_default_credential`.
