# W49-ACCESS-01a — migration `0015`, the schema, the reference register, two operator commands

**Task:** `docs/program/tasks/W49-ACCESS-01.md` (part a of three; one owner, three reports).
**Base:** `dff1922` (`integration/w49`, the W49 freeze). **Branch:** `agent/w49-access-01`.
**Plan:** `docs/program/dispatch/W49-PLAN.md` §3.1–§3.3, §3.6, §4 `W49-ACCESS-01a`.
**Lane:** `FOUNDATION_INSTANCE=gate-w49access`, Postgres `56550`, S3 `60150`/`60151`,
database `auditmanager_w49access`, bucket `auditmanager-w49access` — ports confirmed free
with `ss -ltn` before `make foundation` (no listener on any of the three).

## Premise re-measured

```text
$ PYTHONPATH=src .venv/bin/alembic -c db/migrations/alembic.ini heads     # at dff1922
0014_durable_analysis_effects (head)
```

Baseline at `dff1922` before any edit, same lane:
`.venv/bin/python -m pytest tests/integration/db tests/integration/p02_journey tests/contract/api_v1/test_doc_prose_facts.py tests/integration/access -q`
→ `357 passed, 1 warning in 209.04s`, exit 0.

## What 01a delivers

- **`db/migrations/versions/20261005_0015_accounts_roles_registration.py`**, revision
  `0015_accounts_roles_registration`:
  - `app_user`: `last_name`, `first_name`, `middle_name` (each NULL or 1..60, letters
    separated by single space/hyphen/apostrophe), `profile_completed_at` (NULL for every
    existing row), `archived_at`/`archived_by` (both or neither, never self, RESTRICT FK);
    `ck_app_user_login_format` replaced; `uq_app_user_login` is now a partial unique index
    `WHERE archived_at IS NULL`; `ck_app_user_complete_profile_has_names`.
  - `app_user_role (user_uid, role, granted_at, granted_by)`, PK `(user_uid, role)`,
    `role IN ('expert','admin')`, `user_uid` CASCADE, `granted_by` RESTRICT.
  - `registration_request` with every column of §3.3 plus the three throttle columns named
    as on `app_user`; `ck_registration_request_decision_shape`; partial unique
    `uq_registration_request_pending_login`; `decided_by` RESTRICT, `created_user_uid`
    SET NULL.
  - `am_guard_registration_request()` / `trg_registration_request_guard` (BEFORE INSERT OR
    UPDATE OR DELETE): permits insertion only as `pending`; throttle-only updates in any
    state; exactly one decision `pending → approved | rejected` that nulls the four password
    columns, names the created account on approval and rewrites nothing else; and the
    nulling of `created_user_uid` **only from the purge cascade** (`pg_trigger_depth() > 1`).
    Everything else — second decision (`AM001`), password write after the decision,
    manual `created_user_uid` update, DELETE (`AM003`) — is refused.
  - `expert_decision_event.author_user_uid`: nullable, `ON DELETE RESTRICT`, format CHECK,
    partial index. Column only; the writer is `W49-DECISIONS-01`.
  - Backfill: every account `expert`; the row `login = 'admin'` also `admin`; without such a
    row the upgrade succeeds and the deployment log says `NO ACCOUNT HOLDS THE ROLE 'admin'`
    and names `python -m auditmanager.access.grant`.
  - Downgrade refuses while `app_user_role` or `registration_request` hold rows, and while
    any value the `0014` shape cannot hold exists (names, completed profile, archive, e-mail
    login, authored decision). **`0015` is forward-only in practice: after the backfill every
    real database refuses, and the rollback of W49 is a database restore.** On an empty tree
    (role rows removed) it runs and restores `UNIQUE (login)` and the legacy login CHECK.
- **`src/auditmanager/access/references.py`** — the written register `ACCOUNT_REFERENCES`
  (4 RESTRICT, 1 SET NULL, 1 CASCADE) and `restricting_references()`.
- **`src/auditmanager/access/models.py`** — `EMAIL_LOGIN_PATTERN` (ASCII, ≤254),
  `normalize_email`, `normalize_login` (accepts the e-mail or the legacy shape),
  `normalize_person_name` (≤60, NFC, zero-width removed, no mixed Cyrillic/Latin word),
  `name_label`, `ROLES`/`parse_role`, `RegistrationId` (`reg_<ULID>`, outside the shared
  registry like `usr`), and `UserRecord` widened with six defaulted fields. The name rules
  land here rather than in 01b because the profile command needs them; 01b adds their
  exhaustive tests and the `display_label` precedence tests.
- **`src/auditmanager/access/repository.py`** — `_PUBLIC_COLUMNS`/`_record` carry the six new
  columns; every statement addressed **by login** is restricted to `archived_at IS NULL`
  (a login is unique only among active accounts now); `credential_standing` answers `None`
  for an archived account (§3.1: no standing).
- **`src/auditmanager/access/accounts.py`** — `AccountRepository` with `roles_of`,
  `complete_profile` (one UPDATE, `R-59`) and `grant_role` (epoch bump when the set
  changes). 01b/01c extend it.
- **CLIs** `python -m auditmanager.access.profile` and `python -m auditmanager.access.grant`
  (exit 0/1/2 as `access.name`).
- **`src/auditmanager/access/public.py`** — the ALR-05 public surface (grows in 01b/01c).
- **Head pins (§3.6):** the pin line in `tests/contract/api_v1/test_doc_prose_facts.py`, the
  `migration-application-head` row in `docs/program/CONTRACT_PIN_REGISTRY.md`, the one live
  head sentence in `docs/program/CURRENT_STATE.md` (line 66–67) and in
  `docs/manual-tests/PC-01_prototype.md` (line 39) — each one line, value only.
- **Schema pins:** `EXPECTED_TABLES` (`test_migration_lifecycle.py`), `P02_TABLES`
  (`journey.py`), `NON_CONTRACT_IDENTITY_COLUMNS` (`test_schema_shape.py`; `request_id`,
  `created_user_uid`, `author_user_uid`, asserted instead in the new test), the closed field
  set in `test_app_user_repository.py`, and `EXPECTED_INVENTORY` resealed with the reviewed
  delta written beside it (columns +29, relations +2, constraints +33, indexes +11,
  triggers +1, functions +1; views, extensions, sequences, policies, state topology
  unchanged).
- **Earlier-revision downgrade tests** (`test_app_user_migration.py`,
  `test_reviewer_display_name.py`, `test_run_terminal_detail_schema.py`,
  `test_downgrade_never_loses_a_measurement.py`, `test_durable_analysis_effects.py`,
  `test_norm_embeddings_migration.py`) now call `conftest.clear_the_role_backfill(url)` first:
  without it they would measure `0015`'s refusal instead of their own revision's, and the two
  that assert "downgrade refused" would pass on the wrong refusal.

## 1. Changed files (01a)

```text
db/migrations/versions/20261005_0015_accounts_roles_registration.py   (new)
docs/manual-tests/PC-01_prototype.md                                   (one head sentence)
docs/program/CONTRACT_PIN_REGISTRY.md                                  (head row needle)
docs/program/CURRENT_STATE.md                                          (one head sentence)
docs/program/W49-ACCESS-01a.md                                         (this report)
src/auditmanager/access/accounts.py                                    (new)
src/auditmanager/access/grant.py                                       (new)
src/auditmanager/access/models.py
src/auditmanager/access/profile.py                                     (new)
src/auditmanager/access/public.py                                      (new)
src/auditmanager/access/references.py                                  (new)
src/auditmanager/access/repository.py
tests/contract/api_v1/test_doc_prose_facts.py                          (head pin line)
tests/integration/db/conftest.py
tests/integration/db/test_accounts_migration.py                        (new)
tests/integration/db/test_accounts_operator_commands.py                (new)
tests/integration/db/test_app_user_migration.py
tests/integration/db/test_app_user_repository.py
tests/integration/db/test_downgrade_never_loses_a_measurement.py
tests/integration/db/test_durable_analysis_effects.py
tests/integration/db/test_migration_lifecycle.py
tests/integration/db/test_norm_embeddings_migration.py
tests/integration/db/test_reviewer_display_name.py
tests/integration/db/test_run_terminal_detail_schema.py
tests/integration/db/test_schema_invariant_inventory.py
tests/integration/db/test_schema_shape.py
tests/integration/p02_journey/journey.py                               (P02_TABLES only)
```

## 2. Checks run (tree: the working tree committed as 01a, before this report was added)

| Command | Result |
| --- | --- |
| `PYTHONPATH=src .venv/bin/alembic -c db/migrations/alembic.ini upgrade head` (lane DB) | `0014 -> 0015`, logs both backfill lines, exit 0 |
| `.venv/bin/python -m pytest tests/integration/db tests/integration/p02_journey tests/contract/api_v1/test_doc_prose_facts.py -q` (the 01a required command) | `352 passed, 1 warning in 259.17s`, exit 0 |
| `.venv/bin/python -m pytest tests/contract/architecture/test_alr05_boundaries.py tests/integration/access tests/contract/domain_p02/test_identifier_catalog.py -q` | `98 passed`, exit 0 |
| `git diff --check` | clean |

Note on the lane: `tests/integration/p02_journey` reads the lane's long-lived database
(`DATABASE_URL`), which `make foundation` had migrated to `0014` at the base. A first run
before `alembic upgrade head` on that database failed 12 journey tests with
`column "last_name" does not exist` — a lane at the old head, not a defect; `make gate`
migrates before its battery. All figures above are after the lane upgrade.

### Mutations (every new guard shown red)

Run in a full copy built by `make mutation-copy MUT=/root/w49access-788b07cb-mut FULL=1`
(migrations mutable; `auditmanager.__file__` resolves under the copy). The unmutated copy
was baselined first: `./.venv/bin/pytest tests/integration/db/test_accounts_migration.py
tests/integration/db/test_accounts_operator_commands.py -q` → `60 passed`. Each mutation was
applied alone, `__pycache__` cleared, `PYTHONDONTWRITEBYTECODE=1`, then restored.

| id | mutation | red test | evidence |
| --- | --- | --- | --- |
| M01a-1 | drop `expert_decision_event.author_user_uid` from `ACCOUNT_REFERENCES` | `test_the_reference_register_equals_the_schema_foreign_keys_to_app_user` | `schema-only: [('expert_decision_event', 'author_user_uid', 'RESTRICT')]` — 1 failed |
| M01a-2 | `fk_app_user_role_granted_by` → `ON DELETE SET NULL` in the migration | same | `schema-only: [('app_user_role', 'granted_by', 'SET NULL')]; register-only: [(… 'RESTRICT')]` — 1 failed |
| M01a-3 | remove `AND pg_trigger_depth() > 1` from the guard | `test_a_manual_created_user_uid_update_is_refused[to-null]` | `DID NOT RAISE DBAPIError` — 1 failed |
| M01a-4 | guard returns instead of raising on a status change | `test_a_second_decision_is_refused[rejected-then-approved]` | `DID NOT RAISE DBAPIError` — 1 failed |
| M01a-5 | guard returns instead of raising "immutable apart from its one decision" | `test_a_password_column_write_after_the_decision_is_refused[approved]` | `assert '23514' == 'AM003'` (only the CHECK caught it) — 1 failed |
| M01a-6 | `uq_app_user_login` without `WHERE archived_at IS NULL` | `test_an_archived_account_and_an_active_one_may_share_a_login` | `UniqueViolation … "uq_app_user_login"` — 1 failed |
| M01a-7 | `uq_registration_request_pending_login` without its predicate | `test_a_decided_request_and_a_pending_one_may_share_a_login` | `UniqueViolation … "uq_registration_request_pending_login"` — 1 failed |
| M01a-8 | login CHECK accepts a legacy login regardless of completion | `test_a_legacy_login_is_accepted_only_while_the_profile_is_incomplete` | `DID NOT RAISE DBAPIError` — 1 failed |
| M01a-9 | backfill grants no `admin` | `test_the_backfill_gives_the_seed_both_roles_and_leaves_it_a_legacy_account` | `[('admin', 'expert', None)] == [('admin', 'admin', None), …]` — 1 failed |
| M01a-10 | downgrade never refuses | `TestTheDowngrade::test_it_refuses_while_the_backfill_is_there` | `assert 0 != 0` (downgrade exited 0) — 1 failed |
| M01a-11 | `grant_role` without the epoch bump | `TestTheGrantCommand::test_a_grant_that_changes_the_set_revokes_and_one_that_does_not_does_not` | `assert 1 == (1 + 1)` — 1 failed |
| M01a-12 | profile completion writes `profile_completed_at = NULL` | `test_it_completes_the_seed_in_one_statement_and_changes_nothing_else` | `assert None is not None` — 1 failed |

## 3. Contracts

No file under `contracts/**` changed. The migration head moved from
`0014_durable_analysis_effects` to `0015_accounts_roles_registration` (the enumerator this
task owns, `db/migrations/versions/`; totality query prints exactly one head). Domain
contract revision 8 / 27 identities, API 17 / 20 / 61 and the 22-code catalog are untouched;
`usr` and `reg` stay outside `identifiers.json` and the shared registry until `W49-SEAL-01a`.

## 4. Risks and known limitations

- **Forward-only.** `0015`'s downgrade refuses on every database the backfill touched; the
  W49 rollback is a database restore (as the plan says; to be registered at INT-CLOSE).
- **Login CHECK is narrower than the plan's sentence.** §3.1 says "an e-mail shape, or
  `profile_completed_at IS NULL`"; the CHECK is "an e-mail shape, or (`profile_completed_at
  IS NULL` **and** the `0006` legacy shape)" so raw SQL still cannot store `Admin` beside
  `admin` (M01a-8 proves the narrower arm is enforced). It never accepts what the plan's
  reading would refuse.
- **E-mail is ASCII-only** (`xn--` for internationalised domains); a decision the plan did
  not state explicitly — listed as an open question in the hand-back.
- The mixed-script name rule is enforced in `access` only; the database CHECK restates the
  letter/separator shape, not the per-word script rule.
- The `author_user_uid` reference case in `test_accounts_migration.py` inserts a decision
  event with foreign-key enforcement skipped for that one transaction
  (`SET LOCAL session_replication_role = replica`, lane superuser) to avoid seeding a whole
  run; the DELETE it measures runs normally.

## 5. Instructions to the integrator

- Lanes that run `tests/integration/p02_journey` against a long-lived database must be at
  head (`make foundation`/`make gate` migrate first).
- `W49-DECISIONS-01` can write `expert_decision_event.author_user_uid` from 01a on.
- `W49-SEAL-01` should import only from `auditmanager.access.public` outside `bootstrap`.

## 6. Forbidden hotspots

No path outside the task's `allowed_paths` is touched: `git diff --name-only dff1922` lists
only the files in §1. No `contracts/**`, no `src/auditmanager/{api,bootstrap,decisions}/**`,
no `web/**`, no lock file, no ref, tag or push. The four integrator-owned documents change by
exactly the head value in the one sentence or row the task file grants.
