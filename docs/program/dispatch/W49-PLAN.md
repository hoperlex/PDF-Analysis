# Wave 49 — identity: e-mail accounts, full names, a role set, registration requests, user management

**Status:** planned; dispatchable after `W48-CLOSE` exits and `W49-FREEZE-01` records an exact base.
**Controlling rulings:** `R-55`, `R-56`, `R-57`, `R-59`, `R-60`, `R-61` (provisional numbers,
`IDENTITY-WAVES.md` §4). Nothing in this wave is dispatchable before they are recorded.
**Roles:** lanes, QA, judges and FIX are the executor's; freeze, merges, the final gate and
publication are the integrator's (`IDENTITY-WAVES.md` §8).
**Exit:** the resealed contract, migration, backend, edge throttle and BFF session on `origin/dev`
with literal `GATE OK`. No screens beyond the sign-in refusal sentences; screens are W50/W51.

## 1. Objective

The alpha gets accounts a person can hold: e-mail as the sign-in identifier, a full name shown
where a login used to be, roles as a set `{expert, admin}` enforced on the server by a written
register, registration requests an administrator approves or rejects with a reason, and
administrator management of accounts (edit, archive, restore, purge, reset password).
Everything is reachable through the existing BFF; the browser still never sees a credential.

## 2. Entry conditions

| Condition | Evidence |
| --- | --- |
| `W48-INT-CLOSE` done | `origin/dev` names the W48 candidate; `CURRENT_STATE.md` says so |
| migration head is `0014_durable_analysis_effects` on a fresh database | `PYTHONPATH=src .venv/bin/alembic -c db/migrations/alembic.ini heads` |
| rulings `R-55`…`R-61` recorded | `grep -n 'R-55' docs/program/OWNER_RULINGS_2026-09-17.md` |
| contract set measured at the base | API 17 / 20 / 61 at the recorded SHA-256; error catalog 22; identifiers 27 |
| no other writer on `contracts/**`, migrations, `bootstrap/**`, `web/FRONTEND_LOCK.json` | branch inventory in the freeze report |

## 3. Design decisions bound by this plan

Every decision below was taken by the owner's polls of 2026-10-05 (`IDENTITY-WAVES.md` §3) or
follows from them; where a poll answer had a consequence the poll could not see, the consequence
is stated with its reason.

### 3.1 Account

- `app_user.login` **is** the sign-in identifier and holds the normalised e-mail (trimmed,
  zero-width characters removed, lower-cased; at most 254 characters). The CHECK
  `ck_app_user_login_format` is replaced by: **`login` has an e-mail shape, or
  `profile_completed_at IS NULL`.** No seed constant is hard-coded: every account that exists at
  upgrade is a legacy account until it completes its profile.
- `profile_completed_at`: the backfill leaves it NULL for every existing row. While it is NULL
  the account reaches only the operations in `OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES` (§3.2).
  Completion (`updateMyProfile` with names and, for a legacy login, the e-mail) is **one UPDATE**
  that writes the names, rewrites `login` to the e-mail and sets the timestamp (`R-59`).
- **Operator path, so the stand stays usable between W49 and the W51 screens:**
  `python -m auditmanager.access.profile --login admin --email … --last-name … --first-name …
  [--middle-name …]` completes a profile from the host, replacing `access.name`. It is also
  the recovery path when nobody can sign in to complete a profile.
- Full name: `last_name`, `first_name` (required once complete), `middle_name` (optional); each
  **at most 60 characters**; letters, hyphen, apostrophe, space; no mixed Cyrillic/Latin inside
  one word (the `technic` rule). `display_label` is "Фамилия И. О." when names exist, else
  `display_name`, else `login`. **By construction a decision event is written only by a complete
  profile** (§3.2), so `author_label` (1..128, migration `0002`) always receives the ≤ 67-character
  name form, never a 254-character e-mail.
- `display_name` stays this wave (it is `author_label`'s source today, `R-37`); its retirement is
  registered. `R-55` records that the derived name form takes precedence over `display_name`.
- `archived_at`, `archived_by`: archive is the normal removal (`R-61`). `uq_app_user_login`
  becomes a partial unique index `WHERE archived_at IS NULL`; `standing_of` returns no standing
  for an archived account, so sign-in and every credentialed request answer the generic
  `authentication_required`.
- **Purge** (`R-61`, P-12): an archived account that nothing references may be deleted
  irreversibly. "References" is a **written register** in `access` of the columns that may name a
  `user_uid`, each a real foreign key to `app_user(user_uid)`:
  - `ON DELETE RESTRICT` — `app_user.archived_by`, `app_user_role.granted_by`,
    `registration_request.decided_by`, `expert_decision_event.author_user_uid` (new, §3.1 below);
    an administrator who archived, granted or decided anything, and an expert who authored a
    decision, are therefore unpurgeable — `R-61` says so;
  - `ON DELETE SET NULL` — `registration_request.created_user_uid` (the request that created the
    account is history, not a reference; the immutability trigger permits exactly this nulling);
  - `ON DELETE CASCADE` — `app_user_role.user_uid` (the account's own roles).
  A test enumerates the schema's foreign keys to `app_user` and asserts equality with the
  register, so the database refuses what the register misses. Purge of a non-archived account
  answers `state_transition_not_allowed`; of a referenced one `conflict` with
  `conflict_reason: account_referenced`.
- **`expert_decision_event.author_user_uid`** — a new nullable column with its RESTRICT foreign
  key, written from the subject on every new decision event, NULL for history, no wire change.
  Reason: today the event stores only `author_label`, a display string (`D-78`/`R-37`) that
  cannot identify an account (`AGENTS.md` §4); "no decisions by this account" needs a column.
- `is_default_credential` keeps its wire name and widens its meaning to "must change password":
  seeded, or reset by an administrator. Registered as a naming debt, not renamed now.

### 3.2 Roles and the registers

- Table `app_user_role (user_uid, role, granted_at, granted_by)`, `role IN ('expert','admin')`,
  primary key `(user_uid, role)`. A set, per P-4.
- Backfill at upgrade: every existing account receives `expert`; the row whose `login = 'admin'`
  (the `0006` seed) also receives `admin`. If no such row exists the migration still succeeds and
  the report says so; `python -m auditmanager.access.grant --login … --role admin` is the way in.
- `AccountStanding` (`access/repository.py`, `standing_of`) grows `roles`, `archived` and
  `profile_complete`; it is read on every credentialed request exactly as `token_epoch` is today.
  No role lives in the signed token.
- Three registers in `src/auditmanager/api/security.py`, every operation named, no defaults:
  - `UNAUTHENTICATED_OPERATIONS` = `{issueToken, submitRegistration, readRegistrationStatus}`;
  - `OPERATIONS_A_DEFAULT_CREDENTIAL_REACHES` = `{issueToken, changePassword, getMe}`;
  - `OPERATIONS_AN_INCOMPLETE_PROFILE_REACHES` = `{getMe, updateMyProfile, changePassword}`,
    refusal `permission_denied` with `required_capability: profile_completed`;
  - `OPERATION_ROLES: Mapping[operationId, frozenset[str]]` — **any-of**: the subject holds at
    least one role in the set; the empty set means any active, complete account. Product
    mutations (`createProject`, uploads, `startRun`, verdicts, comments, export) → `{expert}`;
    account and request management → `{admin}`; reads of product data, `getMe`,
    `updateMyProfile`, `changePassword` → `∅` (`R-60`). Refusal `permission_denied` with
    `required_capability` `role:expert` or `role:admin`.
  Order of evaluation on a request: signature and expiry → standing (archived or stale epoch →
  `authentication_required`) → default credential → incomplete profile → roles. Each register has
  a sweep test that compares it with the served application.
- Any role change, archive, restore, purge or administrator reset bumps `token_epoch`, so every
  credential of that account answers `authentication_required` on its next request. The BFF turns
  that 401 into a closed session (§3.5); the account signs in again and only then meets a
  `permission_denied` on what it lost.
- Invariants, enforced in `auditmanager.access` and tested without the router: an account cannot
  archive, purge, demote or reset itself; the last active account holding `admin` cannot be
  archived or lose `admin`; approval grants at least one role.

### 3.3 Registration requests

- Table `registration_request (request_id 'reg_<ULID>', login, last_name, first_name,
  middle_name, password_algorithm/iterations/salt/hash, status IN ('pending','approved',
  'rejected'), submitted_at, decided_at, decided_by, rejection_reason, created_user_uid)` plus
  the three sign-in-throttle columns of `app_user`. One `pending` row per `login` (partial
  unique). The decision UPDATE sets `status`, `decided_at`, `decided_by`, `rejection_reason` or
  `created_user_uid` **and nulls the four password columns**; an `am_guard_*` trigger permits
  exactly that transition once and the later `created_user_uid` nulling by purge, nothing else.
- Submit is unauthenticated; the password is validated by the R-48 policy (plus the names and the
  e-mail local part in the contextual blocklist) at submission and stored hashed until the
  decision. Approval creates the account **in the same transaction** under `FOR UPDATE`, with the
  roles the administrator chose (at least one), `profile_completed_at = now()` (the request
  carried the names). Two concurrent approvals: one wins, the other answers
  `state_transition_not_allowed`.
- A request for a login held by an active account, or already pending, answers `conflict`; more
  than 100 pending requests answers `conflict` too. The reasons are the new safe detail key
  `conflict_reason ∈ {login_taken, request_pending, queue_full, account_referenced}` — an
  enum-like classifier, hence admissible under the catalog's safety rules; a catalog reseal inside
  `W49-CONTRACT-01`. That `login_taken` and `request_pending` disclose a login's existence to
  someone who submits a request is an accepted limitation, registered.
- **Status at sign-in (`R-56`).** `issueToken` is unchanged: a pair that matches no active
  account answers the generic `authentication_required`. A new unauthenticated operation
  `readRegistrationStatus` (`POST /registrations/status`, body `login`, `password`) answers
  `{status: pending|rejected, decided_at?, rejection_reason?}` for a pair that matches a request,
  and the same generic refusal otherwise. The BFF calls it only after a failed exchange (§3.5).
  `rejection_reason` is **1–256 characters** — the catalog's per-value limit (`error-codes.json`,
  `detail_value_rules`) and the reason it is **not** an error detail: a free text typed by an
  administrator is a raw input, which the safety rules exclude from `details`. The owner's
  "1–500" becomes 1–256 as a consequence.
- Constant work: a failed exchange and a status read each perform the same number of PBKDF2
  derivations whether or not a request exists, so timing does not reveal one. The request's
  throttle columns count both kinds of attempts.
- No mail, no verification, no captcha (`R-56`; `IDENTITY-WAVES.md` §9).

### 3.4 Operations added (names are the contract task's to confirm)

| operationId | Method and path | Roles | Registers and rules |
| --- | --- | --- | --- |
| `getMe` | `GET /me` | ∅ | default-credential and incomplete-profile reachable |
| `updateMyProfile` | `PATCH /me` | ∅ | incomplete-profile reachable; `login` writable only while `profile_completed_at IS NULL`; completion is one UPDATE |
| `submitRegistration` | `POST /registrations` | none | unauthenticated; `security: []` in the document |
| `readRegistrationStatus` | `POST /registrations/status` | none | unauthenticated; `security: []`; constant work |
| `listRegistrations` | `GET /registrations?status=` | `{admin}` | response carries `pending_total` for the badge |
| `approveRegistration` | `POST /registrations/{request_id}/approve` | `{admin}` | body: roles (≥ 1); idempotency key as other mutations |
| `rejectRegistration` | `POST /registrations/{request_id}/reject` | `{admin}` | body: reason, 1–256 chars |
| `listUsers` | `GET /users?include_archived=` | `{admin}` | |
| `getUser` | `GET /users/{user_uid}` | `{admin}` | |
| `updateUser` | `PATCH /users/{user_uid}` | `{admin}` | names, roles; invariants of §3.2 |
| `archiveUser` | `POST /users/{user_uid}/archive` | `{admin}` | not self; not the last admin |
| `restoreUser` | `POST /users/{user_uid}/restore` | `{admin}` | `conflict` (`login_taken`) if an active account now holds the login |
| `purgeUser` | `DELETE /users/{user_uid}` | `{admin}` | archived and unreferenced only (§3.1); not self; irreversible |
| `resetUserPassword` | `POST /users/{user_uid}/password` | `{admin}` | temporary password under the R-48 policy; sets must-change; bumps epoch; not self; that the administrator knows the temporary password is registered |

`issueToken` and `changePassword` keep their shapes and semantics. Identifiers `usr` and `reg`
enter `contracts/domain/v1/identifiers.json` because both now cross the wire. Error catalog stays
at 22 codes; one safe detail key is added (`conflict_reason` on `conflict`). `DecisionEvent` on the
wire is unchanged. The surface triple after the reseal is **measured by `W49-CONTRACT-01`**, never
quoted from this plan.

### 3.5 BFF session

- After the exchange the BFF calls `getMe` with the minted credential and stores a subject
  `{login, displayLabel, initials, roles, isDefaultCredential, profileComplete, openedAt,
  expiresAt}`; `credentialOf` stays the forwarder's alone.
- The register file is already versioned (`store.ts`, `version: 1`, unknown versions throw). It
  becomes `version: 2`; a version-1 file is replaced at start, which signs everyone **out** once.
- **Subject refresh:** after a successful forward of `PATCH /me` or of the password change the BFF
  re-reads `getMe` and rewrites the row, so `profileComplete`, `login` and `displayLabel` are
  current without a new sign-in.
- **Upstream 401 with a held credential** (epoch bumped: role change, archive, reset) closes the
  row, clears the cookie and answers the browser with the redirect to `/login?refusal=revoked`
  (a new value in the closed set) instead of forwarding the 401. A mutation test removes the
  closing and must go red.
- A reserved `POST /bff/v1/registration` forwards `submitRegistration` **exactly as the exchange
  is forwarded** (same credential handling, body read here, never returned); it is named in the
  reserved-segment list and its test. On a failed exchange the session handler calls
  `readRegistrationStatus` with the same pair; a `pending`/`rejected` answer is stored as a
  **one-time notice** row in the register (status, reason, five-minute TTL, opaque id) and the
  browser is sent to `/login?refusal=pending|rejected&notice=<id>`; the sign-in page reads and
  deletes the notice. **The reason never travels in a URL**, so it cannot be spoofed by one.
- **Edge throttle for guests:** the BFF applies a per-client token bucket to `POST
  /bff/v1/registration` and `POST /bff/v1/session`, keyed by `X-Forwarded-For` **only when the
  request arrives from the proxy network** (`nginx.conf` sets the header; a request without the
  proxy's address is keyed by its own address). Because `/api/v1/` is public behind nginx, the
  API itself is also covered: `W49-EDGE-01` adds `limit_req` for `POST /api/v1/registrations` and
  `POST /api/v1/registrations/status` in `infra/deploy/proxy/nginx.conf`. The 100-request cap
  stays the last line. Bulk rejection and request retention are registered debts.
- The sign-in refusal set in `web/src/features/sign-in/model/exchange.ts` gains `pending`,
  `rejected`, `revoked`; the sign-in screen renders the sentences (Russian). The full screens are
  W51.

### 3.6 Documentary pins that this wave moves

`tests/contract/api_v1/test_doc_prose_facts.py` pins the surface triple and the migration head as
literals and scans `CURRENT_STATE.md`, `ALPHA_ROADMAP.md` and `docs/manual-tests/*.md` for the
same claims; any lane's `make gate` is red the moment the reseal or `0015` lands unless the pins
move with them. Therefore:

- `W49-CONTRACT-01` moves the triple pin and registers the live triple sentences
  (`CURRENT_STATE.md`, `ALPHA_ROADMAP.md`) in `KNOWN_OUTSTANDING_CLAIMS` with its task id, in the
  reseal commit;
- `W49-ACCESS-01a` moves the head pin (one line of that test file, a named grant) and registers
  the head sentences (`CURRENT_STATE.md`, `docs/manual-tests/PC-01_prototype.md`) the same way;
- `W49-INT-CLOSE` rewrites the sentences and empties the register.

## 4. Tasks

Each task lists `Depends on`. The standard forms of FREEZE, QA, JUDGE, FIX and INT-CLOSE are in
`IDENTITY-WAVES.md` §10 and are not repeated.

### `W49-FREEZE-01` (integrator)
Depends on: `W48-INT-CLOSE`, `W48-RULE-01`, recorded `R-55`…`R-61`. Standard form; also replaces
every provisional ruling number in this plan with the recorded one.

### `W49-CONTRACT-01` — the single contract slot (executor)
- **Depends on:** `W49-FREEZE-01`.
- **Allowed paths:** `contracts/api/v1/openapi.json`, `contracts/api/v1/README.md`,
  `contracts/domain/v1/identifiers.json`, `contracts/domain/v1/error-codes.json`,
  `contracts/domain/v1/README.md`, `web/openapi/openapi.json`, `web/src/shared/api/generated/**`
  (via `npm --prefix web run api:generate`), `web/FRONTEND_LOCK.json`,
  `tests/contract/api_v1/**`, `tests/contract/domain_p02/**`, `web/tests/contract/**`,
  `docs/program/W49-CONTRACT-01.md`.
- **Deliverables:** §3.4 operations and schemas; `info.description` paragraph superseding the
  role-vocabulary sentence under `R-55`; `conflict_reason`; identifiers; regenerated client;
  measured triple and SHA-256 in the report; compatibility statement (every existing operation
  unchanged on the wire); §3.6 pin move and claim registration.
- **Required tests:** `.venv/bin/python -m pytest tests/contract -q`;
  `npm --prefix web run api:verify`; `npm --prefix web test -- --run tests/contract`.
- **Stop:** a 23rd error code; a change to an existing operation's shape; a free-text detail key.

### `W49-ACCESS-01a/b/c` — domain, repository, migration (executor; one owner, three reports)
- **Depends on:** `W49-CONTRACT-01`.
- **Allowed paths (all three):** `src/auditmanager/access/**`,
  `db/migrations/versions/<0015>*.py`, `tests/integration/access/**`,
  `tests/integration/db/test_schema_shape.py`, `tests/integration/db/test_migration_lifecycle.py`,
  `tests/integration/db/test_accounts_migration.py` (new), the head-pin line of
  `tests/contract/api_v1/test_doc_prose_facts.py` and its `KNOWN_OUTSTANDING_CLAIMS`,
  `docs/program/W49-ACCESS-01{a,b,c}.md`.
- **01a — migration `0015` and schema:** every table/column/index/FK/trigger of §3.1–§3.3;
  backfill of §3.2; downgrade refuses while `app_user_role` or `registration_request` hold rows
  (after the backfill that is every real database — **`0015` is forward-only in practice and
  the rollback of W49 is a database restore; the report says so**); the reference register test
  against the schema's foreign keys; CLI `access.profile` and `access.grant`; §3.6 pin move.
- **01b — profile, names, archive, restore, purge:** normalisation and name rules in
  `access/models.py`; `display_label` precedence; `standing_of` with roles/archived/profile;
  ports and repository methods; every invariant of §3.2 at repository level; purge against the
  register.
- **01c — roles and registration lifecycle:** grant/revoke with epoch bump; submit, approve
  (one transaction, `FOR UPDATE`), reject, status read, password-column nulling, queue cap,
  constant-work comparison, throttle columns.
- **Required tests:** fresh upgrade to `0015` and downgrade on an empty tree; upgrade from a
  `0014` database holding the seeded `admin` with a changed password **and** from one holding a
  legacy non-e-mail test login; the trigger refuses a second decision and a password-column
  write after decision; partial unique proven by two rows; `make gate` per report.

### `W49-DECISIONS-01` — the decision event names its author's account (executor)
- **Depends on:** `W49-ACCESS-01a`.
- **Allowed paths:** `src/auditmanager/decisions/**`, `tests/integration/decisions/**`,
  `docs/program/W49-DECISIONS-01.md`.
- **Deliverables:** `ledger` and `journal` take and persist `author_user_uid` beside
  `author_label`; history rows stay NULL and are read as "author account unknown", never as a
  fault. Router wiring is `W49-API-01c`'s.

### `W49-BFF-01` — session subject, notice, throttle, refusal sentences (executor)
- **Depends on:** `W49-CONTRACT-01` (generated client). Parallel with ACCESS.
- **Allowed paths:** `web/src/app/bff/**`, `web/src/shared/api/credentialed-forward.ts`,
  `web/src/shared/config/session-store.ts`, `web/src/features/sign-in/**`,
  `web/src/_pages/sign-in/**`, `web/scripts/reserved-forwarder.mjs`, `web/tests/unit/session/**`,
  `web/tests/guards/reserved-scripts.guard.test.ts`,
  `web/tests/guards/session-durability.guard.test.ts`,
  `web/tests/guards/server-credential.guard.test.ts`, `docs/program/W49-BFF-01.md`.
- **Deliverables:** §3.5 in full. `layout.tsx` and the frame are untouched (W50).
- **Required tests and mutations:** `npm --prefix web test -- --run`; lint; typecheck; a forward
  of `submitRegistration` through the catch-all is refused; a version-1 register file is replaced,
  not read; the notice is deleted on first read and absent after its TTL; removing the
  upstream-401 closing is red; the bucket refuses the N+1th guest request within the window.

### `W49-EDGE-01` — proxy rate limit for the two public registration operations (executor)
- **Depends on:** `W49-CONTRACT-01` (operation paths). Parallel with ACCESS and BFF.
- **Allowed paths:** `infra/deploy/proxy/nginx.conf`, `tests/contract/test_proxy_rate_limits.py`
  (new), `docs/program/W49-EDGE-01.md`.
- **Deliverables:** `limit_req` zones for `POST /api/v1/registrations` and
  `POST /api/v1/registrations/status`; a contract test that reads the configuration and fails
  when either location loses its limit. No other proxy change.

### `W49-API-01a/b/c` — standing, registers, routers, composition (executor; one owner)
- **Depends on:** `W49-ACCESS-01c`, `W49-DECISIONS-01`.
- **Allowed paths (all three):** `src/auditmanager/api/**`, `src/auditmanager/bootstrap/adapters.py`,
  `src/auditmanager/bootstrap/composition.py` (this wave's composition-root owner),
  `tests/integration/api/**`, `tests/integration/auth/**`, `docs/program/W49-API-01{a,b,c}.md`.
- **01a — security:** the three registers and `OPERATION_ROLES`; standing read with roles;
  the evaluation order of §3.2; sweep tests: for every operation × role set in
  `{∅, {expert}, {admin}, {expert, admin}}` × {complete, incomplete} × {default, changed} the
  served application's answer equals the registers.
- **01b — `me` and `users` routers.** **01c — `registrations` router, status read, decisions
  wiring (`author_user_uid`).** Existing suite logins that are not e-mails are created with
  `profile_completed_at IS NULL` or become e-mails; the driver says which.
- **Required tests:** `tests/integration/api/test_authorization.py` extended; new
  `test_role_register.py`, `test_registration_flow.py`, `test_user_management.py`;
  `tests/contract/api_v1/test_openapi_conformance.py`; `make gate` per report.
- **Non-goals:** no business rule in a router; refusals come from `access`.

### `W49-QA-01` (executor, fresh context)
Depends on: `W49-API-01c`, `W49-BFF-01`, `W49-EDGE-01` merged. Standard form, files under
`tests/integration/api/qa_w49/**`, `tests/integration/access/qa_w49/**`,
`web/tests/unit/qa_w49/**`. Brief: approve race; archive/purge/demote/reset of self; last-admin
removal through `updateUser` and `archiveUser`; token after role removal → 401 → BFF closes the
row; restore collision; queue cap at 100 and 101; registration with a taken login; status read as
pending/rejected and the throttle on those attempts; archived account sign-in equals the generic
refusal byte-for-byte; `is_default_credential` after admin reset forces the change; purge of a
non-archived account, of an account that authored a decision event, of one that decided a
request, of one that archived another, and of self — each refused; purge of an archived
unreferenced account succeeds, its request row survives with `created_user_uid` NULL, and the
login is free; the notice is single-use.

### `W49-JUDGE-X` (attacker) and `W49-JUDGE-Y` (architecture) (executor, fresh contexts)
- X: privilege escalation across every operation with every role set and profile state;
  default credential against the new operations; enumeration via `conflict_reason` and via
  timing of the exchange and the status read; flooding to the cap through the BFF, through
  `/api/v1/` directly and from two addresses; a forged `notice` id; a forged `refusal` value;
  BFF: credential-less forward reaches only the two public operations.
- Y: routers free of SQL/logic (`rg` queries recorded); invariants live in `access`; the ALR-05
  guard green (AST walk 0 / 0); migration fresh and both upgrade paths; partial unique; the
  reference register equals the schema's foreign keys to `app_user`; four reseal documents in one
  commit; registers equal sweeps; `AGENTS.md` §4: approval is one transaction, no silent
  fallback, no display-string identity; `KNOWN_OUTSTANDING_CLAIMS` holds exactly the four
  registered sentences.
- Cross-examination as in `W48-JUDGES.md`.

### `W49-FIX` (executor), `W49-INT-CLOSE` (integrator)
Standard forms. INT-CLOSE additionally: rewrites the four registered sentences by measured value
and empties `KNOWN_OUTSTANDING_CLAIMS`; registers the debts of §3 (`display_name` retirement,
`is_default_credential` naming, login disclosure, bulk rejection, decided-request retention,
temporary password known to the administrator, `0015` forward-only).

## 5. Integration order

1. `W49-FREEZE-01`.
2. Stage A: `W49-CONTRACT-01` alone.
3. Stage B: `W49-ACCESS-01a → 01b → 01c` ∥ `W49-BFF-01` ∥ `W49-EDGE-01` from the Stage-A SHA.
4. Stage C: `W49-DECISIONS-01` from the ACCESS merge.
5. Stage D: `W49-API-01a → 01b → 01c` from the DECISIONS merge.
6. Stage E: `W49-QA-01`; judges X and Y in parallel; cross-examination.
7. `W49-FIX` for upheld release-blocking findings only.
8. `W49-INT-CLOSE`.

## 6. Ownership matrix

| Hotspot / path family | Owner | Role | Parallel writer |
| --- | --- | --- | --- |
| `contracts/**`, `web/openapi/**`, generated client, `web/FRONTEND_LOCK.json`, triple pin | `W49-CONTRACT-01` | executor | none |
| migration `0015`, `src/auditmanager/access/**`, head-pin line | `W49-ACCESS-01a/b/c` | executor | BFF, EDGE on disjoint paths |
| `src/auditmanager/decisions/**` | `W49-DECISIONS-01` | executor | none |
| `src/auditmanager/api/**`, `src/auditmanager/bootstrap/**` | `W49-API-01a/b/c` | executor | none |
| `web/src/app/bff/**`, `features/sign-in/**`, `_pages/sign-in/**`, session tests | `W49-BFF-01` | executor | ACCESS, EDGE |
| `infra/deploy/proxy/nginx.conf` | `W49-EDGE-01` | executor | ACCESS, BFF |
| `web/src/_app/**`, `web/src/app/layout.tsx`, `globals.css`, `shared/ui/**` | frozen (W50) | — | none |
| root locks (`uv.lock`, `web/package-lock.json`) | frozen | — | none |
| `CURRENT_STATE.md`, `ALPHA_ROADMAP.md`, `docs/manual-tests/**`, `DEBT_REGISTER.md`, `origin/dev` | `W49-INT-CLOSE` | integrator | none |
| `origin/main`, tags | nobody without a direct owner instruction | integrator | none |

## 7. Stop conditions

Those of `W48-PLAN.md` §14, plus: a rule of §3 turns out to need a decision the polls did not
take; a 23rd error code or a free-text detail key; an existing operation changes shape; the
migration cannot upgrade a `0014` database holding the seeded account; the sweep finds an
operation outside every register; a refusal is computed in a router or a schema validator
instead of `access`; a lane's gate is red on a documentary pin this plan did not assign.

## 8. Non-goals

Screens (W50/W51); mail; verification; captcha; avatar upload; multi-tenancy; retiring
`display_name`; a version endpoint; any change to analysis, runs or findings; any change to
`DecisionEvent` on the wire.
