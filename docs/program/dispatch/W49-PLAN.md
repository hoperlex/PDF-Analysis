# Wave 49 — identity: e-mail accounts, full names, a role set, registration requests, user management

**Status:** planned; dispatchable after `W48-CLOSE` exits and `W49-FREEZE-01` records an exact base.
**Controlling rulings:** `R-55`, `R-56`, `R-57`, `R-59`, `R-60`, `R-61` (provisional numbers,
`IDENTITY-WAVES.md` §4), recorded by `W49-RULE-01` before the freeze. Nothing in this wave is
dispatchable before they are recorded.
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
| rulings `R-55`…`R-61` recorded by `W49-RULE-01` | `grep -n 'R-55' docs/program/OWNER_RULINGS_2026-09-17.md` |
| contract set measured at the base | API 17 / 20 / 61 at the recorded SHA-256; error catalog 22; identifiers 27 |
| `docs/program/CONTRACT_PIN_REGISTRY.md` (from the W48 line) lists every independent pin and its test is green | `.venv/bin/python -m pytest tests/contract/api_v1/test_doc_prose_facts.py -q` |
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
  one word (the `technic` rule). `display_label` is "Фамилия И. О." (at most 66 characters) when
  names exist, else `display_name`, else `login`. **By construction a decision event is written
  only by a complete profile** (§3.2), so `author_label` (1..128, migration `0002`) always
  receives the name form, never a 254-character e-mail.
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
    `registration_request.decided_by`, `expert_decision_event.author_user_uid` (the new column
    below); an administrator who archived, granted or decided anything, and an expert who
    authored a decision, are therefore unpurgeable — `R-61` says so;
  - `ON DELETE SET NULL` — `registration_request.created_user_uid` (the request that created the
    account is history, not a reference; the immutability trigger permits exactly this nulling,
    recognising the cascade by `pg_trigger_depth()` so a manual UPDATE of that column is still
    refused);
  - `ON DELETE CASCADE` — `app_user_role.user_uid` (the account's own roles).
  A test enumerates the schema's foreign keys to `app_user` and asserts equality with the
  register, so the database refuses what the register misses. Purge of a non-archived account
  answers `state_transition_not_allowed` against the `app_user` machine (§3.4); of a referenced
  one `conflict` with `conflict_reason: account_referenced`.
- **`expert_decision_event.author_user_uid`** — a new nullable column with its RESTRICT foreign
  key, written from the subject on every new decision event, NULL for history, no wire change.
  Reason: today the event stores only `author_label`, a display string (`D-78`/`R-37`) that
  cannot identify an account (`AGENTS.md` §4); "no decisions by this account" needs a column.
- `is_default_credential` keeps its wire name and widens its meaning to "must change password":
  seeded, or reset by an administrator. Registered as a naming debt, not renamed now.
- Identifiers before the seal: `tests/contract/domain_p02/test_identifier_catalog.py` asserts
  that the shared identity registry (`shared/identity/ids.py`) equals `identifiers.json`, so
  ACCESS mints `reg_<ULID>` exactly as `usr_<ULID>` is minted today — a local pattern outside the
  shared registry (`access/models.py` explains why `usr` is outside it). `W49-SEAL-01a` adds
  both prefixes to `identifiers.json` and to the registry in the same commit.

### 3.2 Roles and the registers

- Table `app_user_role (user_uid, role, granted_at, granted_by)`, `role IN ('expert','admin')`,
  primary key `(user_uid, role)`. A set, per P-4.
- Backfill at upgrade: every existing account receives `expert`; the row whose `login = 'admin'`
  (the `0006` seed) also receives `admin`. If no such row exists the migration still succeeds and
  the report says so; `python -m auditmanager.access.grant --login … --role admin` is the way in.
- `AccountStanding` and the `AccountStandings` protocol live in `src/auditmanager/api/security.py`
  (lines 365–397 today) and their adapter in `src/auditmanager/bootstrap/adapters.py`
  (`standing_of`); `access` owns the row read. So `W49-ACCESS-01b` adds the repository read of
  roles, archive state and profile completeness, and `W49-SEAL-01` widens `AccountStanding`, the
  protocol and the adapter. The standing is read on every credentialed request exactly as
  `token_epoch` is today. No role lives in the signed token.
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
  `W49-SEAL-01`. That `login_taken` and `request_pending` disclose a login's existence to someone
  who submits a request is an accepted limitation, registered.
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

### 3.4 Operations added (names are the seal task's to confirm)

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
enter `contracts/domain/v1/identifiers.json` because both now cross the wire. Two state machines
enter `contracts/domain/v1/state-machines.json`, because `state_transition_not_allowed` is defined
against that file: `app_user` (`active → archived → active | purged`) and `registration_request`
(`pending → approved | rejected`); their `machine`/`current_state`/`requested_state` details are
then honest. The error catalog grows by **one code, `rate_limited`** (HTTP 429, `retryable:
true`, category `policy`, no detail keys): the edge and the BFF throttles of §3.5 have to answer
with a catalog code — the proxy throttle of §3.5 answers direct callers of `/api/v1/` and the
safety rules forbid inventing a code at the edge, while the catalog has no 429 today. That is the
second reseal of the slot `IDENTITY-WAVES.md` §5 allows; no other code
is added. A code lives in three places at once — `error-codes.json`,
`error-envelope.schema.json` (its `enum` and the per-code `retryable` `allOf`) and the literal
`== 22` in `tests/contract/domain_p02/test_openapi_document.py` — and in the Russian sentence
`web/src/shared/api/catalog-message.ts` carries for every code
(`catalog-message.contract.test.ts` "describes every code the catalog declares"); all four move
in `W49-SEAL-01a`. One safe detail key is added (`conflict_reason` on `conflict`).
`DecisionEvent` on the wire is unchanged. Every sentence in `openapi.json` that denies a role,
subject or capability vocabulary, or rate limiting, is superseded under `R-55` — not a counted
list: the seal's required check is

```sh
rg -n -i -e role -e 'rate limit' contracts/api/v1/openapi.json
```

(two patterns with `-e`; a `\|` inside one pattern is a literal bar to ripgrep and matches
nothing, which is how a check stops being able to fail). At the base it prints six lines in
three places; after the seal the only admissible hits are the `InputManifestEntry.role` field
(its description, `required` entry and property) and the new role-vocabulary sentences the seal
writes, each named in the report. The surface triple after the reseal is **measured by
`W49-SEAL-01`**, never quoted from this plan.

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
  row and clears the cookie, then answers **the 401 envelope**, exactly as `staleSession` does
  today — not a redirect, because the caller is the generated client's `fetch`, which would follow
  a 303 into HTML. The client's existing 401 handling (`shared/api/authorization.ts`) renders the
  signed-out state with the sign-in link; the next server render finds no session and
  `requireScreen` (W50) sends the browser to `/login`. A mutation test removes the row-closing and
  must go red.
- A reserved `POST /bff/v1/registration` forwards `submitRegistration` **exactly as the exchange
  is forwarded** (same credential handling, body read here, never returned). The reservation
  mechanism is the one the route handler already has — the `SESSION_SEGMENT`/`EXCHANGE_SEGMENT`
  constants in `web/src/app/bff/v1/[...path]/route.ts` and their tests in
  `web/tests/unit/session/bff-session.test.ts` — not `web/scripts/reserved-forwarder.mjs`, which
  reserves npm script names. The catch-all refuses the `registrations` first segment to the
  browser exactly as it refuses `auth` today (`not_found` before the session is read), so
  `submitRegistration` and `readRegistrationStatus` are reachable only through the reserved
  handlers and their bucket, never with a session's credential. The registration handler, like
  the session handler, answers the form with `303`: to `/register/submitted` on success, else to
  `/register?refusal=<value>` with the closed set `{validation, login_taken, request_pending,
  queue_full, throttled, upstream}` mapped from the API's `conflict_reason` and status (the W51
  screen renders each value as a sentence; an unknown value is a typed fault).
- On a failed exchange the session handler calls `readRegistrationStatus` with the same pair; a
  `pending`/`rejected` answer is stored as a **one-time notice** row in the register (status,
  reason, five-minute TTL, opaque id) and the browser is sent to
  `/login?refusal=pending|rejected&notice=<id>`; `app/login/page.tsx` reads and deletes the notice
  server-side (it already reads `searchParams` and the register). **The reason never travels in
  a URL**, so it cannot be spoofed by one.
- **Throttle for guests, in the BFF:** a per-client token bucket on `POST /bff/v1/registration`
  and `POST /bff/v1/session`. Both are plain HTML forms answered with `303` to a screen and a
  closed `?refusal=` set (`route.ts` `refuseSignIn`, `exchange.ts`), so the bucket refuses with
  `303` to `/login?refusal=throttled` or `/register?refusal=throttled` — a new value in each
  closed set with its Russian sentence — never with a JSON body a form would render raw. The
  `rate_limited` envelope is what the **proxy** answers to direct callers of `/api/v1/`; the BFF's
  own forwards go to `http://api:8000` inside the compose network (`compose.server.yml`,
  `AUDITMANAGER_API_UPSTREAM`) and never pass the proxy, so a signed-in client never meets it.
  A Next 15
  route handler has no peer address, so the client key is **`X-Real-IP`** — the header both
  proxy configurations set from `$remote_addr` (`nginx.conf:85`, `tls-server.conf:82`) — trusted
  only under `AUDITMANAGER_BEHIND_PROXY=1`, an environment flag `W49-EDGE-01` sets on the `web`
  service in `infra/deploy/compose.server.yml` (the container publishes no port; only the proxy
  reaches it). The flag is read in `web/src/shared/config/` the way `session-store.ts` reads
  `AUDITMANAGER_SESSION_STORE`; it is not a secret and is **not** added to `SERVER_ONLY_VARIABLES`,
  which is pinned literally in three test files. Without the flag every request shares one
  bucket. `X-Forwarded-For` is never the key: its first element is client-supplied; a mutation
  with a forged `X-Forwarded-For` must not escape the bucket.
- **Throttle for guests, at the proxy:** because `/api/v1/` is public behind nginx,
  `W49-EDGE-01` adds `limit_req` for `POST /api/v1/registrations` and
  `POST /api/v1/registrations/status`. Both proxy files are loaded at once when TLS is on
  (`nginx.conf` is mounted as `conf.d/default.conf`; `enable-tls.sh` copies `tls-server.conf`
  beside it), so the `limit_req_zone` and the `map` — `http`-level directives — are declared
  **once, in `nginx.conf`**. The map key is `"$request_method:$uri"`: it yields
  `$binary_remote_addr` for exactly `POST:/api/v1/registrations` and
  `POST:/api/v1/registrations/status` and the empty string (no limit) for everything else, so
  uploads, runs and verdicts are never throttled. `limit_req` plus `limit_req_status 429` plus
  `error_page 429 = @rate_limited` go into **both** `server` bodies inside the existing
  `location /api/v1/` — no new `/api/v1` location, so
  `test_every_api_location_puts_the_prefix_back_on_the_way_out` and
  `test_the_two_server_bodies_do_not_drift` (both in
  `tests/integration/composition/test_proxy_tls_path.py`) stay true; the named location
  `@rate_limited` is the one new block, identical in both files. It returns the `rate_limited`
  envelope as JSON with `$request_id` as `correlation_id` — nginx's own 429 is an HTML page,
  exactly as its 413 is (the comment at `nginx.conf:37-42` is why the body cap is 32m). The
  100-request cap stays the last line. Bulk rejection and request retention are registered debts.
- The sign-in refusal set gains `pending`, `rejected` and `throttled` in both of its mirrors —
  `SIGN_IN_REFUSALS` in `web/src/features/sign-in/model/exchange.ts` and `type Refusal` in
  `web/src/app/bff/v1/[...path]/route.ts` — and the sign-in screen renders the sentences
  (Russian). `exchange.ts` records the `W40-LIMIT` decision **not** to add a `throttled` value,
  because a per-account throttle would tell a stranger that the account exists and is under
  attack; the value added here is **per-client** (the caller's own bucket), says nothing about any
  account, and `W49-BFF-01` rewrites that header comment to say so. The full screens are W51.

### 3.6 Pins that this wave moves, and who moves them

The gate ties contract, routers and documents together, so a reseal that lands alone is red:
`tests/integration/api/test_served_document_and_health_plane.py` asserts the served OpenAPI equals
the frozen document, `test_operation_surface.py` asserts declared operations equal wired routes
(20 today), `tests/contract/api_v1/test_doc_prose_facts.py` pins the surface triple and the
migration head as literals and scans `CURRENT_STATE.md`, `ALPHA_ROADMAP.md` and
`docs/manual-tests/*.md` for the same claims, and — from the W48 line —
`test_contract_pin_registry_is_complete_and_points_to_live_needles` requires every independent
pin to be listed in `docs/program/CONTRACT_PIN_REGISTRY.md` with a live needle. Therefore:

- **the contract, the registers and the routers land in one slot, `W49-SEAL-01`** (as `W46-SEAL`
  did), and that slot owns every surface pin: the triple pin in `test_doc_prose_facts.py`; the
  needle files the registry names, including `tests/e2e/pc01/test_acceptance.py` (one assertion
  on the route count) and the three pins under `tests/integration/composition/**`; the two
  prose counts `test_surface_counts_in_prose.py` reads out of `web/src` — the comment at
  `web/src/app/bff/v1/[...path]/route.ts:22` ("twenty operations across seventeen paths") and
  `web/src/shared/api/authorization.ts:24` ("the twenty operations") — as one-line grants; the
  registry rows for the surface; and the live triple sentences in `CURRENT_STATE.md` and
  `ALPHA_ROADMAP.md` **as the freeze measures them** (the guard reads only the section before
  the first historical heading; at `411c6d0` that is one sentence in each file);
- **`W49-ACCESS-01a` owns the migration head's and the schema's pins:** the head-pin line in
  `test_doc_prose_facts.py`, the registry rows for the head, the schema-inventory digests under
  `tests/integration/db/**`, `P02_TABLES` in `tests/integration/p02_journey/journey.py` (its
  `assert_table_list_is_complete` fails on any table it does not list), and the live head
  sentences in
  `CURRENT_STATE.md` and `docs/manual-tests/PC-01_prototype.md` as the freeze measures them;
- `KNOWN_OUTSTANDING_CLAIMS` stays **empty** (`test_no_known_outstanding_live_claim_is_normalised`
  requires it); nothing is registered as outstanding, the sentences are corrected in the same
  commit that changes the fact;
- `W49-INT-CLOSE` rewrites the live section of `CURRENT_STATE.md` as a whole afterwards.

Exact-sentence grants on integrator-owned documents are the mechanism `IDENTITY-WAVES.md` §8
allows ("unless a task file names an exact sentence"); the freeze writes the sentences into the
task files.

## 4. Tasks

Each task lists `Depends on`. The standard forms of FREEZE, QA, JUDGE, FIX and INT-CLOSE are in
`IDENTITY-WAVES.md` §10 and are not repeated.

### `W49-RULE-01` (integrator)
- **Depends on:** `W48-INT-CLOSE`; the owner's confirmation of the ruling texts of
  `IDENTITY-WAVES.md` §4.
- **Allowed paths:** `docs/program/OWNER_RULINGS_2026-09-17.md` (section `3.18`, continuing
  after `R-53`/`R-54`), `docs/program/dispatch/IDENTITY-WAVES.md`, `W49-PLAN.md`, `W50-PLAN.md`,
  `W51-PLAN.md` (replacing every provisional `R-` number with the recorded one, nothing else),
  `docs/program/W49-RULE-01.md`.
- **Required checks:** `grep -c 'R-55' docs/program/OWNER_RULINGS_2026-09-17.md` ≥ 1;
  `git diff --check`.

### `W49-FREEZE-01` (integrator)
Depends on: `W49-RULE-01`. Standard form; also copies the exact pinned sentences of §3.6, as
measured at the base, into the ACCESS and SEAL task files.

### `W49-ACCESS-01a/b/c` — migration, domain, repository (executor; one owner, three reports)
- **Depends on:** `W49-FREEZE-01`.
- **Allowed paths (all three):** `src/auditmanager/access/**`,
  `db/migrations/versions/<0015>*.py`, `tests/integration/access/**`, `tests/integration/db/**`
  (schema shape, lifecycle, inventories and digests, `test_app_user_migration.py`,
  `test_reviewer_display_name.py`, a new `test_accounts_migration.py`),
  `tests/integration/p02_journey/journey.py` (`P02_TABLES` only), the head-pin line of
  `tests/contract/api_v1/test_doc_prose_facts.py`, the migration-head rows of
  `docs/program/CONTRACT_PIN_REGISTRY.md`, the exact head sentences of
  `docs/program/CURRENT_STATE.md` and `docs/manual-tests/PC-01_prototype.md` named by the task
  file, `docs/program/W49-ACCESS-01{a,b,c}.md`.
- **01a — migration `0015` and schema:** every table/column/index/FK/trigger of §3.1–§3.3
  (including `expert_decision_event.author_user_uid` — the column, not its writer); backfill of
  §3.2; downgrade refuses while `app_user_role` or `registration_request` hold rows (after the
  backfill that is every real database — **`0015` is forward-only in practice and the rollback of
  W49 is a database restore; the report says so**); the reference register test against the
  schema's foreign keys; CLI `access.profile` and `access.grant`; §3.6's head pins.
- **01b — profile, names, archive, restore, purge:** normalisation and name rules in
  `access/models.py`; `display_label` precedence; the repository read of roles, archive state and
  profile completeness that `W49-SEAL-01` will widen `AccountStanding` with; ports and repository
  methods; every invariant of §3.2 at repository level; purge against the register.
- **01c — roles and registration lifecycle:** grant/revoke with epoch bump; submit, approve
  (one transaction, `FOR UPDATE`), reject, status read, password-column nulling, queue cap,
  constant-work comparison, throttle columns.
- **Required tests:** fresh upgrade to `0015` and downgrade on an empty tree; upgrade from a
  `0014` database holding the seeded `admin` with a changed password **and** from one holding a
  legacy non-e-mail test login; the trigger refuses a second decision, a password-column write
  after decision and a manual `created_user_uid` UPDATE; partial unique proven by two rows;
  `make gate` on the 01c hand-back; 01a hands back with `.venv/bin/python -m pytest
  tests/integration/db tests/integration/p02_journey tests/contract/api_v1/test_doc_prose_facts.py -q`
  green, 01b with `tests/integration/access -q` green.

### `W49-EDGE-01` — proxy rate limit and the proxy flag (executor)
- **Depends on:** `W49-SEAL-01` (the `rate_limited` code must exist before the proxy answers
  with it). Parallel with `W49-BFF-01`; disjoint paths.
- **Allowed paths:** `infra/deploy/proxy/nginx.conf`, `infra/deploy/proxy/tls-server.conf`,
  `infra/deploy/compose.server.yml` (the one `AUDITMANAGER_BEHIND_PROXY=1` line on `web`),
  `tests/contract/test_proxy_rate_limits.py` (new), `docs/program/W49-EDGE-01.md`.
- **Deliverables:** §3.5's proxy throttle exactly as described (zone and map once, `limit_req`
  and the named location in both server bodies, the `rate_limited` envelope); the flag line.
- **Required tests:** the new contract test reads both proxy files and the compose file and fails
  when any of the three loses its line, and checks the returned `error_code` against the
  catalog; `nginx -t` inside the pinned nginx image with both files mounted as `conf.d/` entries
  and a throwaway self-signed pair at `/etc/nginx/tls/{fullchain,privkey}.pem` (the TLS server
  block requires them; the configuration must load with both files present);
  `tests/integration/composition/test_proxy_tls_path.py`; `make gate`.

### `W49-DECISIONS-01` — the decision event names its author's account (executor)
- **Depends on:** `W49-ACCESS-01c` merged (ACCESS is one branch; the column exists from 01a).
- **Allowed paths:** `src/auditmanager/decisions/**`, `tests/integration/decisions/**`,
  `docs/program/W49-DECISIONS-01.md`.
- **Deliverables:** `ledger` and `journal` take and persist `author_user_uid` beside
  `author_label`; history rows stay NULL and are read as "author account unknown", never as a
  fault. Router wiring is `W49-SEAL-01`'s.

### `W49-SEAL-01` — contract, registers, routers, pins: one slot (executor; one owner, three reports, one gate)
- **Depends on:** `W49-ACCESS-01c`, `W49-DECISIONS-01`.
- **Why one slot:** §3.6. This is the one task in the programme allowed to exceed the 0.5–3 day
  rule, for the reason `W46-SEAL` was: the gate makes these files one unit. It hands back three
  reports (a, b, c) and **one** `make gate` at the final SHA; intermediate commits need not be
  green.
- **Allowed paths:** `contracts/api/v1/openapi.json`, `contracts/api/v1/README.md`,
  `contracts/domain/v1/identifiers.json`, `contracts/domain/v1/error-codes.json`,
  `contracts/domain/v1/error-envelope.schema.json`, `contracts/domain/v1/state-machines.json`,
  `contracts/domain/v1/README.md`, `web/src/shared/api/catalog-message.ts` (the one sentence for
  `rate_limited`), `web/openapi/openapi.json`, `web/src/shared/api/generated/**` (via
  `npm --prefix web run api:generate`), `web/FRONTEND_LOCK.json`, `tests/contract/**`,
  `web/tests/contract/**`, `src/auditmanager/api/**`, `src/auditmanager/bootstrap/adapters.py`,
  `src/auditmanager/bootstrap/composition.py` (this wave's composition-root owner),
  `tests/integration/api/**`, `tests/integration/auth/**`, `tests/integration/composition/**`,
  `tests/e2e/pc01/test_acceptance.py` (the route-count assertion only),
  `web/src/app/bff/v1/[...path]/route.ts` and `web/src/shared/api/authorization.ts` (the one
  count comment in each, §3.6), `docs/program/CONTRACT_PIN_REGISTRY.md` (all rows but the
  head's), the exact live triple sentences of `docs/program/CURRENT_STATE.md` and
  `docs/program/ALPHA_ROADMAP.md` named by the task file, `docs/program/W49-SEAL-01{a,b,c}.md`.
- **01a — the documents:** §3.4 operations and schemas; `conflict_reason`; `rate_limited` in
  the catalog, the envelope schema, the `== 22` literal and `catalog-message.ts`; identifiers
  (`usr`, `reg`, and their registry types); the two state machines; the superseded denials with
  the `rg` check; regenerated client, mirror and lock; every surface pin of §3.6; the
  registry rows; the live sentences; measured triple and SHA-256 in the report; compatibility
  statement (every existing operation unchanged on the wire). Hands back with
  `.venv/bin/python -m pytest tests/contract -q`, `npm --prefix web run api:verify` and
  `npm --prefix web test -- --run tests/contract` green; the integration suites are expected red
  until 01c.
- **01b — the seam:** the three registers and `OPERATION_ROLES`; `AccountStanding`, its protocol
  and the adapter widened with roles, archive state and profile completeness; the evaluation
  order of §3.2; sweep tests: for every operation × role set in
  `{∅, {expert}, {admin}, {expert, admin}}` × {complete, incomplete} × {default, changed} the
  served application's answer equals the registers. Hands back with
  `.venv/bin/python -m pytest tests/integration/api/test_authorization.py tests/integration/auth -q`
  green.
- **01c — the routers:** `me.py`, `registrations.py`, `users.py`; the decisions router passes the
  subject's `user_uid` to the ledger; the status read with constant work. The suite's own logins
  change where the plan changes the rule: `tests/integration/api/driver.py` (`SUITE_LOGIN`
  becomes an e-mail with a complete profile), `test_authorization.py` (the open set is now three),
  `test_decision_authorship.py` and `tests/integration/auth/test_the_reviewer_name_is_visible.py`
  (the label bound is the 66-character name form).
- **Required tests:** `.venv/bin/python -m pytest tests/contract -q`;
  `npm --prefix web run api:verify`; `npm --prefix web test -- --run tests/contract`;
  `tests/integration/api/test_authorization.py` extended; new `test_role_register.py`,
  `test_registration_flow.py`, `test_user_management.py`;
  `tests/contract/api_v1/test_openapi_conformance.py`; `make gate` at the final SHA.
- **Stop:** any new error code other than `rate_limited`; a change to an existing operation's
  shape; a free-text detail key; a business rule in a router.

### `W49-BFF-01` — session subject, notice, throttle, refusal sentences (executor)
- **Depends on:** `W49-SEAL-01` (generated client, registers, `rate_limited`). Parallel with
  `W49-EDGE-01`.
- **Allowed paths:** `web/src/app/bff/**`, `web/src/app/login/page.tsx` (reads and deletes the
  notice), `web/src/shared/api/credentialed-forward.ts`, `web/src/shared/config/**` (the session
  store format and the proxy flag), `web/src/features/sign-in/**`, `web/src/_pages/sign-in/**`,
  `web/tests/unit/session/**`, `web/tests/guards/session-durability.guard.test.ts`,
  `web/tests/guards/server-credential.guard.test.ts`, `docs/program/W49-BFF-01.md`.
- **Deliverables:** §3.5 in full, including the `throttled` value and sentence in both closed
  refusal sets and the registration handler's set. `layout.tsx` and the frame are untouched (W50).
- **Required tests and mutations:** `npm --prefix web test -- --run`; lint; typecheck; a forward
  under the `registrations` segment through the catch-all is refused with and without a session;
  a version-1 register file is replaced, not read; the notice is deleted on first read and absent
  after its TTL; removing the upstream-401 row-closing is red; the bucket refuses the N+1th guest
  request within the window; a forged `X-Forwarded-For` does not escape the bucket; without the
  flag the bucket is global.

### `W49-QA-01` (executor, fresh context)
Depends on: `W49-BFF-01` and `W49-EDGE-01` merged. Standard form, files under `tests/integration/api/qa_w49/**`,
`tests/integration/access/qa_w49/**`, `web/tests/unit/qa_w49/**`. Brief: approve race;
archive/purge/demote/reset of self; last-admin removal through `updateUser` and `archiveUser`;
token after role removal → 401 → the BFF closes the row and answers the envelope; restore
collision; queue cap at 100 and 101; registration with a taken login; status read as
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
  a forged `X-Forwarded-For`; BFF: the reserved registration handlers reach only the two public
  operations, and the catch-all refuses the `registrations` segment with or without a session.
- Y: routers free of SQL/logic (`rg` queries recorded); invariants live in `access`; the ALR-05
  guard green (AST walk 0 / 0); migration fresh and both upgrade paths; partial unique; the
  reference register equals the schema's foreign keys to `app_user`; the reseal documents and
  the routers in one slot; registers equal sweeps; `AGENTS.md` §4: approval is one transaction,
  no silent fallback, no display-string identity; `KNOWN_OUTSTANDING_CLAIMS` empty and every
  pin's needle live.
- Cross-examination as in `W48-JUDGES.md`.

### `W49-FIX` (executor), `W49-INT-CLOSE` (integrator)
Standard forms. INT-CLOSE additionally registers the debts of §3 (`display_name` retirement,
`is_default_credential` naming, login disclosure, bulk rejection, decided-request retention,
temporary password known to the administrator, `0015` forward-only).

## 5. Integration order

1. `W49-RULE-01`, then `W49-FREEZE-01`.
2. Stage A: `W49-ACCESS-01a → 01b → 01c` from the freeze SHA.
3. Stage B: `W49-DECISIONS-01` from the ACCESS merge.
4. Stage C: `W49-SEAL-01` (a → b → c, one gate) from the DECISIONS merge.
5. Stage D: `W49-BFF-01` ∥ `W49-EDGE-01` from the SEAL merge; merge BFF, then EDGE.
6. Stage E: `W49-QA-01`; judges X and Y in parallel; cross-examination.
7. `W49-FIX` for upheld release-blocking findings only.
8. `W49-INT-CLOSE`.

## 6. Ownership matrix

| Hotspot / path family | Owner | Role | Parallel writer |
| --- | --- | --- | --- |
| `OWNER_RULINGS_2026-09-17.md` §3.18, provisional numbers in the four plans | `W49-RULE-01` | integrator | none |
| migration `0015`, `src/auditmanager/access/**`, `tests/integration/access/**`, `tests/integration/db/**`, `P02_TABLES`, head pin, head registry rows, head sentences | `W49-ACCESS-01a/b/c` | executor | none |
| `src/auditmanager/decisions/**`, `tests/integration/decisions/**` | `W49-DECISIONS-01` | executor | none |
| `contracts/**`, `web/openapi/**`, generated client, `web/FRONTEND_LOCK.json`, `src/auditmanager/api/**`, `bootstrap/adapters.py`, `bootstrap/composition.py`, `catalog-message.ts`, `tests/contract/**` except `test_proxy_rate_limits.py`, `web/tests/contract/**`, `tests/integration/{api,auth,composition}/**`, the `test_acceptance.py` pin line, the two `web/src` count comments, `CONTRACT_PIN_REGISTRY.md` surface rows, triple pin and triple sentences | `W49-SEAL-01` | executor | none |
| `web/src/app/bff/**`, `app/login/page.tsx`, `shared/config/**`, `features/sign-in/**`, `_pages/sign-in/**`, session tests | `W49-BFF-01` | executor | EDGE |
| `infra/deploy/proxy/*.conf`, the compose flag line, `tests/contract/test_proxy_rate_limits.py` | `W49-EDGE-01` | executor | BFF |
| `web/src/_app/**`, `web/src/app/layout.tsx`, `globals.css`, `shared/ui/**` | frozen (W50) | — | none |
| root locks (`uv.lock`, `web/package-lock.json`) | frozen | — | none |
| `CURRENT_STATE.md` live section, `DEBT_REGISTER.md`, `origin/dev` | `W49-INT-CLOSE` | integrator | none |
| `origin/main`, tags | nobody without a direct owner instruction | integrator | none |

## 7. Stop conditions

Those of `W48-PLAN.md` §14, plus: a rule of §3 turns out to need a decision the polls did not
take; any new error code other than `rate_limited`, or a free-text detail key; an existing operation changes shape; the
migration cannot upgrade a `0014` database holding the seeded account; the sweep finds an
operation outside every register; a refusal is computed in a router or a schema validator
instead of `access`; a lane's gate is red on a pin this plan did not assign.

## 8. Non-goals

Screens (W50/W51); mail; verification; captcha; avatar upload; multi-tenancy; retiring
`display_name`; a version endpoint; any change to analysis, runs or findings; any change to
`DecisionEvent` on the wire.
