# Wave 51 — screens: sign-in, registration, account; administration of users and requests; identity in the acceptance pack

**Status:** planned; dispatchable after `W50-INT-CLOSE` and `W51-FREEZE-01`.
**Controlling rulings:** `R-55`, `R-56`, `R-59`, `R-60`, `R-61` (provisional numbers).
**Roles:** lanes, QA, judges and FIX are the executor's; freeze, merges, the final gate and
publication are the integrator's (`IDENTITY-WAVES.md` §8).
**Exit:** the screens on `origin/dev` with literal `GATE OK`; the PC-01 journey and the manual
acceptance pack cover registration, approval, roles, archive and purge. No contract change.

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
| `/login` (reworked) | public; a session redirects home | hidden | AUTH |
| `/register` | public | hidden | AUTH |
| `/register/submitted` | public | hidden | AUTH |
| `/account` (replaces the W50 placeholder) | open-to-default-credential (profile completion) | account | AUTH |
| `/account/password` (existing) | open-to-default-credential | account | AUTH |
| `/admin/users` | session, admin | admin | ADMIN-USERS |
| `/admin/users/[user_uid]` | session, admin | admin | ADMIN-USERS |
| `/admin/registrations` | session, admin | admin | ADMIN-REQUESTS |

Behaviour:

- **Sign-in:** e-mail and password; the validated `next` in a hidden field (W50); refusals
  `credentials`, `validation`, `unconfigured`, `upstream`, `pending`, `rejected`, `throttled` each
  a sentence; for `pending`/`rejected` the page reads the one-time notice named by `?notice=` from
  the register (W49 §3.5) and shows the status and, for a rejection, the reason (≤ 256
  characters); a missing or used notice shows the status sentence without a reason. One generic
  sentence for a wrong pair.
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
now enforces (behaviour, not comments).

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
  `web/src/app/admin/loading.tsx`,
  `tests/e2e/pc01/journey/manifest.json`, `web/tests/unit/screens/route-screens.ts` (seeds),
  `web/tests/guards/screen-guard.guard.test.ts` (open-screen register),
  `docs/program/W51-ROUTES-01.md`. The query namespaces `users` and `registrations` exist since
  W50; the Stage-B lanes add key factories inside them in their own `entities/*` modules, so
  `query-keys.ts` is not touched in this wave.
- **Seed convention:** as `route-screens.ts` does today, every seed renders the named
  `<Screen>Page` export of its `_pages` module and passes only the identities of its dynamic
  segments (`userUid` for `/admin/users/[user_uid]`), never state; AUTH and the ADMIN lanes
  replace the module's content and keep the export name and its props, so the seeds are never
  edited again in this wave.
- **Required tests:** registry completeness both directions; manifest equality; guard sweep;
  `npm --prefix web test -- --run`.

### Stage B — `W51-AUTH-01` ∥ `W51-ADMIN-USERS` ∥ `W51-ADMIN-REQUESTS` (executor; disjoint)
- **Depends on:** `W51-ROUTES-01` (all three).
- **AUTH allowed paths:** `web/src/app/login/**`, `web/src/app/register/**`,
  `web/src/app/account/**`, `web/src/_pages/sign-in/**`, `web/src/_pages/register/**`,
  `web/src/_pages/account/**`, `web/src/features/sign-in/**`, `web/src/features/register/**`,
  `web/src/features/change-password/**`, `web/src/features/edit-profile/**`,
  `web/tests/unit/screens/{sign-in,register,account}*.test.ts`, `web/tests/unit/session/**`,
  `docs/program/W51-AUTH-01.md`. Mutations: an unknown refusal value is a typed fault, not a
  blank; the password mismatch is caught before the request; the e-mail field is disabled once
  the profile is complete; a 256-character reason wraps at 780 px; a forged `?notice=` shows
  the status sentence and no reason.
- **ADMIN-USERS allowed paths:** `web/src/app/admin/users/**`, `web/src/_pages/admin-users/**`,
  `web/src/widgets/user-list/**`, `web/src/widgets/user-card/**`,
  `web/src/features/manage-user/**`, `web/src/entities/user/**`,
  `web/src/_pages/admin-user/**`, `web/tests/unit/screens/admin-users*.test.ts`,
  `web/tests/unit/widgets/user-*.test.ts`, `docs/program/W51-ADMIN-USERS.md`. Mutations: the self-archive and last-admin refusals from the
  API render as typed states; purge is not offered for an active account; a maximum-length name
  (60 characters) in the list does not widen the table at 780 px; after archive, the list is
  refetched (invalidation guard red if removed).
- **ADMIN-REQUESTS allowed paths:** `web/src/app/admin/registrations/**`,
  `web/src/_pages/admin-registrations/**`, `web/src/widgets/registration-queue/**`,
  `web/src/features/decide-registration/**`, `web/src/entities/registration-request/**`,
  `web/tests/unit/screens/admin-registrations*.test.ts`,
  `web/tests/unit/widgets/registration-*.test.ts`, `docs/program/W51-ADMIN-REQUESTS.md`.
  Mutations: approve with zero roles is refused client-side and the server's refusal is a typed
  state; a reason of 257 characters is refused before the request; after approve, the queue and
  the home tile key are invalidated (guard red if removed).

### `W51-E2E-01` — Stage C (executor)
- **Depends on:** the three Stage-B lanes merged.
- **Allowed paths:** `tests/e2e/pc01/**`, `tests/e2e/test_pc01_journey_conformance.py`,
  `scripts/manual-alpha-check.sh`, `docs/program/ALPHA-MANUAL-01.md`,
  `docs/manual-tests/ALPHA_PUBLIC_ACCEPTANCE.md` (new steps only; **the prose guard scans this
  directory** for migration-head and surface claims — state them by command, never by number),
  `docs/program/W51-E2E-01.md`.
- **Deliverables:** journey: register → admin approves with `expert` → the new account signs in
  (its profile came from the request), records a verdict whose author label is "Фамилия И. О."
  → admin removes `expert` → the account's next BFF call answers the 401 envelope, the session
  row is gone and the screen shows the signed-out state with the sign-in link → it signs in again
  → the next mutation is `permission_denied` → archive → sign-in is the generic refusal → purge is
  refused (`account_referenced`, it authored a decision). Refusal cases: pending/rejected status with and
  without a notice, self-archive, last admin, zero roles. Manual steps A13–A20 added to the pack
  with expected sentences.
- **Required tests:** the journey against a built stand with `provider_mode=recorded`; the
  conformance test; `shellcheck scripts/manual-alpha-check.sh`.

### `W51-QA-01`, `W51-JUDGE-X`, `W51-JUDGE-Y` (executor, fresh contexts), `W51-FIX` (executor), `W51-INT-CLOSE` (integrator)
- QA: standard form, files under `web/tests/unit/qa_w51/**`: every screen with every role set,
  profile state and the guest; every API refusal of W49 §3.2–§3.3 rendered.
- X (built stand, black-box first): enumeration through registration; flooding to the cap from
  the form and from `/api/v1/` directly; open redirect via `next` and `from`; the rejected
  applicant's reason cannot be read without the pair or with a forged notice; role removal takes
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
3. Stage B: `W51-AUTH-01` ∥ `W51-ADMIN-USERS` ∥ `W51-ADMIN-REQUESTS` from the Stage-A SHA; merge
   in that order.
4. Stage C: `W51-E2E-01`.
5. `W51-QA-01`; judges X and Y; cross-examination; `W51-FIX`.
6. `W51-INT-CLOSE`.

## 6. Ownership matrix

| Hotspot / path family | Owner | Role | Parallel writer |
| --- | --- | --- | --- |
| `contracts/**`, migrations, backend, root locks, `globals.css`, `_app/**`, `shared/ui/**`, `screen-lock.ts` | frozen | — | none |
| `screen-registry.ts`, `route-screens.ts`, `screen-guard.guard.test.ts`, `manifest.json`, the five placeholder `_pages` modules | `W51-ROUTES-01` (Stage A) | executor | none |
| `shared/api/query-keys.ts` | frozen (namespaces entered in W50) | — | none |
| `app/{login,register,account}/**`, `_pages/{sign-in,register,account}/**`, `features/{sign-in,register,change-password,edit-profile}/**` | `W51-AUTH-01` | executor | the two ADMIN lanes |
| `app/admin/users/**`, `_pages/{admin-users,admin-user}/**`, `widgets/{user-list,user-card}/**`, `features/manage-user/**`, `entities/user/**` | `W51-ADMIN-USERS` | executor | AUTH, ADMIN-REQUESTS |
| `app/admin/registrations/**`, `_pages/admin-registrations/**`, `widgets/registration-queue/**`, `features/decide-registration/**`, `entities/registration-request/**` | `W51-ADMIN-REQUESTS` | executor | AUTH, ADMIN-USERS |
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
