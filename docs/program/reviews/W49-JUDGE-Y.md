# W49-JUDGE-Y — independent judge, architecture and data-integrity entry point

- **Task:** `docs/program/tasks/W49-JUDGE-Y.md` (read at `1b25955`)
- **Subject:** `1b259556a98e529ecf7378c335fa85b1c9a426b3` on `integration/w49`
  (`merge(W49): rate-limit the two public registration operations at the proxy`)
- **Base of the wave:** `23e0579` (W48 closure on `origin/dev`)
- **Branch:** `agent/w49-judge-y`, worktree `.local/worktrees/w49-judge-y`
- **Author independence:** this session wrote none of the code, contracts, migrations, tests or
  plans it judges.
- **Report-only:** this file is the only tracked path this branch changes.

Part one (sections 1–9) is this judge's own pass, committed before reading
`docs/program/dispatch/W49-PLAN.md`, any `docs/program/W49-*.md` lane or QA report, or anything
under `docs/program/reviews/`. Part two (sections 10–11) is the cross-examination and the
verdict, written after that commit.

---

## 1. Inputs read before the own pass

`AGENTS.md`; the task file; `docs/program/CURRENT_STATE.md`;
`docs/program/dispatch/OPERATING_CONSTRAINTS.md` §1–§10 (and the sections between them);
`docs/architecture/ARCHITECTURE_LINT_RULES.md` (ALR-01…ALR-05, ALR-14…ALR-19);
`docs/program/OWNER_RULINGS_2026-09-17.md` §3.19 (`R-55`…`R-61`, with the `R-56` addendum);
the code, contracts, migrations and tests at the subject; the `docs/program/tasks/W49-*.md`
task files where a commit message pointed at them. Commit subjects of the wave were read with
`git log`; the commit *bodies* of `220638d` and `2a31edf` were read because the identifier
finding (F-1) had to be traced to the commit that produced it.

Not read before the own-pass commit: `docs/program/dispatch/W49-PLAN.md`,
`docs/program/W49-*.md`, `docs/program/reviews/**`.

## 2. Environment

| Item | Value |
|---|---|
| Host kernel | Linux 6.8.0-142-generic |
| Lane | `FOUNDATION_INSTANCE=gate-w49jy`, `POSTGRES_PORT=56620`, `S3_API_PORT=60220`, `S3_CONSOLE_PORT=60221`, `POSTGRES_DB=auditmanager_w49jy`, `S3_BUCKET=auditmanager-w49jy` (`.env` = `w49-int`'s with only these values renamed; `DATABASE_URL`/`S3_ENDPOINT_URL` carry the same ports) |
| Port check before start | `ss -ltn \| grep -E ':(56620\|60220\|60221)\b'` → exit 1 (all three free); after `make foundation` all three listen on `127.0.0.1` |
| Services | foundation only (`make foundation`): PostgreSQL 17.11, pgvector 0.8.6, MinIO. No application image was built; `make gate` was not run |
| Runtime | `.venv` Python 3.12.3, pytest 9.1.1, FastAPI 0.141.1; `.venv/bootstrap` jsonschema 4.26.0; node v22.23.1 (`npm --prefix web ci` only) |
| Memory | `free -g` before start: available 4 GB; lowest observed during the run: 2 GB (another judge's stand in parallel) |
| Mutation copy | `make mutation-copy MUT=/root/w49jy-mut FULL=1` → `MUTATION-COPY OK /root/w49jy-mut/src/auditmanager/__init__.py`; every mutation run with `PYTHONDONTWRITEBYTECODE=1` and `__pycache__` cleared between cases |
| Probe databases | `jy_fresh`, `jy_up_a`, `jy_up_b`, `jy_sweep`, created and dropped inside this lane's own PostgreSQL only |

## 3. Commands and exit statuses

Every pytest run below was one run at a time in this lane, with the tree committed or unchanged.
Logs were kept in the session scratchpad; the counts are quoted from the pytest summary line.

| # | Command (in the worktree unless stated) | Exit | Result |
|---|---|---|---|
| C1 | `make bootstrap FOUNDATION_PYTHON=/usr/bin/python3.12` | 0 | `bootstrap OK` |
| C2 | `npm --prefix web ci` | 0 | 184 packages |
| C3 | `make foundation` | 0 | migrations `0001`→`0015` on an empty database; `check-db: current 0015_accounts_roles_registration`; foundation suite 35 passed |
| C4 | `.venv/bin/pytest -q tests/contract/architecture/test_alr05_boundaries.py` | 0 | 1 passed |
| C5 | independent ALR-05 AST walk (Appendix A.1) over `src/auditmanager` | 0 | **deep 0 / package-root 0**; 43 imports of a `public` module; 54 cross-context imports from `bootstrap` (composition root, exempt by ALR-05's text) counted, not hidden; 0 `shared`→context imports; 0 literal `import_module`/`__import__` targets |
| C6 | `.venv/bin/pytest -q tests/integration/db/test_accounts_migration.py tests/integration/db/test_accounts_operator_commands.py` | 0 | 60 passed |
| C7 | upgrade-path probe (Appendix A.2): `jy_fresh` → head; `jy_up_a`, `jy_up_b` → `0014`, seeded by the **W48 code** (`git archive 23e0579 src`), then → head | 0 (each of 5 `alembic upgrade`) | see §5.4 |
| C8 | after-upgrade journeys through the real composition root (Appendix A.3) on `jy_up_a`, `jy_up_b` | 0, 0 | see §5.4 |
| C9 | served-application register sweep (Appendix A.4) on a fresh `jy_sweep` | 0 | 34 served operations = `OPERATION_ROLES ∪ UNAUTHENTICATED_OPERATIONS`; **342 requests, 0 mismatches** |
| C10 | partial-unique / purge / guard / concurrency probe (Appendix A.5) on `jy_sweep` | 0 | see §5.5 |
| C11 | approval-atomicity fault injection (Appendix A.6) on a fresh `jy_sweep` | 0 | see §5.9 |
| C12 | reference register vs `pg_constraint` (Appendix A.7) on the lane database | 0 | 6 = 6, equal |
| C13 | three catalogs vs their schemas, `.venv/bootstrap/bin/python` + jsonschema | 0 (script) | error-codes 0 errors, state-machines 0, **identifiers 4 errors** (F-1); same check at `23e0579`: 0 / 0 / 0 |
| C14 | the domain README's own "every catalog validates against its schema" one-liner (`contracts/domain/v1/README.md` §Verification) | **1** | `ValidationError ... On instance['entities']['User']: 'user_uid'` |
| C15 | the README's envelope-enum, guard-code and family-consistency one-liners | 0, 0, 0 | envelope enum = catalog (23); guard codes OK (13); bindings OK, one `contract_version`, `candidate_revision` 9 |
| C16 | `.venv/bootstrap/bin/python scripts/validate_bootstrap.py` | 1 | 5 problems, all `Broken md link` in older reports (`W38-KB`, `W39-REVOKE`, `W12/16/27-WEB` reviews) — pre-existing, not W49; the quarantined script is not in the gate |
| C17 | `.venv/bin/pytest -q tests/contract --ignore=…cp00_candidate --ignore=…cp00_final_state --ignore=…validate_bootstrap` | 0 | 467 passed, 50 subtests |
| C18 | pin registry: every needle of `docs/program/CONTRACT_PIN_REGISTRY.md`'s JSON block read from its path; `KNOWN_OUTSTANDING_CLAIMS` read by AST | 0 | 27 pins, 27 unique ids, 0 dead needles, 0 needles occurring twice; `KNOWN_OUTSTANDING_CLAIMS = frozenset()` at `tests/contract/api_v1/test_doc_prose_facts.py:527` |
| C19 | `.venv/bin/pytest -q tests/integration/access` | 0 | 210 passed |
| C20 | `.venv/bin/pytest -q tests/integration/api/{test_role_register,test_user_management,test_registration_flow,test_authorization,test_decision_authorship,test_operation_surface,test_served_document_and_health_plane}.py` | 0 | 129 passed |
| C21 | `.venv/bin/pytest -q tests/integration/auth tests/integration/decisions/test_decision_author_account.py tests/integration/decisions/test_decision_ledger.py tests/integration/composition` | 0 | 483 passed, 1 skipped (`test_router_answers.py:358`, pre-existing data-dependent skip) |
| C22 | first-parent landing of every reseal artefact (`git log --first-parent 23e0579..HEAD -- <path>`) | 0 | see §5.7 |
| C23 | edge probes (Appendix A.8) on `jy_sweep` | 1 (the last line imports `jsonschema`, absent from the runtime venv; every probe line before it printed) | see F-3, F-5, F-6 |
| C24 | final unmutated sweep on a fresh `jy_sweep`, after all mutations were restored | 0 | 342 requests, 0 mismatches |

## 4. What was checked, and how, in one table

| Deliverable | Verdict | Where |
|---|---|---|
| Routers free of SQL and business logic | holds | §5.1 |
| Invariants in `access`, not in routers or schemas | holds | §5.2 |
| ALR-05 guard green; independent walk 0 deep / 0 package-root | holds | §5.3 |
| Migration `0015` fresh, and both upgrade paths | holds | §5.4 |
| Partial unique indexes | hold | §5.5 |
| Reference register = schema's foreign keys to `app_user` | holds | §5.6 |
| Reseal documents and routers in one slot | holds | §5.7 |
| Three access registers and `OPERATION_ROLES` = served application | holds | §5.8 |
| `AGENTS.md` §4 | holds | §5.9 |
| `KNOWN_OUTSTANDING_CLAIMS` empty; every pin's needle live | holds | §5.10 |
| Error catalog, envelope schema, domain revision, identifier catalog consistent | **fails: the identifier catalog does not validate against its own schema** | §5.11, F-1 |

## 5. Checks

### 5.1 Routers free of SQL and business logic

The queries, run over `src/auditmanager/api` at the subject:

```text
Q1  rg -n "^\s*(from|import)\s+(sqlalchemy|psycopg|asyncpg|sqlite3|databases)" src/auditmanager/api
    -> exit 0, one hit: src/auditmanager/api/routers/errors.py:39  from sqlalchemy.exc import DBAPIError
       (unchanged since before W49: `git show 23e0579:src/auditmanager/api/routers/errors.py` carries it; see F-7)
Q2  rg -n "\b(AsyncSession|Session|Connection|Engine|sessionmaker|session\.execute|\.execute\(|\.commit\(|\.rollback\(|begin_nested)\b" src/auditmanager/api
    -> exit 0, three hits, all prose ("Session `B5`", "A port never takes a ``Session``")
Q3  rg -n -i "[\"'](\s*)(select|insert|update|delete|create|alter|drop|with)\s" src/auditmanager/api
    -> exit 0, four hits, all docstrings ("Create a project…", "Delete an archived…", "Create the account…", "Drop the ``default``…")
Q4  rg -n "\btext\(" src/auditmanager/api
    -> exit 1 (none)
Q5  AST walk of every If/IfExp/Compare/Assert in api/routers/*.py, api/schemas/*.py and
    bootstrap/adapters.py whose test mentions actor_uid==, user_uid==, archived, last_admin,
    LAST_ADMIN, SELF_ACTION, ROLE_ADMIN, ROLE_EXPERT, profile_complete, is_default_credential or roles
    -> two hits, both optional-field mapping: users.py:108 `body.roles is None`, adapters.py:1185 `roles is not None`
```

The three new routers (`me.py`, `users.py`, `registrations.py`) parse, call one port method and
render. The one conditional with an outcome, `registrations.py` `read_registration_status`
(`if status is None: raise DomainError(ErrorCode.AUTHENTICATION_REQUIRED)`), maps the port's
"no" to the transport's refusal. `handlers.py` and `declarations.py` changes are transport
(path-parameter aggregate names, list-location naming, the `include_archived` absent flag).

### 5.2 Invariants live in `access`

The §3.2 invariants are raised in `src/auditmanager/access/accounts.py` and
`src/auditmanager/access/registrations.py`, never in a router, schema or adapter:

- no act on oneself — `_refuse_self` (`accounts.py`), used by archive, purge, revoke/set roles, reset;
- last active administrator — `_lock_admins_then` + `_refuse_last_admin`, under a lock on every
  active administrator row in `user_uid` order;
- purge only archived and unreferenced — `purge_account` + `references_to` (the register),
  with the database's RESTRICT keys as backstop (`23503` → `account_referenced`);
- approval grants at least one role, one decision per request, password nulled at the decision —
  `RegistrationRepository.approve`/`reject`, and `trg_registration_request_guard` in the database.

What lives outside `access` is the seam's operation→role policy (`api/security.py`
`OPERATION_ROLES` and the two capability registers). That is authorization over `operationId`s,
read against a standing the seam receives through a port; it is where `T-6` put the seam and it
imports nothing of `access`. Two transport bounds restate contract keywords
(`ApproveRegistrationRequest.roles` `min_length=1` = `minItems: 1`, `_unique_roles` =
`uniqueItems`); the rule itself is also in `access`, so neither is the only enforcement.

### 5.3 ALR-05

`test_alr05_boundaries.py` passes (C4). The independent walk (Appendix A.1, written without the
guard's code: relative imports resolved with `importlib.util.resolve_name`, `from auditmanager
import X` treated as package-root, literal `import_module`/`__import__` targets included,
every directory under `src/auditmanager` treated as a context whether or not it has an
`__init__.py`) reads **0 deep / 0 package-root** (C5). Both instruments were shown able to fail
(M1, M1b).

### 5.4 Migration `0015`: fresh and both upgrade paths

Fresh (`jy_fresh`, and the lane database through `make foundation`): head
`0015_accounts_roles_registration`; the seed reads `admin | is_default_credential=t |
legacy=t | roles admin,expert`.

Path A — a `0014` database whose seeded `admin` changed its password **with the W48 code**
(`UserRepository.change_password` imported from `git archive 23e0579 src`, `token_epoch` 2,
default flag cleared) → head: `admin | f | legacy | epoch 2 | admin,expert`; deployment log
"1 existing account(s) now hold the role 'expert'…", "the account 'admin' also holds the role
'admin'". Through the real composition root (C8): sign-in with the legacy login and the changed
password 200, `is_default_credential=false`; `getMe` 200, `profile_complete=false`,
roles `[admin, expert]`; `listProjects`/`listUsers` 403 `required_capability: profile_completed`;
completion without an e-mail 422 `field: email`; a raw `UPDATE … profile_completed_at=now()` on
the legacy login is refused by `ck_app_user_login_format` (`23514`); completion with an e-mail
200 (label `Петров П. И.`); the legacy login then 401, the e-mail 200; `listProjects` and
`listUsers` 200; a second completion with another e-mail 422 `field: login`.

Path B — a `0014` database holding the untouched seed and two legacy non-e-mail logins created
by the W48 code (`reviewer.one`, `qa_2-x`) → head: both `expert`, legacy; the seed
`admin,expert`. The same journey for `reviewer.one`: identical answers, except `listUsers` after
completion is 403 `role:admin` — correct, it holds `expert` only.

The repository's own `TestUpgradeFromA0014Database` (both paths and the no-seed path) and
`TestTheDowngrade` pass (C6).

### 5.5 Partial unique indexes

From `pg_index` on the lane database: `uq_app_user_login … (login) WHERE (archived_at IS
NULL)`, `uq_registration_request_pending_login … (login) WHERE (status = 'pending')`,
`ix_expert_decision_event_author_user_uid … WHERE (author_user_uid IS NOT NULL)`.
Behaviour through the API (C10): a second pending request for one login, typed in upper case,
is 409 `request_pending`; a submission for a login an active account holds 409 `login_taken`;
after archiving the holder the same login submits (201) and is approved, leaving two rows with
the login, one active; restoring the archived one is 409 `login_taken`; a raw second active
holder and a raw second pending request are refused by the indexes themselves (`23505`).
Two concurrent approvals of one request: `[200, 409]`, one account created.

### 5.6 Reference register equals the schema's foreign keys

`ACCOUNT_REFERENCES` (imported from `auditmanager.access.public`) against every single-column
foreign key `pg_constraint` lists with `confrelid = app_user` (C12): **6 = 6, schema-only [],
register-only []** — `app_user.archived_by` RESTRICT, `app_user_role.granted_by` RESTRICT,
`app_user_role.user_uid` CASCADE, `registration_request.decided_by` RESTRICT,
`registration_request.created_user_uid` SET NULL, `expert_decision_event.author_user_uid`
RESTRICT. No migration before `0015` creates a foreign key to `app_user`
(`rg -n "REFERENCES app_user" db/migrations/versions` outside `0015`: none).
Behaviour (C10): purging an archived, unreferenced account 204 and its request keeps
`status=approved` with `created_user_uid` NULL (the cascade passes the guard); purging an
archived administrator who decided requests 409 `account_referenced`; a manual NULL of
`created_user_uid`, a DELETE and a second decision are refused by the guard (`AM003`, `AM003`,
`AM001`).

### 5.7 Reseal documents and routers in one slot

`git log --first-parent 23e0579..HEAD -- <path>` names exactly one slot, `2a31edf`
(`merge(W49): the contract, the access registers and the identity routers in one slot`), for
each of: `contracts/api/v1/openapi.json`, `web/openapi/openapi.json`,
`web/src/shared/api/generated/operations.gen.ts`, `web/FRONTEND_LOCK.json`, the three domain
catalogs and `identifiers.schema.json`/`error-envelope.schema.json`, `api/routers/{me,users,
registrations}.py`, `api/security.py`, `api/schemas/models.py`, `bootstrap/adapters.py`,
`shared/errors/codes.py`, `contracts/api/v1/README.md`, `contracts/domain/v1/README.md`,
`src/auditmanager/api/README.md`, `docs/program/P02_SEAMS.md`, `infra/deploy/README.md`.
`CURRENT_STATE.md` and `CONTRACT_PIN_REGISTRY.md` moved in `0dbb418` (migration head) and
`2a31edf` (surface); the BFF route and the proxy moved again only in their own later slots
(`4159555`, `1b25955`), which consume the contract and do not change it.

### 5.8 Registers equal the served application

Independent sweep (Appendix A.4): the application is built by the **real composition root**
(`create_app` → `bootstrap.composition.build_application`, real `CredentialAdapter.standing_of`
over real rows), the routes are enumerated from the served application (34 operations, 4
documentation routes), and the expected answer is computed from `R-50`/`R-59`/`R-60` as written
in the rulings, not read from `api/security.py`. Nine standings, each a real account created
through the API or the operator code path: anonymous; complete with roles ∅, {expert}, {admin},
{expert, admin}; complete on a default credential (an administrator's reset); incomplete
(legacy login, operator `grant_role`); incomplete on a default credential; archived, with a
credential minted **under its current epoch** so only the archive flag can refuse it.
Every passing request was aimed at a nonexistent identity or carried an invalid body.
Result (C9, C24): **34 served operations = `OPERATION_ROLES ∪ UNAUTHENTICATED_OPERATIONS`;
342 requests, 0 mismatches.** The sweep reddens on a one-line register change (M4).
The repository's own sweep (`test_role_register.py`) passes too (C20); it drives the seam with
stand-in standings, so it and this one cover different halves.

### 5.9 `AGENTS.md` §4

- **Approval is one transaction.** A probe trigger in the disposable database made the *last*
  statement of an approval (the decision UPDATE) fail (C11): the API answered 500
  `internal_error`, and afterwards 0 accounts with the login, 0 role rows, the request still
  `pending` with its digest, 0 `command_record` rows for the key. With the trigger dropped the
  same key approved (200) and created exactly one account. Claim, account, roles and decision
  share `_SessionHolder._write`'s one session and one commit.
- **No silent fallback.** `parse_role` and `_seam_role` refuse an unknown role; `standing_of`
  answering `None` is a refusal; `RegistrationAdapter.read_status` turns a proven non-pending
  request into `internal_error` rather than showing it; the operator CLIs report and exit 2.
  `spend_a_verification`'s `except DomainError: return` spends nothing on a password that could
  not match any digest, a declared equal-cost path, not a success.
- **No display-string identity.** `expert_decision_event.author_user_uid` (RESTRICT) is written
  from `Subject.user_uid`; no statement selects or compares by `display_name`, names,
  `author_label` or `display_label` (`rg` for `WHERE … (display_name|last_name|first_name|
  author_label|display_label) =` and for `==` on them: none). The login is unique only among
  active accounts and is not used as a key.
- **No dual-write.** `access` imports no object-store, HTTP or mail client
  (`rg` for `boto|httpx|requests|smtplib|urllib|BlobStore`: none); registration sends no mail
  (`R-56`); revocation is a column.
- No generic repository or base service added; no job state introduced.

### 5.10 `KNOWN_OUTSTANDING_CLAIMS` and the pins

`KNOWN_OUTSTANDING_CLAIMS = frozenset()` (read by AST). All 27 pins of
`CONTRACT_PIN_REGISTRY.md` resolve: each needle occurs exactly once at its path (C18). The
non-surface pins name 22 stored codes, 23 catalog codes in four places and the head
`0015_accounts_roles_registration`.

### 5.11 Catalogs, envelope, revision, identifiers

- Error catalog: 23 codes; `rate_limited` 429 retryable, no detail keys; `conflict` gains
  `conflict_reason` with the five values the code raises (`login_taken`, `request_pending`,
  `queue_full`, `account_referenced`, `last_admin`); `ErrorCode` has 23 members; the envelope
  schema's `error_code` enum equals the catalog (C15).
- Domain revision: all three catalogs and all three schemas carry `candidate_revision` 9, one
  `contract_version` `1.0.0-draft.1` (C15).
- State machines: `app_user` (`active→archived→active|purged`) and `registration_request`
  (`pending→approved|rejected`) match the code and the guard trigger.
- **Identifier catalog: does not validate against its own schema** (C13, C14) — F-1.

## 6. Findings

Classes: **release-blocking** (W49 must not be released with it; opens `W49-FIX`),
**must-fix-before-merge** (no runtime harm, but must be repaired while the slot that owns it is
still this wave's), **register** (record and schedule).

### F-1 — must-fix-before-merge — the identifier catalog fails its own schema

- **Where:** `contracts/domain/v1/identifiers.schema.json:179-206` (`entities.additionalProperties.enum`)
  and `:234-261` (`distinct_identities.items.identifiers.items.enum`) list the 27 pre-W49
  identifier names; `contracts/domain/v1/identifiers.json:90-91` binds `User → user_uid`,
  `RegistrationRequest → request_id`, and `:166-169` adds `account_identity` naming both.
- **Reproduction:** `.venv/bootstrap/bin/python` + jsonschema 4.26.0, Draft 2020-12:
  4 errors — `entities/User`, `entities/RegistrationRequest`,
  `distinct_identities/5/identifiers/0`, `…/1`, each "`'user_uid'`/`'request_id'` is not one of
  […]". The README's own verification one-liner (C14) exits 1. At `23e0579` the same check reads
  0 errors.
- **Cause:** `220638d` (`W49-SEAL-01c`) moved the three schemas' `candidate_revision` const
  8→9 without adding the two names to the two enums. In the same slot,
  `contracts/domain/v1/README.md:8-10` and `:753` still state that "the three family schemas
  still pin `const: 8`" and that the catalogs and schemas "disagree until an owner of those files
  moves the pins" — the pins have moved, and the README now describes a disagreement that is no
  longer the one that exists.
- **Consequence:** the sealed revision-9 domain contract is internally inconsistent: any consumer
  that validates the catalog (the README's documented gate, CP-00 tooling) rejects it. Nothing at
  runtime reads `identifiers.schema.json` and the gate runs no catalog-against-schema validation
  (`rg` finds the schema file named only in the quarantined `tests/contract/test_cp00_candidate.py`),
  which is how it reached the merged candidate green.
- **Why not release-blocking:** no served behaviour, stored value or generated client depends on
  it. **Why before merge:** `contracts/**` moves only in `W49-SEAL-01`; once this candidate is
  published, the repair is a further reseal of revision 9 (or a revision 10).
- **Repair shown sufficient:** M5 — adding `user_uid` and `request_id` to the two enums, and
  nothing else, makes the catalog validate (0 errors). The two README sentences move with it.

### F-2 — register — a live schema comment and a migration log instruct a removed command

- **Where:** `db/migrations/versions/20260923_0009_reviewer_display_name.py:118` (column
  COMMENT) and `:134` (deployment-log warning).
- **What:** the live `app_user.display_name` comment at head still reads "Set with python -m
  auditmanager.access.name …" and "the label falls back to the login, which is unique and is
  1-100 characters, so it always fits author_label". `W49-SEAL-01` removed `access/name.py`
  (`tests/integration/auth/test_the_reviewer_name_is_visible.py:215-218` proves the module is
  gone), and since `0015` a login is unique only among active accounts and up to 254 characters.
  `0015` re-comments `login`, `profile_completed_at` and the archive columns but not this one.
- **Reproduction:** `select col_description('app_user'::regclass, <attnum of display_name>)`
  on the lane database.
- **Consequence:** an operator reading the schema is told to run a module that fails with
  "No module named"; the 1–100/fits claim is false for a legacy fallback that no longer exists
  on complete profiles. No security edge (`OPERATING_CONSTRAINTS.md` §4.7's class, without its
  direction of damage). A later migration's `COMMENT ON COLUMN` is the repair; `0009` is history.

### F-3 — register — `name_label` can exceed the contracted 66 characters

- **Where:** `src/auditmanager/access/models.py:356-367` (`name_label`, `first_name[0].upper()`),
  `:148` (`MAX_NAME_LABEL_LENGTH = 66`); `contracts/api/v1/openapi.json:4320`
  (`RegistrationRequest.display_label` `maxLength: 66`).
- **What:** `normalize_person_name` admits a name starting with `ß`, `ŉ` or `ǰ`, whose
  `str.upper()` is two characters. A 60-letter last name with such first and middle names gives
  a 68-character label.
- **Reproduction:** C23/E5 — submit `last_name="A"*60`, `first_name="ßabc"`,
  `middle_name="ßabc"` (201); `listRegistrations` serves `display_label` of length 68.
- **Consequence:** a served body violates the frozen schema for that item; `author_label`
  (≤128) is unaffected. Realistic names do not start with these letters.

### F-4 — register — the "per-request standing read" is not the one production uses

- **Where:** `src/auditmanager/access/accounts.py:141-152` (`_SELECT_STANDING`, documented as
  "run on every credentialed request") and `:335` (`account_standing`);
  `src/auditmanager/bootstrap/adapters.py:1037` (`CredentialAdapter.standing_of` reads
  `get_account`).
- **What:** `account_standing` is reached only by tests (`test_roles.py:74`,
  `test_account_management.py:75-132`); the served seam reads `get_account`. The production path
  is covered (`tests/integration/auth/test_the_standing_is_the_accounts_row.py`, and C9), so this
  is a second, unused statement of one decision with a comment claiming it is the live one.

### F-5 — register — docstrings that say the opposite of the code

- `src/auditmanager/access/accounts.py:390` — `complete_profile` documents
  `state_transition_not_allowed` for an already complete profile; the code raises
  `validation_failed` on `login` (`:402-406`), which is what the contract describes.
- `src/auditmanager/access/registrations.py:40-46` — the rejected-applicant answer is called
  "an open question … a one-statement change once ruled"; it was ruled (`R-56` addendum,
  2026-10-06) and the code already implements the ruling.
- `src/auditmanager/bootstrap/adapters.py:1174` — "a refused role change keeps the names":
  measured (C23/E1), `updateUser` on oneself with new names and a dropped `admin` is 403 and the
  names are **not** changed (the whole transaction rolls back). The behaviour is the atomic one;
  the sentence reads as its opposite.

### F-6 — register — an archived account is changed by one operation and "not found" by another

- `updateUser` on an archived account is 200 and changes its roles and names (C23/E2, E3:
  `{expert, admin}` → `{expert}`), while `resetUserPassword` on the same account is 404
  `not_found` (E3b) and `AccountRepository.grant_role` refuses an archived account
  (`accounts.py:687`). `set_roles`/`update_names` (`accounts.py:488`, `:735`) do not check
  `archived`. No standing is affected (an archived account is refused on every request), and the
  contract's `updateUser` text is silent on archived targets; the refusal surface is simply not
  one rule.

### F-7 — register (pre-existing, information) — ALR-01's literal detection matches `errors.py`

`src/auditmanager/api/routers/errors.py:39` imports `sqlalchemy.exc.DBAPIError` for exception
classification. ALR-01 detection (a) flags any `sqlalchemy` import in a router module; this one
executes no SQL and touches no session. Present at `23e0579`; not introduced by W49.

### Q-1 — interpretation for the cross-examination, not a finding

`R-60`: "An active account **with any role** reads product data." The seam reads it as "any
complete account, whatever its roles, none included" (`OPERATION_ROLES` reads = `frozenset()`;
`accounts.py` `set_roles` docstring; the contract's description "Reading product data needs any
active account with a complete profile"). The sweep confirms the served behaviour (a complete
account with ∅ roles reads all 13 product reads). Whether "with any role" means "whatever role"
or "with at least one role" is to be settled against `W49-PLAN.md` §3.2 in part two.

## 7. Mutations

All in `/root/w49jy-mut` (`make mutation-copy … FULL=1`), one at a time, baseline first.

| # | Mutation | Instrument | Red? | Red output (abridged) | Restored |
|---|---|---|---|---|---|
| M0 | none (baseline) | ALR-05 guard, `TestThePartialUniqueIndexes`, the register-equality test, `test_role_register.py`, the walk | green | 29 passed; walk 0/0 | — |
| M1 | `api/routers/users.py` gains `from auditmanager.access.accounts import LAST_ADMIN` | ALR-05 guard; independent walk | **red; red** | `deep src/auditmanager/api/routers/users.py:37 auditmanager.access.accounts`; walk `deep 1` | `cmp` identical |
| M1b | same file gains `from auditmanager import access` | guard; walk | **red; red** | `package-root …users.py:37 auditmanager.access`; walk `package_root 1` | `cmp` identical |
| M2 | `ACCOUNT_REFERENCES` loses `expert_decision_event.author_user_uid` | `test_the_reference_register_equals_the_schema_foreign_keys_to_app_user` | **red** | `schema-only: [('expert_decision_event', 'author_user_uid', 'RESTRICT')]; register-only: []` | `cmp` identical |
| M3 | `0015` creates `uq_app_user_login` without `WHERE archived_at IS NULL` (whole-tree copy, so the migration is the copy's) | `TestThePartialUniqueIndexes` | **red** | `FAILED …test_an_archived_account_and_an_active_one_may_share_a_login` — `UniqueViolation … "uq_app_user_login"`; 1 failed, 3 passed | `cmp` identical |
| M4 | `OPERATION_ROLES["listUsers"]` `_ADMIN` → `_ANY_COMPLETE_ACCOUNT` | this judge's sweep; `test_role_register.py` | **red; red** | sweep `mismatches: 2` (`complete:none`, `complete:expert` → `listUsers` 200 where `role:admin` was due); test 4 failed, 19 passed | `cmp` identical |
| M5 | repair proof for F-1: `user_uid`, `request_id` appended to the two enums of `identifiers.schema.json` | jsonschema | turns **green** | 4 errors → 0 | `cmp` identical |

Each mutated run printed the copy's module path (`/root/w49jy-mut/src/auditmanager/…`) or the
copy's file in its red, so none of the reds came from the pristine tree. After M4 the final
unmutated sweep (C24) was green.

## 8. Untested questions

- **Real concurrency of the last-administrator rule** was not driven by this judge; it rests on
  code reading (lock order) and the repository's three threaded tests (C19). Through the API the
  actor is always a surviving complete administrator, so the rule is reachable only by the
  operator path or two administrators acting on each other at once.
- **A submission racing an approval of the same login** (submit's first check before the
  approval commits, second check after) could record a pending request for a login that is
  already active; its approval then answers `login_taken` and leaves it pending. Reasoned from
  the statements, not driven.
- **Migration cost on a large ledger.** `ALTER TABLE expert_decision_event ADD … FOREIGN KEY`
  validates every existing row under a share lock; measured only on empty and small databases.
- **The edge and the BFF** (`nginx.conf` rate limits, `guest-throttle.ts`, the BFF subject) are
  outside this entry point and were not exercised.
- **The frontend battery and the browser journey** were not run (`make gate` is not this
  judge's to run).

## 9. Own-pass verdict (provisional)

No release-blocking finding. One must-fix-before-merge (F-1: the revision-9 identifier catalog
does not validate against its own schema, and the domain README describes the schema pins
wrongly), six register items (F-2…F-7), one interpretation question (Q-1) for part two. Every
architecture and data-integrity property named in the task's deliverables holds at the subject
except the identifier catalog's schema validity.

---

# Part two — cross-examination and verdict

Written after the own pass was committed (`b9544d7`). Read for it, all at the subject unless
stated: `docs/program/dispatch/W49-PLAN.md` (whole); `docs/program/W49-ACCESS-01{a,b,c}.md`,
`W49-SEAL-01{a,b,c}.md`, `W49-DECISIONS-01.md`, `W49-EDGE-01.md`, `W49-BFF-01.md` (their risk,
limit and open-question sections); `W49-QA-01.md` from `agent/w49-qa-01` at `bcad663`; the
peer judge's `docs/program/reviews/W49-JUDGE-X.md` from `agent/w49-judge-x` at `fe20de3`
(its black-box pass `b24dc29` and its cross-examination). Both branches were read with
`git show <branch>:<path>`; no other worktree was opened.

## 10. Cross-examination

### 10.1 This pass's findings against the plan and the lane reports

| Own item | What the plan and the lanes say | Standing after cross-examination |
|---|---|---|
| **F-1** identifier catalog fails its schema | `W49-PLAN.md` §4 `W49-SEAL-01` grants the seal "the `candidate_revision` const in `contracts/domain/v1/*.schema.json`" and nothing else of those files. The seal then measured exactly this defect and stopped at its grant: `W49-SEAL-01c.md` §7.4 **Q12** ("`identifiers.schema.json` does not validate the revision-9 catalog … the proposed edit adds `user_uid` and `request_id` to both enums … outside grant (e), which is the const only, so it is not edited"), committed in `220638d` at 05:44, after the integrator's last settlement of the seal's questions (`addbe6c`, 05:28). It was merged in `2a31edf` unsettled, and `contracts/domain/v1/README.md` still carries the seal's *earlier* statement (schemas pin 8). | **Upheld, must-fix-before-merge.** Not a new discovery — an open question the slot owner raised, measured and could not close, that reached the merged candidate as a caveat rather than a stop (`OPERATING_CONSTRAINTS.md` §12, sixth shape: "a stated non-measurement was passed along as a caveat instead of being treated as a blocker" — here a stated *defect*). This pass's contribution is the independent reproduction, the README contradiction, the base comparison (0 errors at `23e0579`) and the repair proof (M5). The plan's own entry condition ("contract set measured at the base") and the README's verification block both presuppose a catalog that validates. |
| **F-2** live schema comment / `0009` log instruct `access.name` | `W49-SEAL-01c.md` §4 item 7 lists the remaining references to the deleted module, "migration `0009`'s comments name it (migrations are forbidden)". The plan's task for ACCESS-01a owned migration `0015` and could have re-commented the column; nobody did. | **Upheld, register.** The lane saw the source comments; this pass adds that the *live* `COMMENT ON COLUMN app_user.display_name` instructs the removed command and states a login bound `0015` made false. Repair is a later migration's `COMMENT ON COLUMN`. |
| **F-3** `name_label` exceeds 66 | Plan §3.1: "`display_label` is 'Фамилия И. О.' (at most 66 characters)"; `W49-SEAL-01c` pinned `RegistrationRequest.display_label` `maxLength: 66`. No lane mentions multi-character upper-case initials. | **Upheld, register.** The plan's own bound is the claim falsified; `author_label` (128) is unaffected. |
| **F-4** unused `account_standing` | `W49-ACCESS-01b.md` §5 told the seal to wire `account_standing`; `W49-SEAL-01c.md` §4 item 4 records that it read `get_account` instead ("Both are one statement"). | **Upheld, register** — known to the seal; what remains is the dead method and a comment calling it the per-request read. |
| **F-5** docstrings contradicting the code | The rejected-applicant question was ruled (`R-56` addendum, plan §3.3); the peer judge independently reports the same documentation lag (`W49-JUDGE-X.md` §5.4). The `complete_profile` code and the `update_account` sentence are not discussed by any lane. | **Upheld, register.** |
| **F-6** archived targets | Plan §3.4: `updateUser` "names, roles; invariants of §3.2" — silent on archived accounts; `archiveUser`/`purgeUser`/`restoreUser` define their archived behaviour. No lane discusses it. | **Upheld, register.** No standing consequence; a restore brings back whatever roles an administrator set meanwhile, which may be intended. A one-line ruling would settle it. |
| **F-7** `errors.py` imports `sqlalchemy.exc` | Pre-existing; not in any W49 grant. | **Upheld, register (information).** |
| **Q-1** "with any role" | Plan §3.2: `OPERATION_ROLES` is any-of and "the empty set means any active, complete account"; reads, `getMe`, `updateMyProfile`, `changePassword` → `∅` (`R-60`). The contract text says the same. | **Closed — no finding.** The plan read `R-60`'s "with any role" as "whatever its roles, none included", the code and the contract follow the plan, and the sweep measured the served behaviour. A roleless complete account reads every product read; if the owner meant "at least one role", that is a one-line register change and a re-sweep, and W51's user screens are where a roleless account first becomes visible. Noted for `W49-INT-CLOSE`, not raised as a defect. |

### 10.2 The plan's claims this pass can check, against its measurements

- §3.1 "`standing_of` returns no standing for an archived account": the adapter returns a
  standing with `archived=True` and the seam refuses it; the outcome is the generic
  `authentication_required` either way (C9, archived standing with a current-epoch credential).
  A wording difference, not a behaviour one.
- §3.1 "`uq_app_user_login` becomes a partial unique index"; the reference register "a test
  enumerates the schema's foreign keys … and asserts equality" — measured (§5.5, §5.6, M2, M3).
- §3.2 "the empty set means any active, complete account", the order of evaluation, the three
  registers — measured over the real composition root (§5.8, 342/0) and shown able to fail (M4).
- §3.2 "Any role change, archive, restore, purge or administrator reset bumps `token_epoch`":
  purge deletes the row instead (`accounts.py` module docstring says so); the effect on
  credentials is the same. Not a finding.
- §3.3 "Approval creates the account in the same transaction under `FOR UPDATE`" — measured by
  fault injection (§5.9, C11) and by the concurrent-approval probe (§5.5).
- §3.6 "the contract, the registers and the routers land in one slot" — measured (§5.7).
- §4 `W49-ACCESS-01a` required tests "upgrade from a `0014` database holding the seeded `admin`
  with a changed password **and** from one holding a legacy non-e-mail test login" — reproduced
  independently with the W48 code writing the `0014` rows (§5.4), not only with the lane's
  fixtures.
- §7 stop conditions in this lane's scope ("a refusal is computed in a router or a schema
  validator instead of `access`"; "the sweep finds an operation outside every register"): neither
  occurred (§5.1, §5.2, §5.8).

### 10.3 The peer judge (`W49-JUDGE-X`)

- **Agreement on the register.** Its 34-operation sweep and 4×2×2 matrix (black box, served
  stand) and this pass's 9-standing sweep (real composition root, archived standing isolated
  from the epoch) reach the same answer by different routes: no operation outside a register,
  no escalation. The two are independent instruments; together they cover the seam's logic and
  the standing adapter.
- **B-1 (release-blocking for the live deployment — the proxy keeps serving the old
  `nginx.conf`).** Outside this entry point, but its mechanism has a data-path half this judge
  could check without starting anything. Measured here: `git checkout --detach` (the deploy
  workflow's step, `.github/workflows/deploy-auto.yml:105`) **replaces** a tracked file with a new
  inode — with the old file held open, the held inode was `145877` and still read `one`, while the
  path's inode became `145911` and read `two` (git 2.43.0, scratch repository). Read in the tree:
  the proxy mounts `./proxy/nginx.conf` as a single file (`infra/deploy/compose.server.yml:260`),
  `deploy.sh` keeps the proxy container across deploys (its own header, measured by
  `W23-DEPLOY`), and `reload-proxy.sh:70` only runs `nginx -s reload` inside it. The Docker half
  (a single-file bind mount stays on the inode it was started with) was **not** measured here:
  available memory was 1 GB when this was examined, under the brief's 2 GB floor for starting
  anything. On that basis this judge **concurs** with B-1 and with its scope: it does not block the
  `integration/w49` merge or the `origin/dev` publication; it blocks publishing W49 to the live
  host until the proxy is recreated on a proxy-file change and the deployed check probes the
  throttle. It also predates W49 (any earlier `nginx.conf` change, e.g. `1f723db`, met the same
  path); W49 is the first wave whose new *control* lives there.
- **Its R-1…R-5** are edge, enumeration and BFF items outside this entry point; nothing here
  contradicts them. Its §5.4 (the ACCESS-01c "open question" is a documentation lag on a ruled
  behaviour) is the same observation as this pass's F-5, reached independently.
- **What this pass has that the peer did not check:** F-1 (catalog schema validity), F-2
  (live schema comment), F-3 (label bound), F-6 (archived targets), the upgrade paths over
  W48-written rows, approval atomicity under fault injection, and the reference register against
  `pg_constraint`.

### 10.4 QA (`W49-QA-01`)

- **QA Q-1 (a pending applicant's brake is spent twice per BFF sign-in attempt).** Confirmed by
  reading: `access/repository.py` `authenticate` runs `_NOTE_A_FAILED_REQUEST_ATTEMPT` for a
  login no active account holds, `access/registrations.py` `read_status` counts its own refusal,
  and the BFF calls both for one failed sign-in. It is the plan's §3.3 sentence ("the request's
  throttle columns count both kinds of attempts") composed with §3.5. From the data side this
  judge adds one fact to QA's: the exchange never compares the pair with the request's digest,
  so the exchange-side count guards no secret of the request and only spends the applicant's
  allowance. **Register**, for a ruling; not release-blocking (the request's brake gates only the
  `pending` sentence, never an account).
- **QA Q-2 (last administrator reachable through the API only as a race)** is the same
  conclusion as this pass's §8 first bullet and `W49-SEAL-01c.md` §4 item 11. No finding.
- QA records no finding; nothing in its twelve items contradicts a measurement here.

## 11. Verdict

**PASS for the architecture and data-integrity entry point, conditional on F-1 being repaired
before the candidate is merged and published.**

- **Release-blocking (this lane):** none. Routers carry no SQL and no rule; every §3.2 invariant
  is raised in `access` and refused again by the database where the schema can; ALR-05 reads
  0 / 0 by two instruments; `0015` applies to an empty database and over both `0014` shapes the
  W48 code writes; the partial unique indexes, the registration guard and the reference register
  hold and are each shown able to fail; the reseal landed in one slot; the served application
  equals the registers; approval is one transaction; `KNOWN_OUTSTANDING_CLAIMS` is empty and
  every pin is live.
- **Concurrence with the peer:** `W49-JUDGE-X` **B-1** is upheld as release-blocking for the
  **live deployment only** (`origin/main` / the alpha host), not for the merge or `origin/dev`.
- **Must-fix-before-merge:** **F-1** — `contracts/domain/v1/identifiers.schema.json` must admit
  `user_uid` and `request_id` in its two identifier enums (M5 proves that is sufficient), and
  `contracts/domain/v1/README.md:8-10` and `:753` must stop saying the schemas pin `8`. It is a
  `contracts/**` edit, so it needs the contract slot's owner; the integration contract reserves
  `W49-FIX` for release-blocking findings, so the integrator chooses the vehicle.
- **Register:** F-2, F-3, F-4, F-5, F-6, F-7 (this pass); QA Q-1 (double brake, for a ruling);
  Q-1 of this pass noted for `W49-INT-CLOSE` (the permissive reading of `R-60` is what ships).
- **Untested** (§8): real concurrency of the last-administrator rule beyond the repository's
  threaded tests; the submit/approve race on one login; migration cost on a large ledger; the
  edge, the BFF, the frontend battery and the browser journey; the Docker half of B-1.

---

## Appendix A — the probes

The probes ran from the session scratchpad, which does not survive a restart, so their
load-bearing parts are kept here. No password appears: every probe password was generated at
run time (`openssl rand`/`secrets`) and never printed; the seed's `password` is the published
constant of migration `0006`. Run each from the worktree with the lane's `.env` loaded
(`set -a; . ./.env; set +a`), `PYTHONPATH=src`, `PYTHONDONTWRITEBYTECODE=1`, and `DATABASE_URL`
pointed at a disposable database of the lane (`CREATE DATABASE jy_…` then
`.venv/bin/python -m alembic --config db/migrations/alembic.ini upgrade head`).

### A.1 Independent ALR-05 walk (`.venv/bin/python walk.py <repo-root>`)

```python
"""Independent ALR-05 walk (W49-JUDGE-Y). Written without reusing the guard's code.

Resolves every import (absolute, relative, `from auditmanager import X`, import_module /
__import__ string literals) in src/auditmanager/<A>/** to a dotted target and classifies a
target in another context B (B != A, B != shared) as:
  public        auditmanager.B.public  (or `from auditmanager.B import public`)
  package-root  auditmanager.B itself, or `from auditmanager.B import <name != public>`
  deep          anything below auditmanager.B other than .public exactly
Importers under bootstrap/ (composition root) are counted separately, not exempted silently.
"""
import ast, sys, importlib.util, json
from pathlib import Path

root = Path(sys.argv[1]) / "src" / "auditmanager"
contexts = sorted(p.name for p in root.iterdir() if p.is_dir() and p.name != "__pycache__")
counts = {"deep": [], "package-root": [], "public": 0, "bootstrap-cross": 0, "shared-to-context": [], "dynamic": []}

def modname(path):
    rel = path.relative_to(root.parent)
    parts = list(rel.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)

def classify(importer_ctx, target, names, path, line):
    p = target.split(".")
    if p[0] != "auditmanager" or len(p) < 2:
        return
    if len(p) == 1:
        return
    b = p[1]
    if b not in contexts:
        return
    if b == importer_ctx:
        return
    if importer_ctx == "shared":
        counts["shared-to-context"].append(f"{path}:{line} {target}")
        return
    if importer_ctx == "bootstrap":
        counts["bootstrap-cross"] += 1
        return
    if b == "shared":
        return
    if len(p) == 2:
        # `from auditmanager.B import names` or `import auditmanager.B`
        if names is not None and all(n == "public" for n in names):
            counts["public"] += 1
        else:
            counts["package-root"].append(f"{path}:{line} {target} {names}")
    elif len(p) == 3 and p[2] == "public":
        counts["public"] += 1
    else:
        counts["deep"].append(f"{path}:{line} {target}")

for path in sorted(root.rglob("*.py")):
    rel = path.relative_to(root)
    if len(rel.parts) < 2:
        continue
    ctx = rel.parts[0]
    mod = modname(path)
    pkg = mod if path.name == "__init__.py" else mod.rpartition(".")[0]
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                classify(ctx, a.name, None, rel, node.lineno)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = importlib.util.resolve_name("." * node.level + (node.module or ""), pkg) if node.module else importlib.util.resolve_name("." * node.level, pkg)
            else:
                base = node.module or ""
            names = [a.name for a in node.names]
            if base == "auditmanager":
                for n in names:
                    classify(ctx, f"auditmanager.{n}", None, rel, node.lineno)
            else:
                classify(ctx, base, names, rel, node.lineno)
        elif isinstance(node, ast.Call):
            f = node.func
            fname = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else "")
            if fname in ("import_module", "__import__") and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                counts["dynamic"].append(f"{rel}:{node.lineno} {node.args[0].value}")
                classify(ctx, node.args[0].value, None, rel, node.lineno)

print(json.dumps({"contexts": contexts, "deep": len(counts["deep"]), "package_root": len(counts["package-root"]),
                  "public_imports": counts["public"], "bootstrap_cross_context": counts["bootstrap-cross"],
                  "shared_to_context": counts["shared-to-context"], "dynamic_literal_imports": counts["dynamic"],
                  "deep_list": counts["deep"], "package_root_list": counts["package-root"]}, indent=1))
```

### A.2 Upgrade paths (C7)

```bash
# per database: CREATE DATABASE; alembic upgrade 0014_durable_analysis_effects; seed with the W48 code; alembic upgrade head
git archive 23e0579 src | tar -x -C "$BASE"            # the W48 closure's own access code
# A: the seed changes its password through the W48 repository, at 0014
PYTHONPATH="$BASE/src" python -c '... UserRepository().change_password(s, user_uid=<admin>, current_password="password", new_password=<disposable>); s.commit()'
# B: two legacy non-e-mail logins created through the W48 repository, at 0014
PYTHONPATH="$BASE/src" python -c '... for login in ("reviewer.one", "qa_2-x"): UserRepository().create_user(s, login, <disposable>); s.commit()'
# both: alembic upgrade head with the subject's tree, then
psql -Atc "select login, is_default_credential, profile_completed_at is null, token_epoch,
           (select string_agg(role, ',' order by role) from app_user_role r where r.user_uid=u.user_uid) from app_user u"
```

### A.3 After-upgrade journeys (C8)

Through `TestClient(create_asgi_app(env))` with a random `AUDITMANAGER_API_TOKEN`: sign in with
the legacy login → `GET /me` → `GET /projects`, `GET /users` → `PATCH /me` without `email` →
raw `UPDATE app_user SET last_name, first_name, profile_completed_at=now() WHERE login=<legacy>`
(expect `23514 ck_app_user_login_format`) → `PATCH /me` with names and an e-mail → sign in with
the legacy login (401) and with the e-mail (200) → `GET /projects`, `GET /users` →
`PATCH /me` with another e-mail (422 `field: login`).

### A.4 The served-application sweep (C9, C24, M4)

Standings are built through the API (`changePassword`, `PATCH /me`, `submitRegistration` +
`approveRegistration`, `PATCH /users/{uid}` with `roles: []`, `resetUserPassword`,
`archiveUser`) and the operator path (`UserRepository.create_user` + `AccountRepository.grant_role`
for the two legacy accounts). The archived standing's credential is minted with
`build_signer(env).issue(Subject(..., token_epoch=<current epoch>))`. Routes are enumerated from
the served application, recursing into FastAPI's `_IncludedRouter.original_router.routes`;
path identities are `<prefix>_01M2545JSD15ETSNNV904X991F` (nonexistent); bodies are `{}`.

```python
OPEN = {"issueToken", "submitRegistration", "readRegistrationStatus"}
READS = {"listProjects","listDocuments","getDocumentVersion","streamDocumentVersionContent","getVersionBlocks",
         "listVersions","listRuns","getRunStatus","listRunFindings","getFinding","listDecisionHistory","listDecisions",
         "getDashboardSummary"}
OWN = {"getMe", "updateMyProfile", "changePassword"}
MUT = {"createProject","uploadDocument","startRun","appendDecision","exportRunCsv"}
MGMT = {"listRegistrations","approveRegistration","rejectRegistration","listUsers","getUser","updateUser",
        "archiveUser","restoreUser","purgeUser","resetUserPassword"}
DEFAULT_REACH = {"changePassword", "getMe"}                         # R-50 (+ getMe); issueToken is OPEN
INCOMPLETE_REACH = {"getMe", "updateMyProfile", "changePassword"}   # R-59: the way out

def expected(standing, op):        # standing like "complete:default:expert+admin"
    if op in OPEN: return "pass"
    if standing == "anonymous" or standing.startswith("archived"): return "A"
    parts = standing.split(":"); complete = parts[0] == "complete"; default = "default" in parts
    roles = frozenset(x for x in parts[-1].split("+") if x in ("expert", "admin"))
    if default and op not in DEFAULT_REACH: return "D:password_changed"
    if not complete and op not in INCOMPLETE_REACH: return "D:profile_completed"
    if op is None or op in READS or op in OWN: return "pass"           # R-60 as the seam reads it (Q-1)
    if op in MUT: return "pass" if "expert" in roles else "D:role:expert"
    if op in MGMT: return "pass" if "admin" in roles else "D:role:admin"
    return "D:"

def observe(r):   # 401 authentication_required -> "A"; 403 permission_denied -> "D:<required_capability>"; else "pass"
    body = r.json() if r.content else {}
    if r.status_code == 401 and body.get("error_code") == "authentication_required": return "A"
    if r.status_code == 403 and body.get("error_code") == "permission_denied":
        return "D:" + str((body.get("details") or {}).get("required_capability", ""))
    return "pass"
```

### A.5 Partial unique, purge, guard, concurrency (C10)

`U1` submit L → `U2` submit `L.upper()` (409 `request_pending`) → approve → `U3` submit L
(409 `login_taken`) → `U4` archive the holder → `U5` submit L (201) → approve → `U6`
`select count(*), count(*) filter (where archived_at is null) from app_user where login=L`
(2, 1) → `U7` restore the first (409 `login_taken`) → `U8` raw `update app_user set
archived_at=NULL, archived_by=NULL` on the first (`23505 uq_app_user_login`) → `U9` two raw
pending inserts for one login (`23505 uq_registration_request_pending_login`) → `P1` purge the
active holder (409 `state_transition_not_allowed`) → `P2` purge the archived one (204) → `P3` its
request (`approved`, `created_user_uid` NULL) → `P4/P5` archive and purge an administrator who
decided requests (409 `account_referenced`) → `P6` restore → `G1–G3` raw NULL of
`created_user_uid`, DELETE, second decision (refused `AM003`, `AM003`, `AM001`) → `C1` two
threads approve one request (`[200, 409]`, one account).

### A.6 Approval atomicity (C11)

```sql
CREATE FUNCTION jy_fail_approval() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN IF NEW.status = 'approved' THEN RAISE EXCEPTION 'judge-y probe: the decision UPDATE fails'; END IF; RETURN NEW; END $$;
CREATE TRIGGER jy_fail_approval BEFORE UPDATE ON registration_request FOR EACH ROW EXECUTE FUNCTION jy_fail_approval();
-- POST /registrations/{id}/approve  Idempotency-Key: K  {"roles": ["expert","admin"]}   -> 500 internal_error
select count(*) from app_user where login = :l;                                            -- 0
select count(*) from app_user_role r join app_user u using (user_uid) where u.login = :l;  -- 0
select status, password_hash is not null from registration_request where request_id = :r;  -- (pending, true)
select count(*) from command_record where idempotency_key = :K;                            -- 0
DROP TRIGGER jy_fail_approval ON registration_request; DROP FUNCTION jy_fail_approval();
-- the same request with the same key -> 200 approved; one account
```

### A.7 Reference register against the schema (C12)

```python
rows = cx.execute(text("""
  select c.conrelid::regclass::text, a.attname, c.confdeltype, array_length(c.conkey,1),
         (select attname from pg_attribute where attrelid=c.confrelid and attnum=c.confkey[1])
  from pg_constraint c join pg_attribute a on a.attrelid=c.conrelid and a.attnum=c.conkey[1]
  where c.contype='f' and c.confrelid='app_user'::regclass""")).all()
ACTION = {"r": "RESTRICT", "n": "SET NULL", "c": "CASCADE", "a": "NO ACTION", "d": "SET DEFAULT"}
schema = {(t, col, ACTION[act]) for t, col, act, n, ref in rows}           # every key single-column, to user_uid
register = {(r.table, r.column, r.on_delete) for r in ACCOUNT_REFERENCES}  # auditmanager.access.public
assert schema == register
```

### A.8 Edge probes (C23)

`E1` `PATCH /users/<self>` `{"names": {...}, "roles": ["expert"]}` as the only-self administrator
(403) then `GET /me` (names unchanged); `E2` `PATCH /users/<archived>` `{"roles": ["expert"]}`
(200, roles now `[expert]`); `E3` `PATCH /users/<archived>` `{"names": {...}}` (200);
`E3b` `POST /users/<archived>/password` (404); `E5` `POST /registrations` with
`last_name="A"*60, first_name="ßabc", middle_name="ßabc"` (201), then the item's
`display_label` from `GET /registrations?status=pending` (length 68).
