# Task SEC-DB-TERSE-ERRORS-01 — close the other half of F-12: no row data in a database exception string

task_id: SEC-DB-TERSE-ERRORS-01
status: completed in development candidate (measured on the integrator's lane PostgreSQL 17.11 on a private throw-away database; nothing run against a deployed host)

## Outcome

`EXPOSURE-REVIEW-02` `F-12`, the part `HARDEN-01` left open (`docs/program/HARDEN-01.md`, "Needs your attention" 1): a database exception raised through the product's engine carries no row data. `hide_parameters=True` hid SQLAlchemy's `[parameters: ...]`; PostgreSQL's own `DETAIL:  Failing row contains (...)` and `DETAIL:  Key (a)=(k1) already exists.` were still in `str(exc)`, so the two `_log.exception` sinks (`runs/carrier.py`, `workers/service.py`) and any other could write a column of the refused row (`D-225`: the model output of a `stage_result` insert; a client document's text) into a log line. Every PostgreSQL connection the product opens now asks libpq for **terse** error verbosity, so the message keeps the primary text (it names the constraint) and loses `DETAIL`, `HINT`, `CONTEXT`.

## Depends on

- `HARDEN-01` (merged into the base `a1d3f348`; its `hide_parameters=True` and `tests/unit/shared/test_engine_hides_parameters.py`).
- `EXPOSURE-REVIEW-02` row `F-12`; register row `D-240` (the `rg hide_parameters` check passed and the harm was not gone).

## Frozen inputs

- domain contract: not_applicable
- API contract: `1.7.0` (`info.version`), unchanged (`contracts/**` is not touched; no response carries a database message)
- analysis/comparison/event contract: not_applicable
- migration head: unchanged (`0033_ar_v3_cite_stage_id`)
- base commit: `a1d3f348` (`integration/ar-close-1026`), branch `agent/sec-db-terse-errors-01`

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the brief named `connection.pgconn.set_error_verbosity(...)` as psycopg 3's way to set the verbosity. **That differs from the installed driver (P-02): psycopg 3.3.5 has no such method.** The lane did not stop: the brief's own wording ("use its supported way; if the driver cannot do it, fall back to scrubbing at the two sinks") and the driver's documented `pgconn_ptr` give a way that needs neither a scrub nor a change to the sinks. Everything else the brief names was re-read at `a1d3f348` and is as described.

### P-01 — the engine at the base: `hide_parameters` is there, the server's message is not tamed
- captured_at: 2026-10-27
- command: `git show a1d3f348:src/auditmanager/shared/db/engine.py | sed -n 29,38p; git show a1d3f348:src/auditmanager/shared/db/engine.py | sed -n 33,50p | grep -n "hide_parameters"`
- captured_output:
  ```text
      ``hide_parameters`` is on (``EXPOSURE-REVIEW-02`` ``F-12``): without it a SQLAlchemy
      exception renders ``[parameters: (...)]`` after the statement, and the sinks that log an
      exception (the run carrier, the worker) would write bound values -- client text, model
      output -- into the container log. The statement text stays in the message; the values do
      not, in the exception string and in the statement log that ``echo`` turns on. This does
      **not** remove the database server's own ``DETAIL`` line (``Failing row contains (...)``,
      ``Key (...)=(...) already exists``), which the driver puts in the same string; that is a
      separate, open follow-up (``docs/program/HARDEN-01.md``).
      """
      return create_engine(
  ```
- interpretation: `create_database_engine` is the only caller of `create_engine` under `src/` (P-05) and it has no `connect` hook at the base.

### P-02 — psycopg 3.3.5 has no setter for the error verbosity, and documents the way around it
- captured_at: 2026-10-27
- command: `cd /tmp && .venv/bin/python -I -c "import psycopg, psycopg.pq as pq; print('psycopg', psycopg.__version__, 'impl', pq.__impl__, 'libpq', pq.version()); print('PGconn verbosity methods:', [n for n in dir(pq.PGconn) if 'verb' in n.lower()]); print('PGconn.pgconn_ptr present:', hasattr(pq.PGconn, 'pgconn_ptr'))"; grep -rniE "verbosity" .venv/lib/python3.12/site-packages/psycopg .venv/lib/python3.12/site-packages/psycopg_binary --include=*.py --include=*.pyx --include=*.pxd --include=*.pyi | wc -l`
- captured_output:
  ```text
  psycopg 3.3.5 impl binary libpq 180006
  PGconn verbosity methods: []
  PGconn.pgconn_ptr present: True
  0
  ```
- interpretation: `connection.pgconn.set_error_verbosity` does not exist (zero lines mention "verbosity" in the driver). psycopg documents `PGconn.pgconn_ptr` as the handle for calling libpq functions it does not wrap, through ctypes. The wheel bundles its own libpq (`psycopg_binary.libs/libpq-e9b5c9ac.so.5.18`, version 180006); a call must go through *that* library, not a system one of another version (a different `PGconn` layout). Measured with the prototype: `PQsetErrorVerbosity(ptr, 0)` returned `1` (the default) the first time and `0` the second, and the next error message on that connection was terse.

### P-03 — the leak, measured on the lane PostgreSQL (private database, dropped afterwards)
- captured_at: 2026-10-27
- command: a scratch script building an engine through `create_database_engine` at the base and violating a primary key, a CHECK and a NOT NULL (`PostgreSQL 17.11`, host `127.0.0.1:58640`, database created and dropped by the script)
- captured_output:
  ```text
  (psycopg.errors.UniqueViolation) duplicate key value violates unique constraint "t_pkey"
  DETAIL:  Key (a)=(k1) already exists.
  [SQL: insert into t values ('k1','SENTINEL-u')]
  (psycopg.errors.CheckViolation) new row for relation "t" violates check constraint "t_b_check"
  DETAIL:  Failing row contains (k2, forbidden).
  (psycopg.errors.NotNullViolation) null value in column "b" of relation "t" violates not-null constraint
  DETAIL:  Failing row contains (SENTINEL-n, null).
  diag.message_detail: Key (a)=(k1) already exists. | constraint: t_pkey | sqlstate 23505
  ```
- interpretation: the three server messages put row values in the exception string at the base. `diag` (structured) carries `constraint_name` and `sqlstate`.

### P-04 — the sinks, and nothing that reads the text
- captured_at: 2026-10-27
- command: `rg -n "_log\.exception" src/auditmanager/runs/carrier.py src/auditmanager/workers/service.py | cut -c1-150`; and `rg -n "DETAIL|diag\.|constraint_name|\.detail" src tests --glob '*.py'` filtered to database-error reads (the full listing was read; non-database `.detail` attributes of other classes were discarded)
- captured_output:
  ```text
  src/auditmanager/runs/carrier.py:310:                _log.exception("durable dispatch poll failed")
  src/auditmanager/runs/carrier.py:370:                _log.exception("lease reclaim pass failed")
  src/auditmanager/runs/carrier.py:466:        _log.exception("run %s did not reach a terminal by itself", run_id)
  src/auditmanager/runs/carrier.py:470:        _log.exception("run %s did not reach a terminal by itself", run_id)
  src/auditmanager/runs/carrier.py:521:        _log.exception("run %s could not be recorded as failed either", run_id)
  src/auditmanager/workers/service.py:329:                _log.exception("worker %s heartbeat failed; retried next tick", self._worker_id)
  src/auditmanager/workers/service.py:388:                    _log.exception("worker %s probe pass failed; retried", self._worker_id)
  src/auditmanager/workers/service.py:401:                _log.exception(
  src/auditmanager/workers/service.py:412:                _log.exception("worker %s lease reclaim pass failed", self._worker_id)
  src/auditmanager/workers/service.py:424:                _log.exception("worker %s could not read the queue", self._worker_id)
  src/auditmanager/workers/service.py:478:                _log.exception("worker %s could not touch its heartbeat file", self._worker_id)
  src/auditmanager/documents/refusals.py:79:    value = getattr(diagnostic, "constraint_name", None)
  src/auditmanager/jobs/repository.py:862:            constraint = getattr(diagnostic, "constraint_name", None)
  src/auditmanager/decisions/ledger.py:240:        and getattr(diagnostic, "constraint_name", None)
  tests/integration/db/test_norm_custody_migration.py:51:    return getattr(getattr(error.value.orig, "diag", None), "constraint_name", None)
  tests/integration/db/test_durable_analysis_effects.py:297:            getattr(getattr(refused.value.orig, "diag", None), "constraint_name", None)
  tests/integration/ingest/test_immutability.py:173:    assert constraint_name_of(exc) == "pk_input_manifest_entry"
  ```
- interpretation: eleven `_log.exception` calls in the two named modules (the review counted nine; `carrier.py:310,370` are two more) print the whole traceback including the chained driver exception. All product reads of a database refusal are of SQLSTATE or `diag.constraint_name` (structured fields libpq stores raw, whatever the verbosity). **No product code and no test reads `DETAIL`, `Failing row`, `HINT` or `CONTEXT` text.** Tests that read the *primary* message for a constraint name (`match="pk_stage_result"`, `in str(caught.value.orig)` ...) are unaffected, because terse keeps the primary message; they were run (report section 6).

### P-05 — no second door
- captured_at: 2026-10-27
- command: `rg -n "create_engine\(|create_async_engine\(|psycopg\.connect\(|engine_from_config\(" src; rg -n "create_engine\(|psycopg\.connect\(" scripts tests/e2e --glob '*.py'`
- captured_output:
  ```text
  src/auditmanager/shared/db/engine.py:139:    engine = create_engine(
  scripts/rehearsal/w55b/drive.py:286:    with psycopg.connect(_db_url()) as conn:
  scripts/recovery/synthetic_drill_compare.py:258:        engine = create_engine(values["DATABASE_URL"])
  scripts/recovery/synthetic_drill_compare.py:273:        engine = create_engine(target["DATABASE_URL"])
  ```
- interpretation: inside `src/` the one constructor is the only door (a test now fails if a second appears). `alembic`'s `env.py`, every CLI under `src/` and `bootstrap/composition.py` all go through `create_database_engine`. Two operator scripts under `scripts/` open their own connection; they are outside this lane's paths and are listed in the report.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: none
- origin_main_authority: none

The lane commits to `agent/sec-db-terse-errors-01` and pushes nothing. `origin/main` triggers a deployment (`AGENTS.md` section 6) and is not touched.

## Allowed paths

- `src/auditmanager/shared/db/engine.py`
- `tests/unit/shared/**`
- `tests/integration/db/**`
- `docs/program/tasks/SEC-DB-TERSE-ERRORS-01.md`
- `docs/program/SEC-DB-TERSE-ERRORS-01.md`

`src/auditmanager/runs/carrier.py` and `src/auditmanager/workers/service.py` were allowed only if the premise proved the hook cannot cover them. It covers them (the message is built by libpq at result time, on the connection), so neither is touched.

## Forbidden hotspots

- `contracts/**`, migrations and the migration head
- `infra/**`, `web/**`, every other file under `src/**`
- root dependency/lock files
- `docs/program/DEBT_REGISTER.md`, `CURRENT_STATE.md`, the plan, the rulings, the ADRs

## Non-goals

- the PostgreSQL server's own log (`docker logs` of the `postgres` service prints `DETAIL` regardless of the client: `log_error_verbosity` is a server setting; that is `infra/**`)
- a redaction layer or scrubbing at log sinks (not needed: the message never contains the detail)
- `scripts/recovery/synthetic_drill_compare.py` and `scripts/rehearsal/w55b/drive.py`, which build their own connections
- SQL text that a caller inlines instead of binding (`[SQL: ...]` stays in the message by design)

## Deliverables

- `src/auditmanager/shared/db/engine.py`: the `connect` hook `_set_terse_error_verbosity`, the libpq lookup `_driver_libpq`, the registration in `create_database_engine`, docstrings corrected
- new tests: `tests/integration/db/test_database_errors_are_terse.py` (real PostgreSQL), `tests/unit/shared/test_engine_terse_hook.py` (no database); modified: `tests/unit/shared/test_engine_hides_parameters.py` (docstring only)
- the report `docs/program/SEC-DB-TERSE-ERRORS-01.md`

## Required tests

- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); env $(grep -v '^#' .env | grep -v '^$' | xargs) PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/shared tests/integration/db/test_database_errors_are_terse.py`
- expected: all pass; the counts are in the report
- command: the existing database-error suites (report section 6): `tests/integration/db` whole, `tests/integration/runs/test_idempotency_and_topology.py`, `tests/integration/api/test_database_refusals.py`, `tests/integration/findings/test_ungrounded_vocabulary_is_enforced.py`, `tests/integration/runs/test_call_status_and_output_tokens.py`, `tests/integration/norms/test_snapshot_rows.py`, `tests/integration/ingest/test_immutability.py`, `tests/integration/jobs`
- expected: all pass
- command: `PYTHONPATH=src:$BS .venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` (after the last commit)
- expected: green

## Integration contract

What the integrator can rely on:

- every engine built by `create_database_engine` for `postgresql+psycopg` sets libpq's error verbosity to terse on each new connection, before the pool hands it out. That covers the served API, the workers, the carrier, `alembic` (`db/migrations/env.py`), and every CLI under `src/`.
- an exception string from such an engine has: the SQLAlchemy line `(psycopg.errors.<Class>) <primary message>`, `[SQL: ...]`, `[SQL parameters hidden ...]`. It has no `DETAIL:`, `HINT:`, `CONTEXT:`, `QUERY:` line and no `LINE n:` snippet (a position, `at character N`, replaces it).
- unchanged: SQLSTATE (`exc.orig.sqlstate`, the exception class), `exc.orig.diag.*` (including `constraint_name`, `column_name`, and, as before, `message_detail` and `message_hint`, which nothing prints), the primary message with the constraint name.
- the hook **fails closed**: if the process's libpq cannot be identified (not exactly one libpq file mapped, a version that psycopg does not report, an unreadable `/proc/self/maps`, a connection without a handle) the new connection is closed and `DatabaseConfigurationError` propagates; no connection is served verbose. The mechanism is Linux-only; the product's images and hosts are Linux.
- no file under `contracts/**`, `db/migrations/**`, `infra/**`, `web/**`, the lock files, `runs/carrier.py` or `workers/service.py` is touched.

## Failure/idempotency/security cases

- unique, CHECK, NOT NULL and foreign-key refusals each carry a sentinel in the refused row; it is absent from `str`/`repr` of the SQLAlchemy exception, of the driver exception, from `args`, and from the text a `logger.exception` call writes (which includes the chained driver exception, as both sinks do)
- the same four refusals through an engine without the hook show the sentinel and `DETAIL:` (the control)
- three simultaneously open pooled connections, an engine rebuilt by `dispose()`, and the process-wide `get_engine()` are each terse
- `sqlstate`, `diag.constraint_name`, `diag.column_name` and the product's own `documents.sqlstate_of` / `constraint_name_of` read the right values through a terse engine
- the lookup refuses none, two, or a mismatching libpq; a connection without a handle, or with an untrusted lookup, is closed
- every guard is shown failing under a mutation (the table in the report)

## Rollback / feature flag

No flag. Reverting the commit restores the previous message (with `DETAIL`), which is exactly the previous state; nothing is data and nothing needs a migration. If a host reports `DatabaseConfigurationError` from the hook at start, the cause is a process whose libpq cannot be identified; the revert is the remedy, and the exception text names which check refused.

## Handoff

- changed files: see the report, section 2
- commands/results: see the report, section 6
- known limits: see the report, section 8
- integration notes: see the report, section 7
