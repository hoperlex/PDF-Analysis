# Database migrations

One migration head owner per wave. Use forward migrations and expand→backfill→switch→contract for incompatible changes. A `down` file is not a substitute for data recovery. Migration tests must cover clean install, supported upgrade, and safe re-run/backfill behavior.

## Current head

| Revision | Parent | What it creates |
|---|---|---|
| `0001_baseline` | — | nothing. The empty, migrated P01 baseline (FF-01 §4 approves no product table) |
| `0002_pc01_schema` | `0001_baseline` | the complete PC-01 schema: 15 tables, 1 view, 5 trigger functions |
| `0003_open_items` | `0002_pc01_schema` | three owner-ruled corrections: the blob index comment, `model_call.status` widened to admit `truncated`, a CHECK on `ungrounded_reason` |
| `0004_cost_basis` | `0003_open_items` | `model_call.cost_basis` — whether `cost_micros` was measured or derived |
| `0005_truncated_call_status` | `0004_cost_basis` | the two invariants that give `truncated` content: it carries a response checksum and no error code |
| `0006_app_user` | `0005_truncated_call_status` | `app_user`: a login, a salted PBKDF2-SHA256 digest with its parameters, and one seeded account (`admin`) flagged `is_default_credential` |
| `0007_credential_epoch` | `0006_app_user` | `app_user.token_epoch` and `token_epoch_updated_at`: the generation of credentials an account accepts, so raising it by one revokes every credential that account holds |
| `0008_sign_in_throttle` | `0007_credential_epoch` | **head** — `app_user.failed_sign_ins`, `last_failed_sign_in_at` and `sign_in_blocked_until`: consecutive recent failed sign-ins, and the instant before which this account's password is not consulted at all. The rate limit and the lockout of `R-26`'s second half |

**One head, one owner.** `A1` owns it until Gate A closes, then the integrator; `W34-DOM`
holds it for wave 34 and wrote `0006_app_user`; `W39-REVOKE` holds it for wave 39 and wrote
`0007_credential_epoch`; `W40-LIMIT` holds it for wave 40 and wrote `0008_sign_in_throttle`.
No Gate B session writes DDL. A schema
need is submitted as a test plus the constraint it asks for; see `docs/program/P02_SEAMS.md` §10.

The table list, the SQLSTATE codes and the declared state topology are documented in
`docs/program/P02_SEAMS.md` §3, which is the register Gate B consumes. This file
covers only how to run and extend the migrations.

## Running them

The literal invocation, from `docs/program/FOUNDATION_LOCK.json`:

```sh
PYTHONPATH=src .venv/bin/python -m alembic --config db/migrations/alembic.ini upgrade head
```

`make migrate` forwards to exactly that. `DATABASE_URL` must be set — it is one of the
fifteen names FF-01 freezes — and must carry the `postgresql+psycopg` driver. There is
no default connection and no SQLite fallback: both are refused explicitly by
`auditmanager.shared.db.config`, before any connection is attempted.

To read the state without changing it:

```sh
PYTHONPATH=src .venv/bin/python -m auditmanager.shared.db.check     # make check-db
```

The check never applies a migration. Keeping the two apart is what makes "the second
migration is a no-op" a checkable claim: a probe that could upgrade would always find
itself at head.

## Layout

```
db/migrations/
  alembic.ini        the reserved runner configuration
  env.py             reads DATABASE_URL through auditmanager.shared.db.config
  script.py.mako     template for a new revision
  versions/          one file per revision, named <date>_<number>_<slug>.py
```

`script_location = %(here)s` in the ini, so the script directory resolves from the
ini's own location and the working directory does not matter. There is **no**
`sqlalchemy.url` in the ini: a URL there would be a second, unfrozen source of truth,
and it would be committed to git.

## Autogenerate is not wired, deliberately

`target_metadata` is `None` and `alembic revision --autogenerate` produces nothing
useful. Write the DDL.

The invariants that carry this schema are append-only ledgers, immutable published
rows and a declared state topology, all of which live in triggers and CHECK
constraints. Autogenerate neither writes those nor notices one going missing, so a
declarative model tree kept only to feed it would be a second description of the
schema with no reader — and the more authoritative-looking of the two.

## Adding a revision

1. `PYTHONPATH=src .venv/bin/python -m alembic --config db/migrations/alembic.ini revision -m "<slug>"`
2. Write explicit DDL in `upgrade()`. Reuse the helpers at the top of
   `20260910_0002_pc01_schema.py` — `id_check`, `enum_check`, the vocabulary tuples —
   so the new object agrees with the frozen contracts by construction.
3. Add the test that proves the new constraint **can fail**, under
   `tests/integration/db/`. A constraint nobody has watched refuse anything is a
   comment with a syntax-error budget.
4. Run the gate below.

Two traps this schema has already paid for:

* **A CHECK that evaluates to NULL is satisfied.** `verdict = 'accepted'` with a NULL
  verdict passes the constraint that exists to stop it. Use `IS NOT DISTINCT FROM`.
* **A named constraint is a droppable constraint.** Every CHECK, UNIQUE and FK here
  is named. PostgreSQL invents names for unnamed ones and a later migration cannot
  address them.

## Downgrade

`0002_pc01_schema` has a real `downgrade()`. It exists so a **pre-consumer** revert is
one command against a disposable local database, which is the rollback the task
specifies. It drops every finding, decision and audit event.

Never run it against a populated database. Rollback of a populated database is a
restore, not a migration.

## Gate

Against a real PostgreSQL instance — never SQLite — with this lane's `DATABASE_URL`:

```sh
PYTHONPATH=src .venv/bin/python -m alembic --config db/migrations/alembic.ini upgrade head  # from empty
PYTHONPATH=src .venv/bin/python -m alembic --config db/migrations/alembic.ini upgrade head  # safe at head
PYTHONPATH=src .venv/bin/python -m auditmanager.shared.db.check
.venv/bin/pytest tests/integration/db
git diff --check
```

`tests/integration/db` creates and drops its own throwaway database per test, so it
needs `CREATEDB`, and it **fails** rather than skips when `DATABASE_URL` is unset: a
skipped integration suite reports success while proving nothing.
