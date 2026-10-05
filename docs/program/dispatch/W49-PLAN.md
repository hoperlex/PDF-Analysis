# Wave 49 — identity: e-mail accounts, full names, a role set, registration requests, user management

**Status:** planned; dispatchable after `W48-CLOSE` exits and `W49-FREEZE-01` records an exact base.
**Controlling rulings:** `R-55`, `R-56`, `R-57`, `R-59`, `R-60`, `R-61` (provisional numbers,
`IDENTITY-WAVES.md` §4). Nothing in this wave is dispatchable before they are recorded.
**Exit:** the resealed contract, migration, backend and BFF session on `origin/dev` with literal
`GATE OK`. No screens beyond the sign-in refusal sentences; screens are W50/W51.

## 1. Objective

The alpha gets accounts a person can hold: e-mail as the sign-in identifier, a full name shown
where a login used to be, roles as a set `{expert, admin}` enforced on the server by a written
register, registration requests an administrator approves or rejects with a reason, and
administrator management of accounts (edit, archive, restore, reset password). Everything is
reachable through the existing BFF; the browser still never sees a credential.

## 2. Entry conditions

| Condition | Evidence |
| --- | --- |
| `W48-INT-CLOSE` done | `origin/dev` names the W48 candidate; `CURRENT_STATE.md` says so |
| migration head is `0014_durable_analysis_effects` on a fresh database | `PYTHONPATH=src .venv/bin/alembic -c db/migrations/alembic.ini heads` |
| rulings `R-55`…`R-61` recorded | `grep -n 'R-55' docs/program/OWNER_RULINGS_2026-09-17.md` |
| contract set measured at the base | API 17 / 20 / 61 at the recorded SHA-256; error catalog 22; identifiers 27 |
| no other writer on `contracts/**`, migrations, `bootstrap/**`, `web/FRONTEND_LOCK.json` | branch inventory in the freeze report |

## 3. Design decisions bound by this plan

Every decision below was taken by the owner's polls of 2026-10-05 (`IDENTITY-WAVES.md` §3);
the ruling numbers are provisional until `W48-RULE-01`/`W49-FREEZE-01` record them.

### 3.1 Account

- `app_user.login` **is** the sign-in identifier and holds the normalised e-mail (trimmed,
  zero-width characters removed, lower-cased). Its CHECK widens from `LOGIN_PATTERN` to
  "an e-mail shape, or the seed constant `admin` from migration `0006`". `R-59`: the seeded
  account completes its profile at its first sign-in after the upgrade and chooses its e-mail
  there; `login` is rewritten in that one UPDATE together with the names.
- Full name: `last_name`, `first_name`, `middle_name` (nullable), letters/hyphen/apostrophe/space,
  no mixed Cyrillic/Latin inside one word (the `technic` rule). `display_label` becomes
  "Фамилия И. О." when names exist, else `display_name`, else `login`. The `display_name` column
  stays for this wave (it is `author_label` on decisions, `R-37`); its retirement is registered.
- `archived_at`, `archived_by`: archive is the normal removal (`R-61`). `uq_app_user_login`
  becomes a partial unique index `WHERE archived_at IS NULL`; sign-in and `credential_standing`
  refuse an archived account with the generic refusal.
- **Purge** (`R-61`, P-12): an archived account that nothing references may be deleted
  irreversibly. "References" is a **written register** in `access` of the columns that may name
  a `user_uid`: `app_user.archived_by`, `app_user_role.granted_by`,
  `registration_request.decided_by`, `registration_request.created_user_uid`, and
  `expert_decision_event.author_user_uid` — a **new nullable column** this wave adds, written
  from the subject on every new decision event and NULL for history, because today the event
  stores only `author_label`, a display string (migration `0002`, `D-78`/`R-37`) that cannot
  identify an account (`AGENTS.md` §4). Every new column is a real foreign key to
  `app_user(user_uid)` with `ON DELETE RESTRICT`, so the database refuses what the register
  misses; a test enumerates the schema's foreign keys to `app_user` and asserts equality with
  the register. Purge of a referenced or non-archived account answers `conflict` with
  `conflict_reason: account_referenced` / `state_transition_not_allowed` respectively.
- `profile_completed_at`: NULL means the account must complete names/e-mail before it reaches
  anything but `getMe`, `updateMyProfile`, `changePassword`.
- `is_default_credential` keeps its wire name and widens its meaning to "must change password":
  seeded, or reset by an administrator. Registered as a naming debt, not renamed now.

### 3.2 Roles

- Table `app_user_role (user_uid, role, granted_at, granted_by)`, `role IN ('expert','admin')`,
  primary key `(user_uid, role)`. A set, per P-4.
- Backfill at upgrade: every existing account receives `expert`; the seed `admin` also receives
  `admin`.
- Enforcement: a register `OPERATION_ROLES: Mapping[operationId, frozenset[role]]` in
  `src/auditmanager/api/security.py`, every operation named, no defaults. Product mutations
  (`createProject`, uploads, `startRun`, verdicts, comments, export) require `expert`; account
  management requires `admin`; `getMe`, `updateMyProfile`, `changePassword` require an active
  account only. Reads of product data (`R-60`): any active account may read.
- Refusal: `permission_denied` with `required_capability` `role:expert` or `role:admin`.
- Any role change bumps `token_epoch` so every credential and BFF session of that account dies.
- Invariants, enforced in `auditmanager.access` and tested without the router: an account cannot
  archive or demote itself; the last active account holding `admin` cannot be archived or lose
  `admin`.

### 3.3 Registration requests

- Table `registration_request (request_id 'reg_<ULID>', login, last_name, first_name,
  middle_name, password_algorithm/iterations/salt/hash, status IN ('pending','approved',
  'rejected'), submitted_at, decided_at, decided_by, rejection_reason, created_user_uid)`, plus
  the three sign-in-throttle columns of `app_user`. One `pending` row per `login` (partial unique).
  Decided rows are immutable (an `am_guard_*` trigger in the programme's existing style).
- Submit is unauthenticated (`UNAUTHENTICATED_OPERATIONS` grows to `{issueToken,
  submitRegistration}`); the password is validated by the R-48 policy at submission and stored
  hashed; approval creates the account **in the same transaction** under `FOR UPDATE`, with the
  roles the administrator chose (at least one). Two concurrent approvals: one wins, the other
  answers `state_transition_not_allowed`.
- A request for a login held by an active account, or already pending, answers `conflict`.
  Queue cap: more than 100 pending requests answers `conflict` as well. The reasons are
  distinguished by a new safe detail key `conflict_reason ∈ {login_taken, request_pending,
  queue_full, account_referenced}` — a catalog reseal inside `W49-CONTRACT-01`. Revealing that a
  login is taken is an accepted limitation, registered.
- Status at sign-in (`R-56`): `issueToken` with a pair that matches no active account but
  matches a request's login and password answers `permission_denied` with `required_capability`
  `registration_approval` (pending) or `registration_rejected` plus the safe detail key
  `rejection_reason`. The request's throttle columns count these attempts.
- No mail, no verification, no captcha (`R-56`; `IDENTITY-WAVES.md` §9).

### 3.4 Operations added (names are the contract task's to confirm)

| operationId | Method and path | Roles | Registers |
| --- | --- | --- | --- |
| `getMe` | `GET /me` | active account | default-credential reachable |
| `updateMyProfile` | `PATCH /me` | active account | default-credential reachable; `login` writable only while `profile_completed_at IS NULL` |
| `submitRegistration` | `POST /registrations` | none | unauthenticated |
| `listRegistrations` | `GET /registrations?status=` | admin | response carries `pending_total` for the badge |
| `approveRegistration` | `POST /registrations/{request_id}/approve` | admin | body: roles; idempotency key as other mutations |
| `rejectRegistration` | `POST /registrations/{request_id}/reject` | admin | body: reason, 1–500 chars |
| `listUsers` | `GET /users?include_archived=` | admin | |
| `getUser` | `GET /users/{user_uid}` | admin | |
| `updateUser` | `PATCH /users/{user_uid}` | admin | names, roles; invariants of §3.2 |
| `archiveUser` | `POST /users/{user_uid}/archive` | admin | not self; not the last admin |
| `restoreUser` | `POST /users/{user_uid}/restore` | admin | `conflict` if the login is now held by an active account |
| `resetUserPassword` | `POST /users/{user_uid}/password` | admin | temporary password under the R-48 policy; sets must-change; bumps epoch; not self |
| `purgeUser` | `DELETE /users/{user_uid}` | admin | archived and unreferenced only (§3.1); not self; irreversible |

`issueToken` and `changePassword` keep their shapes; `issueToken` gains the refusal semantics of
§3.3. Identifiers `usr` and `reg` enter `contracts/domain/v1/identifiers.json` because both now
cross the wire. Error catalog stays at 22 codes; two safe detail keys are added
(`conflict_reason`, `rejection_reason`). `DecisionEvent` on the wire is unchanged: the new
`author_user_uid` column is internal. The surface triple after the reseal is **measured by
`W49-CONTRACT-01`**, never quoted from this plan.

### 3.5 BFF session

- After the exchange the BFF calls `getMe` with the minted credential and stores a subject
  `{login, displayLabel, initials, roles, isDefaultCredential, profileComplete, openedAt,
  expiresAt}`; `credentialOf` stays the forwarder's alone.
- The register file format gets a version field; rows of the old shape are dropped at start,
  which signs everyone in once (`R-47`/`R-51` durability semantics unchanged).
- A reserved `POST /bff/v1/registration` forwards `submitRegistration` **without** a credential;
  it is the only credential-less forward and is named in the reserved-segment list and its test.
- The sign-in refusal set in `web/src/features/sign-in/model/exchange.ts` gains `pending` and
  `rejected`; the sign-in screen renders the two sentences (Russian). The full screens are W51.

## 4. Tasks

### `W49-FREEZE-01`
Records base SHA, contract set and migration head; writes task files from
`TASK_TEMPLATE.md` with exact `allowed_paths`; replaces every provisional ruling number with the
recorded one; takes ports in `PORT_REGISTRY.md`; owns the initial `origin/dev` bookkeeping only.
Checks: full `make gate` at the base; `test_doc_prose_facts.py`; `git diff --check`.

### `W49-CONTRACT-01` — the single contract slot
- **Allowed paths:** `contracts/api/v1/openapi.json`, `contracts/api/v1/README.md`,
  `contracts/domain/v1/identifiers.json`, `contracts/domain/v1/error-codes.json`,
  `contracts/domain/v1/README.md`, `web/openapi/openapi.json`, `web/src/shared/api/generated/**`
  (via `npm --prefix web run api:generate`), `web/FRONTEND_LOCK.json`,
  `tests/contract/api_v1/**`, `tests/contract/domain_p02/**`, `web/tests/contract/**`,
  `docs/program/W49-CONTRACT-01.md`.
- **Deliverables:** §3.4 operations and schemas; `info.description` paragraph superseding the
  "no role vocabulary may be added" sentence under `R-55`; detail keys; identifiers; regenerated
  client; measured triple and SHA-256 in the report; compatibility statement (every existing
  operation unchanged on the wire).
- **Required tests:** `.venv/bin/python -m pytest tests/contract -q`;
  `npm --prefix web run api:verify`; `npm --prefix web test -- --run tests/contract`.
- **Stop:** a 23rd error code, or a change to an existing operation's shape.

### `W49-ACCESS-01` — domain, repository, migration
- **Allowed paths:** `src/auditmanager/access/**`, `db/migrations/versions/<0015>*.py`,
  `tests/integration/access/**`, `tests/integration/db/test_schema_shape.py`,
  `tests/integration/db/test_migration_lifecycle.py`, a new
  `tests/integration/db/test_accounts_migration.py`, `docs/program/W49-ACCESS-01.md`.
- **Deliverables:** §3.1–§3.3 model, normalisation and name rules in `access/models.py`, ports
  in `access/ports.py`, repository methods (profile, roles, registration lifecycle, archive,
  restore, purge with the reference register, admin reset), invariants, migration `0015` with
  upgrade/downgrade (downgrade refuses while `registration_request` or `app_user_role` hold
  rows, in the `0013`/`0014` style; it also adds `expert_decision_event.author_user_uid` with its
  foreign key — the column, not its writer), backfill of §3.2, CLI
  `python -m auditmanager.access.grant` to grant/revoke a role for recovery (the way out if the
  last admin is locked), `access/README.md`.
- **Required tests:** fresh upgrade to `0015` and downgrade on an empty tree; upgrade from a
  `0014` database holding the seeded `admin` with a changed password; every invariant tested at
  repository level; `am_guard` trigger refuses an UPDATE of a decided request; partial unique
  index proven by two rows; `make gate`.

### `W49-DECISIONS-01` — the decision event names its author's account
- **Allowed paths:** `src/auditmanager/decisions/**`, `tests/integration/decisions/**`,
  `docs/program/W49-DECISIONS-01.md`.
- **Deliverables:** `ledger` and `journal` take and persist `author_user_uid` beside
  `author_label`; `author_label` keeps its `R-37` meaning; history rows stay NULL and are read as
  "author account unknown", never as a fault. The router wiring is `W49-API-01`'s.
- **Required tests:** the column is written on every new event; a NULL history row is listed
  without error; `make gate`.
- **Sequence:** after `W49-ACCESS-01` (the column exists), before `W49-API-01`.

### `W49-API-01` — routers, security register, composition
- **Allowed paths:** `src/auditmanager/api/**`, `src/auditmanager/bootstrap/adapters.py`,
  `src/auditmanager/bootstrap/composition.py` (this wave's composition-root owner),
  `tests/integration/api/**`, `tests/integration/auth/**`, `docs/program/W49-API-01.md`.
- **Deliverables:** routers `me.py`, `registrations.py`, `users.py`; the decisions router passes
  the subject's `user_uid` to the ledger; `OPERATION_ROLES` register;
  `UNAUTHENTICATED_OPERATIONS` and `OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES` extended exactly as
  §3.4; the subject gains roles read from the row on every request; sweep tests: for each
  operation × role set in `{∅, {expert}, {admin}, {expert, admin}}` the served application's
  answer equals the register; the open set and the default-credential set equal theirs.
- **Required tests:** `tests/integration/api/test_authorization.py` extended; new
  `test_role_register.py`, `test_registration_flow.py`, `test_user_management.py`;
  `tests/contract/api_v1/test_openapi_conformance.py`; `make gate`.
- **Non-goals:** no business rule in a router; refusals come from `access`.

### `W49-BFF-01` — session subject, registration forward, refusal sentences
- **Allowed paths:** `web/src/app/bff/**`, `web/src/shared/api/credentialed-forward.ts`,
  `web/src/shared/config/session-store.ts`, `web/src/features/sign-in/**`,
  `web/src/_pages/sign-in/**`, `web/scripts/reserved-forwarder.mjs`, `web/tests/unit/session/**`,
  `web/tests/guards/reserved-scripts.guard.test.ts`,
  `web/tests/guards/session-durability.guard.test.ts`,
  `web/tests/guards/server-credential.guard.test.ts`, `docs/program/W49-BFF-01.md`.
- **Deliverables:** §3.5. `layout.tsx` and the frame are untouched (W50).
- **Required tests:** `npm --prefix web test -- --run`; lint; typecheck; mutation: a forward of
  `submitRegistration` through the catch-all must be refused; a session row of the old format
  must be dropped, not read.

### `W49-QA-01` — independent verification
- **Allowed paths:** new files only under `tests/integration/api/qa_w50/**`,
  `tests/integration/access/qa_w50/**`, `docs/program/W49-QA-01.md`.
- **Brief:** written without reading the lane reports: approve race; archive-self; last-admin
  removal through `updateUser` and `archiveUser`; token after role removal; restore collision;
  queue cap at 100 and 101; registration with a taken login; sign-in as pending/rejected
  applicant and the throttle on those attempts; archived account sign-in equals the generic
  refusal byte-for-byte; `is_default_credential` after admin reset forces the change; purge of
  a non-archived account, of an account that authored one decision event, of one that decided a
  request, and of self — each refused; purge of an archived unreferenced account succeeds and the
  login is free.

### `W49-JUDGE-X` (attacker) and `W49-JUDGE-Y` (architecture)
- Subjects: the merged candidate. Allowed paths: `docs/program/reviews/W49-JUDGE-X.md`,
  `docs/program/reviews/W49-JUDGE-Y.md`.
- X: privilege escalation across every operation with every role set; default credential
  against the new operations; enumeration via `conflict_reason`; flooding to the cap; timing
  of the generic refusal; BFF: credential-less forward reaches only `submitRegistration`.
- Y: routers free of SQL/logic (`rg` queries recorded); invariants live in `access`; no new
  ALR-05 import (the W48 guard stays green; AST walk reads 0 / 0); migration fresh and upgrade
  paths; partial unique; the reference register equals the schema's foreign keys to `app_user`;
  four reseal documents in one commit; registers equal sweeps; `AGENTS.md` §4: no dual-write
  (approval is one transaction), no silent fallback, no display-string identity.
- Cross-examination as in `W48-JUDGES.md`.

### `W49-FIX`, `W49-INT-CLOSE`
Standard: one bounded repair slot with explicit grants; integration in the order of §5; full
gate; `CURRENT_STATE.md` live section (contract triple and migration head by measured value);
`DEBT_REGISTER.md` rows (display_name retirement, `is_default_credential` naming,
login-taken disclosure); `PORT_REGISTRY.md` release; fast-forward `origin/dev`; stop.

## 5. Integration order

1. `W49-FREEZE-01`.
2. Stage A: `W49-CONTRACT-01` alone (it owns every contract hotspot).
3. Stage B: `W49-ACCESS-01` ∥ `W49-BFF-01` from the Stage-A SHA.
4. Stage C: `W49-DECISIONS-01` from the ACCESS merge.
5. Stage D: `W49-API-01` from the DECISIONS merge.
6. Stage E: `W49-QA-01` on the merged candidate; judges X and Y in parallel; cross-examination.
7. `W49-FIX` for upheld release-blocking findings only.
8. `W49-INT-CLOSE`.

## 6. Ownership matrix

| Hotspot / path family | Owner | Parallel writer |
| --- | --- | --- |
| `contracts/**`, `web/openapi/**`, generated client, `web/FRONTEND_LOCK.json` | `W49-CONTRACT-01` | none |
| migration `0015`, `src/auditmanager/access/**` | `W49-ACCESS-01` | none |
| `src/auditmanager/decisions/**` | `W49-DECISIONS-01` | none |
| `src/auditmanager/api/**`, `src/auditmanager/bootstrap/**` | `W49-API-01` | none |
| `web/src/app/bff/**`, `features/sign-in/**`, `_pages/sign-in/**`, session tests | `W49-BFF-01` | none |
| `web/src/_app/**`, `web/src/app/layout.tsx`, `globals.css`, `shared/ui/**` | frozen (W50) | none |
| root locks (`uv.lock`, `web/package-lock.json`) | frozen | none |
| `CURRENT_STATE.md`, `DEBT_REGISTER.md`, `origin/dev` | `W49-INT-CLOSE` | none |
| `origin/main`, tags | nobody without a direct owner instruction | none |

## 7. Stop conditions

Those of `W48-PLAN.md` §14, plus: a rule of §3 turns out to need a decision the polls did not
take; a 23rd error code; an existing operation changes shape; the migration cannot upgrade a
`0014` database holding the seeded account; the sweep finds an operation outside every register;
a refusal is computed in a router or a schema validator instead of `access`.

## 8. Non-goals

Screens (W50/W51); mail; verification; captcha; avatar upload; multi-tenancy; retiring
`display_name`; a version endpoint; any change to analysis, runs, findings or decisions beyond
reading the author label as before.
