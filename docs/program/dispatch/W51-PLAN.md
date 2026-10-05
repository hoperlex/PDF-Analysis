# Wave 51 — screens: sign-in, registration, account; administration of users and requests; identity in the acceptance pack

**Status:** planned; dispatchable after `W50-INT-CLOSE` and `W51-FREEZE-01`.
**Controlling rulings:** `R-55`, `R-56`, `R-59`, `R-60`, `R-61` (provisional numbers).
**Exit:** the screens on `origin/dev` with literal `GATE OK`; the PC-01 journey and the manual
acceptance pack cover registration, approval, roles and archive. No contract change.

## 1. Objective

A person can request an account, learn its status, sign in with an e-mail, complete and edit a
profile, and change a password. An administrator can see the queue, approve with roles or reject
with a reason, list and edit users, archive and restore them, and reset a password. Every refusal
the API gives is shown as a typed state in Russian; no rule is computed in the browser.

## 2. Entry conditions

| Condition | Evidence |
| --- | --- |
| `W50-INT-CLOSE` done: registry, `requireScreen`, primitives, `entities/account` | `origin/dev` |
| W49 operations in the generated client | `operations.gen.ts` names §3.4 of `W49-PLAN.md` |
| alpha acceptance pack baseline | `scripts/manual-alpha-check.sh`, `docs/program/ALPHA-MANUAL-01.md` at the base |

## 3. Screens

| Address | Access / roles | Group | Lane |
| --- | --- | --- | --- |
| `/login` (reworked) | public; a session redirects home | hidden | AUTH |
| `/register` | public | hidden | AUTH |
| `/register/submitted` | public | hidden | AUTH |
| `/account` | open-to-default-credential (profile completion) | account | AUTH |
| `/account/password` (existing) | open-to-default-credential | account | AUTH |
| `/admin/users` | session, admin | admin | ADMIN |
| `/admin/users/[user_uid]` | session, admin | admin | ADMIN |
| `/admin/registrations` | session, admin | admin | ADMIN |

Behaviour:

- **Sign-in:** e-mail and password; a `next` parameter the server validated; refusals
  `credentials`, `validation`, `unconfigured`, `upstream`, `pending`, `rejected` (with the
  reason) each a sentence; one generic sentence for a wrong pair.
- **Registration:** surname, name, patronymic (optional), e-mail, password twice; the R-48 policy
  explained before submission; `conflict_reason` rendered as three different sentences;
  `/register/submitted` says what happens next (an administrator decides; the status is shown at
  sign-in) — no mail is promised (`R-56`).
- **Account:** profile view/edit (names; e-mail only while the profile is incomplete, `R-59`),
  the avatar preview, roles read-only, link to the password screen. The seeded account lands here
  after its forced password change until it has saved names and an e-mail.
- **Users:** list with filters (role, archived), the card with names/roles/state, actions edit,
  archive (with the API's refusals for self and last admin shown verbatim as typed states),
  restore, purge (offered only for an archived account; the API's `account_referenced` refusal
  is a typed state; a confirmation names the e-mail and says it is irreversible), reset password
  (temporary password entered twice, shown nowhere afterwards).
- **Requests:** queue with `pending_total`, approve with a role picker (at least one), reject with
  a reason; decided requests visible read-only with filter.

Query invalidation after every mutation follows the pattern `dashboard-invalidation.guard.test.ts`
now enforces (behaviour, not comments).

## 4. Tasks

### `W51-FREEZE-01`
Base SHA; task files; ports; baseline counts.

### `W51-ROUTES-01` — Stage A, alone
- **Allowed paths:** `web/src/shared/config/routes.ts`, the eight `page.tsx` of §3 as
  `RoutePlaceholder` pages with `requireScreen`, `web/src/app/admin/loading.tsx`,
  `web/tests/unit/screens/route-screens.ts` (seeds), `web/tests/guards/screen-guard.guard.test.ts`
  (open-screen register), `docs/program/W51-ROUTES-01.md`.
- **Deliverables:** every W51 address registered and guarded before any content exists, so AUTH
  and ADMIN never touch the registry or the seeds.
- **Required tests:** registry completeness both directions; guard sweep; `npm --prefix web test
  -- --run`.

### `W51-AUTH-01` — Stage B
- **Allowed paths:** `web/src/app/login/**`, `web/src/app/register/**`, `web/src/app/account/**`,
  `web/src/_pages/sign-in/**`, `web/src/_pages/register/**`, `web/src/_pages/account/**`,
  `web/src/features/sign-in/**`, `web/src/features/register/**`,
  `web/src/features/change-password/**`, `web/src/features/edit-profile/**`,
  `web/tests/unit/screens/{sign-in,register,account}*.test.ts`, `web/tests/unit/session/**`,
  `docs/program/W51-AUTH-01.md`.
- **Required mutations:** an unknown refusal value is a typed fault, not a blank; the password
  mismatch is caught before the request; the e-mail field is disabled once the profile is
  complete; `rejection_reason` of 500 characters wraps at 780 px.

### `W51-ADMIN-01` — Stage B, parallel with AUTH
- **Allowed paths:** `web/src/app/admin/**`, `web/src/_pages/admin/**`,
  `web/src/widgets/user-list/**`, `web/src/widgets/user-card/**`,
  `web/src/widgets/registration-queue/**`, `web/src/features/manage-user/**`,
  `web/src/features/decide-registration/**`, `web/src/entities/user/**`,
  `web/src/entities/registration-request/**`, `web/src/shared/api/query-keys.ts`,
  `web/tests/unit/screens/admin-*.test.ts`, `web/tests/unit/widgets/{user,registration}*.test.ts`,
  `web/tests/guards/query-key-shape.guard.test.ts` (new keys), `docs/program/W51-ADMIN-01.md`.
- **Required mutations:** approve with zero roles is refused client-side and server-side; the
  self-archive refusal from the API renders as a typed state; a 200-character surname in the
  list does not widen the table at 780 px; after approve, the queue and the users list are
  refetched (invalidation guard red if removed).

### `W51-E2E-01` — Stage C, after AUTH and ADMIN merge
- **Allowed paths:** `tests/e2e/pc01/**`, `tests/e2e/test_pc01_journey_conformance.py`,
  `scripts/manual-alpha-check.sh`, `docs/program/ALPHA-MANUAL-01.md`,
  `docs/program/ALPHA_PUBLIC_ACCEPTANCE.md`, `docs/manual-tests/**` (new steps only; the prose
  guard scans this directory for migration-head and surface claims — state them by command, not
  by number), `docs/program/W51-E2E-01.md`.
- **Deliverables:** journey: register → admin approves with `expert` → new account signs in,
  completes nothing (profile came from the request), records a verdict whose author label is
  "Фамилия И. О." → admin removes `expert` → the account's next request is `permission_denied`
  → archive → sign-in is the generic refusal. Refusal cases: pending/rejected sign-in,
  self-archive, last admin. Manual steps A13–A20 added to the pack with expected sentences.
- **Required tests:** the journey against a built stand with `provider_mode=recorded`; the
  conformance test; `shellcheck scripts/manual-alpha-check.sh`.

### `W51-QA-01`, `W51-JUDGE-X`, `W51-JUDGE-Y`, `W51-FIX`, `W51-INT-CLOSE`
- QA: new files only under `web/tests/unit/qa_w52/**`: every screen with every role set and the
  guest; every API refusal of W49 §3.2–§3.3 rendered.
- X (built stand, black-box first): enumeration through registration; flooding to the cap from the
  form; open redirect via `next`; the rejected applicant's reason cannot be read without the pair;
  role removal takes effect on the next request; keyboard-only completion of registration and
  approval; 780 × 900 with 200-character names and a 500-character reason; console clean.
- Y: no business rule in a component (`rg -n 'roles.length|isLastAdmin|=== me' web/src` finds only
  presentation); FSD boundaries; typed states for every closed vocabulary (`role`, `status`,
  `conflict_reason`); invalidation after each mutation; registry and seeds complete; lock bytes
  unchanged.
- INT-CLOSE: standard; `CURRENT_STATE.md`; `DEBT_REGISTER.md`; `origin/dev`; stop.

## 5. Integration order

1. `W51-FREEZE-01`.
2. Stage A: `W51-ROUTES-01`.
3. Stage B: `W51-AUTH-01` ∥ `W51-ADMIN-01` from the Stage-A SHA.
4. Merge AUTH then ADMIN; Stage C: `W51-E2E-01`.
5. `W51-QA-01`; judges X and Y; cross-examination; `W51-FIX`.
6. `W51-INT-CLOSE`.

## 6. Ownership matrix

| Hotspot / path family | Owner | Parallel writer |
| --- | --- | --- |
| `contracts/**`, migrations, backend, root locks, `globals.css`, `_app/**`, `shared/ui/**` | frozen | none |
| `shared/config/routes.ts`, `route-screens.ts`, `screen-guard.guard.test.ts` | `W51-ROUTES-01` (Stage A) | none |
| `app/{login,register,account}/**`, `_pages/{sign-in,register,account}/**`, `features/{sign-in,register,change-password,edit-profile}/**` | `W51-AUTH-01` | ADMIN |
| `app/admin/**`, `_pages/admin/**`, `widgets/{user-list,user-card,registration-queue}/**`, `features/{manage-user,decide-registration}/**`, `entities/{user,registration-request}/**`, `shared/api/query-keys.ts` | `W51-ADMIN-01` | AUTH |
| `tests/e2e/**`, `scripts/manual-alpha-check.sh`, acceptance docs | `W51-E2E-01` (Stage C) | none |
| `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `origin/dev` | `W51-INT-CLOSE` | none |

## 7. Stop conditions

`W48-PLAN.md` §14, plus: a screen needs an operation or a detail key W49 did not seal; a rule
has to be computed in the browser because the API does not refuse it; a global style or a
primitive is missing and would have to be added outside W50's ownership (then a bounded
`W51-SHELL-FIX` grant, not a silent edit); the journey needs a live provider (it must not).

## 8. Non-goals

Mail; captcha; avatar upload; password reset by link; bulk user import; audit log of
administrator actions beyond what `decided_by`/`archived_by` already record; any API change.

## 9. After W51

Candidates for the next planning round, registered rather than scheduled: SMTP and
notifications; avatar upload; a deployed-revision endpoint; the normative corpus plane withdrawn
with W49; retiring `display_name`; renaming `is_default_credential`.
