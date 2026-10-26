# SEC-DB-TERSE-ERRORS-01 — the other half of F-12: no row data in a database exception string

Status: built in the development candidate on `agent/sec-db-terse-errors-01` (base `a1d3f348`), measured on the integrator's lane PostgreSQL 17.11 with private, throw-away databases. Nothing was run in the deployed image or on a host (no docker in this lane); see section 8, item 1, for the one-line check the integrator should run in the built image.

## 1. Result

`HARDEN-01` hid SQLAlchemy's `[parameters: ...]` and named a residual: PostgreSQL's own `DETAIL:  Failing row contains (...)` and `DETAIL:  Key (a)=(k1) already exists.` were still in `str(exc)`, so the `_log.exception` sinks (11 calls in `runs/carrier.py` and `workers/service.py`) and any other could write a column of the refused row into a log line. Now every `postgresql+psycopg` connection built by `create_database_engine` is set to libpq's **terse** error verbosity from a SQLAlchemy `connect` event, before the pool hands it out. Measured with a sentinel bound into the refused row, for a unique, a CHECK, a NOT NULL and a foreign-key refusal: the sentinel is absent from `str`/`repr` of the SQLAlchemy exception, from `str`/`repr`/`args` of the driver exception it chains from, and from the text `logger.exception` writes (which includes that chain, as both sinks do). The same four refusals through an engine without the hook print the sentinel and `DETAIL:` (the control), and the new test was red on the base (6 of 14 failed, section 5).

**The brief's premise differed (task file P-02): psycopg 3.3.5 has no `set_error_verbosity`.** It documents `PGconn.pgconn_ptr` as the handle for libpq functions it does not wrap, so the hook calls `PQsetErrorVerbosity(ptr, 0)` through `ctypes` on the library the process has loaded. The sinks did not need touching, so the fallback to scrubbing was not used and `runs/carrier.py`, `workers/service.py` are unchanged.

## 2. Files

| file | change |
| --- | --- |
| `src/auditmanager/shared/db/engine.py` | `_loaded_libpq_paths`, `_driver_libpq`, `_set_terse_error_verbosity`; `create_database_engine` registers the hook for the `psycopg` driver; two docstrings corrected |
| `tests/integration/db/test_database_errors_are_terse.py` | new, 14 tests, real PostgreSQL (private database from the suite's `empty_database` fixture) |
| `tests/unit/shared/test_engine_terse_hook.py` | new, 12 tests, no database |
| `tests/unit/shared/test_engine_hides_parameters.py` | docstring paragraph only (no assertion touched, see section 4) |
| `docs/program/tasks/SEC-DB-TERSE-ERRORS-01.md`, this report | new |

## 3. What an operator loses and keeps (measured, section 6 item 7 gives the script's shape)

Through a terse connection, the same statement on the same server:

| case | default verbosity | terse |
| --- | --- | --- |
| unique | `duplicate key value violates unique constraint "uq_doc_body"` + `DETAIL:  Key (body)=(<value>) already exists.` | the first line only |
| CHECK / NOT NULL | primary line + `DETAIL:  Failing row contains (<row>).` | the first line only |
| foreign key | primary line + `DETAIL:  Key (parent)=(<value>) is not present in table "parent".` | the first line only |
| trigger `RAISE ... USING ERRCODE='AM001', DETAIL, HINT` | `state_transition_not_allowed: x` + `DETAIL:  machine=m, current_state=a` + `HINT:  Append a new event.` + `CONTEXT:  PL/pgSQL function g() line 2 at RAISE` | `state_transition_not_allowed: x` |
| syntax error | `syntax error at or near "selec"` + `LINE 1: selec 1` + caret | `syntax error at or near "selec" at character 1` |
| `select 1/0` | `division by zero` | unchanged |

**Lost** from every exception string, traceback, CLI line and `alembic` failure that is built on an engine from `create_database_engine`: the `DETAIL`, `HINT`, `CONTEXT` lines (the `USING HINT` text of 22 trigger and migration refusals in 9 migration files, the PL/pgSQL call stack) and the `LINE n:` statement snippet (a character position replaces it; the full statement is still printed by SQLAlchemy as `[SQL: ...]`).

**Kept**: the exception class (which is the SQLSTATE class: `UniqueViolation`, `CheckViolation`, ...), `exc.orig.sqlstate`, the primary message (it names the constraint and the column), the statement text, and the structured fields: `exc.orig.diag.*` is unchanged, `constraint_name`, `column_name`, and also `message_detail` and `message_hint`, which libpq stores raw whatever the verbosity and which nothing in the product prints. Someone debugging can still read `exc.orig.diag.message_detail`.

**Does any product code or test read a DETAIL or constraint name from the message text?** The search of the task file (P-04, `rg -n "DETAIL|diag\.|constraint_name|\.detail" src tests`, then each hit read) finds: no reader of `DETAIL`, `Failing row`, `HINT` or `CONTEXT` text anywhere. Product code reads SQLSTATE and `diag.constraint_name` only (`documents/refusals.py:79`, `jobs/repository.py:862`, `decisions/ledger.py:240`; the `machine=`/`current_state=` words seen in `src` are keyword arguments built in Python, not parsed from a `DETAIL`). Five tests read the *primary* message for a constraint name (`findings/test_ungrounded_vocabulary_is_enforced.py:124`, `runs/test_call_status_and_output_tokens.py:214,248`, `db/test_ar_v3_cite_stage_id_migration.py:227`, `norms/test_snapshot_rows.py:272`); terse keeps the primary message, and all five ran green (section 6). Three tests read `diag.constraint_name` (`db/test_norm_custody_migration.py:51`, `db/test_durable_analysis_effects.py:297`, `ingest/test_immutability.py:173` through `constraint_name_of`); green.

## 4. Modified tests, before and after

Only `tests/unit/shared/test_engine_hides_parameters.py`. Per test: `test_the_control_...`, `test_the_engine_hides_parameters_by_construction`, `test_a_refused_statement_carries_no_parameter_in_its_string_or_repr`, `test_the_statement_log_prints_no_parameter_when_echo_is_on` asserted the same before and after; only the module docstring changed (the paragraph that said the `DETAIL` residual was open now says it is closed by the new tests). The four ran green after (section 6, item 1) and three of them are also red under mutation M9, which shows they still bite.

## 5. Mutation table

Files under test for every row: `tests/unit/shared/test_engine_terse_hook.py`, `tests/integration/db/test_database_errors_are_terse.py`, `tests/unit/shared/test_engine_hides_parameters.py` (30 tests). The mutation is applied to `engine.py`, the three files are run, `engine.py` is restored (`git status` clean after the table was produced).

| # | mutation | result | what turned red |
| --- | --- | --- | --- |
| base | `engine.py` as at `a1d3f348` (no hook), integration file only | 6 failed, 8 passed | the four per-case "no row data" tests, the pooled test, the process-wide test; the 4 controls and the 4 structured-field tests pass by design |
| M1 | hook not registered | 7 failed, 23 passed | the four per-case tests, pooled, process-wide, and the unit test that the hook is installed |
| M2 | verbosity left at default (`1`) | 7 failed, 23 passed | the same five integration tests, the unit test that asserts the value passed to libpq is `0`, and the process-wide test |
| M3 | verbosity `SQLSTATE` (`3`) instead of terse | 5 failed, 25 passed | the four per-case tests (the primary message, which names the constraint, is gone) and the unit pointer/value test |
| M4 | hook sets only the first connection of the process | 7 failed, 23 passed | pooled, process-wide, the four per-case tests (the flag is process-wide, so every connection after the first in the process is verbose) |
| M5 | hook installed only on the `get_engine()` engine, not in the constructor | 6 failed, 24 passed | the four per-case tests, pooled, unit "carries the hook"; **the process-wide test stays green**, as it should (this is the "one engine only" case) |
| M6 | no `PQlibVersion` cross-check | 1 failed, 29 passed | `test_a_libpq_of_another_version_than_psycopgs_is_refused` |
| M7 | any number of libpq files accepted | 1 failed, 29 passed | `test_anything_but_exactly_one_libpq_is_refused[two different libpq files mapped]` |
| M8 | connection not closed when the hook fails | 2 failed, 28 passed | the two "closed and refused" tests |
| M9 | hook installed for every dialect | 3 failed, 27 passed | `test_a_sqlite_engine_does_not` and two of the existing SQLite tests (the SQLite connection has no `pgconn`) |
| M10 | the no-handle check removed | 1 failed, 29 passed | `test_a_connection_without_a_libpq_handle_is_closed_and_refused` |
| M11 | a stray `create_engine(...)` planted in `src/auditmanager/shared/db/zz_stray.py` (removed afterwards) | 1 failed, 11 passed (unit file only) | `test_no_module_of_src_opens_a_connection_of_its_own` names the file and line |

The scan of `src` has its own failing case in the same file (`test_the_scan_sees_a_stray_engine`: a throw-away tree with a stray `create_engine`, `psycopg.connect` and `create_async_engine`, and one `create_database_engine` that must not match).

## 6. Commands and counts

All with `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages)`, `PYTHONPATH=src:$BS`, `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`, one pytest at a time; the ones that need the stack are prefixed with `env $(grep -v '^#' .env | grep -v '^$' | xargs)`.

1. `tests/unit/shared tests/integration/db/test_database_errors_are_terse.py`: 46 passed (32 + 14).
2. The existing database-error suites on private databases: `tests/integration/db/test_schema_invariants.py test_every_immutable_table_refuses_a_write.py test_transactions.py test_norm_custody_migration.py test_durable_analysis_effects.py test_ar_v3_cite_stage_id_migration.py test_norm_embeddings_migration.py`, `tests/integration/runs/test_idempotency_and_topology.py`, `tests/integration/api/test_database_refusals.py`, `tests/integration/findings/test_ungrounded_vocabulary_is_enforced.py`, `tests/integration/runs/test_call_status_and_output_tokens.py`, `tests/integration/norms/test_snapshot_rows.py`, `tests/integration/ingest/test_immutability.py`, `tests/integration/jobs`: **297 passed** in 62 s.
3. `tests/integration/db` whole: **709 passed** in 7 min 39 s (it includes the 14 new tests; it builds a migrated template and drops it).
4. Neighbours: `tests/unit/shared tests/unit/api/test_errors_module_uses_the_database_boundary.py tests/contract/architecture tests/integration/shared_kernel tests/integration/foundation/test_negative_paths.py tests/integration/workers`: **119 passed, 244 subtests passed** in 43 s.
5. Mutations: section 5 (ten runs of three files, about 1.2 s each).
6. Docs guards on a clean tree after the code and docs commit: `tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py`: **105 passed** in 20 s; the governance one-liner on the task file prints `[]`; `git diff --check a1d3f348..HEAD` is silent.
7. The measurements of section 3 are from scratch scripts that create a private database on the lane PostgreSQL, build one engine through `create_database_engine` and one plain engine with `hide_parameters=True`, run the statements and drop the database in a `finally`; they are not committed (the committed tests assert the same facts).

Forbidden paths untouched: `git diff --name-only a1d3f348..HEAD` lists exactly

```text
docs/program/SEC-DB-TERSE-ERRORS-01.md
docs/program/tasks/SEC-DB-TERSE-ERRORS-01.md
src/auditmanager/shared/db/engine.py
tests/integration/db/test_database_errors_are_terse.py
tests/unit/shared/test_engine_hides_parameters.py
tests/unit/shared/test_engine_terse_hook.py
```

all inside the allowed paths; `contracts/**`, `db/migrations/**`, `infra/**`, `web/**`, the lock files, `runs/carrier.py` and `workers/service.py` do not appear.

## 7. Integration notes

- Nothing to configure: no setting, no environment variable, no flag. The hook is in the constructor, so the served API, the workers, the carrier, `alembic` (`db/migrations/env.py` builds its engine with `create_database_engine`) and every CLI under `src/` get it. A test fails if any module of `src/` builds an engine or a connection of its own.
- Operator behaviour changes as section 3 says: after deploy a database failure in the container log shows the primary message and the SQLSTATE class but no `DETAIL`/`HINT`/`CONTEXT`. No line of `docs/program/DEPLOYMENT_RUNBOOK.md` or `docs/runbooks` mentions `HINT`, `DETAIL` or `CONTEXT:` (`rg` found none), so no operator instruction goes stale.
- Register wording for the integrator: `D-240` / `F-12` is now fully built (both halves) and unobserved on a live host. The residuals of section 8 items 2 to 5 are not closed by this lane.
- No file under `contracts/**`, `db/migrations/**`, `infra/**`, `web/**`, the lock files, `runs/carrier.py` or `workers/service.py` is touched (proof below).

## 8. Limits and risks

1. **Fail-closed, Linux-only, not run in the built image.** If the process's libpq cannot be identified (not exactly one libpq file mapped, a version psycopg does not report, `/proc/self/maps` unreadable) the first connection raises `DatabaseConfigurationError` and the process is down rather than verbose. `infra/deploy/Dockerfile.api` installs the same `psycopg[binary]==3.3.5` wheel with `uv sync --frozen`, so the lookup should resolve to `psycopg_binary.libs/libpq-*.so.5.18` as it does here, but no docker command is allowed in this lane. A check that needs no database, to run in the built `api` image (and the `norms-worker` one): `PYTHONPATH=src python -c "from auditmanager.shared.db.engine import _driver_libpq; print(_driver_libpq())"` prints a `CDLL` and exits 0. A development machine that is not Linux cannot connect through this engine; the repository is Linux-only (`Makefile`, the images, the hosts).
2. **A primary message can still echo an input literal.** Terse removes `DETAIL`, `CONTEXT`, `HINT`; it cannot remove the first line, and PostgreSQL puts the value in it for casts: measured, `cast(:x as integer)` with a bound string gives `invalid input syntax for type integer: "SENTINEL"` (22P02). A cast to `jsonb` is safe (`invalid input syntax for type json`; the document snippet was in `CONTEXT`), `varchar(3)` overflow and a CHECK on text are safe. `rg` finds 23 `CAST(:name AS type)` / `:name::type` lines in `src`; the first eight read are pagination cursors, timestamps and intervals, not document text, and the rest were not read. Closing this would need scrubbing at the sinks or a typed bind; it is a separate decision.
3. **`diag.message_detail` still holds the row.** libpq stores the fields raw; nothing in the product prints them, and the structured readers need the neighbouring fields. A future sink that logs `exc.orig.diag` would reopen the leak; the integration test pins the reads of `constraint_name`/`column_name`, not the absence of `message_detail`.
4. **The PostgreSQL server's own log is outside this lane.** The server writes `DETAIL` into its log regardless of what the client asks for (`log_error_verbosity` is a server setting; `rg log_error_verbosity infra` finds none, so it is the PostgreSQL default). Not measured here (no docker).
5. **Two operator scripts open their own connection** and are not terse: `scripts/recovery/synthetic_drill_compare.py:258,273` (`create_engine` on a drill target) and `scripts/rehearsal/w55b/drive.py:286` (`psycopg.connect`). Outside the allowed paths; neither is a product log sink.
6. **Inlined literals stay.** The statement text is part of the message by design (`[SQL: ...]`); a caller that builds SQL with a value in the text, rather than a bound parameter, still shows it. The product binds its values (the `hide_parameters` lane's premise).
7. **The mechanism is a workaround for a missing driver method.** If psycopg adds `PGconn.set_error_verbosity`, the ctypes lookup can be replaced by that call; the integration test would keep holding without change.
8. **Orphan template databases on the lane PostgreSQL, not created by this lane.** `pg_database` lists ten `a1_tpl_*` databases (about 126 MB; seven with the migration digest of this tree, `4a21eb91bdc4`, three with `840b23b0bf99`) with no connection and no pytest process on the host. This lane's two sessions that build such a template ended with exit 0 and their finalizers dropped them, so these were left by other sessions; they were not touched. The lane created and dropped only `a1_probe_*`/`a1_clone_*`/`a1_tpl_*` (by the fixtures) and `terse_probe_*` (by the scratch scripts, each in a `finally`).
