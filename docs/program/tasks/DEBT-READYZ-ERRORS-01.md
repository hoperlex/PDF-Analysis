# Task DEBT-READYZ-ERRORS-01 — `/readyz` waits for the API listener; the errors module stops importing SQLAlchemy

task_id: DEBT-READYZ-ERRORS-01
status: completed in development candidate

## Outcome

Two debt rows that `DEBT-AUDIT-1` and `DEBT-AUDIT-2` measured as still open against the tree on 2026-10-26 are closed in code:

- `D-196`: the health plane answers `/readyz` with `503` until the API `uvicorn.Server` has completed its lifespan start-up and bound its listener, then with the unchanged `200` body. `/healthz` is unchanged and never waits.
- the code half of `D-129` Y F-7: `src/auditmanager/api/routers/errors.py` no longer imports `sqlalchemy`; it takes `DBAPIError` (the same class object) from `auditmanager.shared.db.public`. No module under `src/auditmanager/api/**` imports `sqlalchemy` any more, and a test says so.

## Depends on

- `DEBT-AUDIT-1`, `DEBT-AUDIT-2` — completed; they measured both rows as still open.
- `GATE-REPAIR-01` — completed; it measured the `/readyz` window and repaired only the QA harness.

## Frozen inputs

- domain contract: unchanged (27 error codes)
- API contract: unchanged (92 paths / 104 operations / 300 schemas); the health plane is off the contract document by design (`T-3`)
- analysis/comparison/event contract: unchanged
- migration head: `0032_ar_v3_run_group`
- base commit: `1703d5bacacb1288fe7bdd7f99793705f1453406` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: `/readyz` is served by a thread that does not depend on the API socket, and `errors.py` imports `sqlalchemy.exc`; both rows were still open on the base tree

### P-01 — the start order in `serve.py` (D-196)

- captured_at: 2026-10-26
- command: `git show 1703d5ba:infra/deploy/serve.py | rg -n "build_health_app\(|threading.Thread|uvicorn.Server\(|\.run\(\)"`
- captured_output:
  ```text
  88:    health_app = build_health_app(application)
  90:    health = uvicorn.Server(
  93:    threading.Thread(target=health.run, name="health-plane", daemon=True).start()
  101:    uvicorn.Server(
  103:    ).run()
  ```
- interpretation: the health app is built from the application alone and served from a daemon thread before the API server is even constructed; nothing connects `/readyz` to the API listener.

### P-02 — `/readyz` answers before the API port accepts, measured on the base tree (D-196)

- captured_at: 2026-10-26
- command: `LIFESPAN_SECONDS=0.3 /root/projects/PDF-Analysis/.venv/bin/python -I /tmp/claude-0/-root-projects-PDF-Analysis/16441722-42ee-458c-b74f-e08cf340d7b7/scratchpad/l12/measure_main.py <lane worktree on 1703d5ba> 28710 28711`
- captured_output:
  ```text
  readyz status changes (status, ms since spawn): [(200, 1126)]
  first /readyz 200 at 1126 ms; API port accepted at 1414 ms
  /readyz answered 200 288 ms BEFORE the API port accepted a connection
  readyz status changes (status, ms since spawn): [(200, 1138)]
  first /readyz 200 at 1138 ms; API port accepted at 1424 ms
  /readyz answered 200 286 ms BEFORE the API port accepted a connection
  readyz status changes (status, ms since spawn): [(200, 1157)]
  first /readyz 200 at 1157 ms; API port accepted at 1448 ms
  /readyz answered 200 291 ms BEFORE the API port accepted a connection
  ```
- interpretation: this runs the real `infra/deploy/serve.py` `main()`, the real `build_health_app` and two real `uvicorn` servers over real sockets. Only the application factories are stood in (`create_app`, `create_asgi_app`), because the real lifespan connects to PostgreSQL (a start with an unreachable `DATABASE_URL` exits 3 in the lifespan, before any bind, and no database may be started in this lane); the stand-in API app is a bare ASGI app whose lifespan start-up sleeps 0.3 s in place of that work. The script is a scratch file and is not committed; its method is: spawn the child, poll `/readyz` and a TCP connect to the API port every 2 ms, print the status changes and the two first-success times. With `LIFESPAN_SECONDS=0` the same script shows a race of a few milliseconds (two runs: the first `/readyz` 200 and the first accepted connect 1 ms and 0 ms apart), consistent with `GATE-REPAIR-01`'s 19 to 26 ms over 12 real starts; the window is the API's lifespan start-up time, so a database-touching start-up widens it.

### P-03 — the router imports the persistence library (D-129 Y F-7)

- captured_at: 2026-10-26
- command: `git grep -n "sqlalchemy" 1703d5ba -- src/auditmanager/api`
- captured_output:
  ```text
  1703d5ba:src/auditmanager/api/routers/errors.py:39:from sqlalchemy.exc import DBAPIError
  ```
- interpretation: one import, in one module, used for `isinstance(exc, DBAPIError)` in `to_domain_error` and `except DBAPIError` in `guarded`. No other module of the API package imports `sqlalchemy`, so a package-wide guard has no exceptions to carry.

### P-04 — no public database-boundary name for the exception existed

- captured_at: 2026-10-26
- command: `git ls-tree --name-only 1703d5ba src/auditmanager/shared/db/ && git grep -n "DBAPIError" 1703d5ba -- src/auditmanager/shared`
- captured_output:
  ```text
  src/auditmanager/shared/db/__init__.py
  src/auditmanager/shared/db/check.py
  src/auditmanager/shared/db/config.py
  src/auditmanager/shared/db/engine.py
  src/auditmanager/shared/db/errors.py
  src/auditmanager/shared/db/migrations.py
  src/auditmanager/shared/db/schema.py
  src/auditmanager/shared/db/session.py
  1703d5ba:src/auditmanager/shared/statemachine/guard.py:6:did wrong instead of reading a ``DBAPIError``.
  ```
- interpretation: `shared/db` has no `public.py` and exports no driver-error class or classifier helper (`shared.db.errors` holds the boundary's own `DatabaseError` family, not the driver's); the only other mention is a docstring. One minimal re-export was therefore added in the new `shared/db/public.py`, as the lane brief provides.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `infra/deploy/serve.py`
- `src/auditmanager/api/routers/errors.py`
- `src/auditmanager/api/health.py`
- `src/auditmanager/shared/db/public.py`
- `tests/unit/api/**`
- `tests/integration/composition/test_deployed_stack_probe.py`
- `tests/integration/composition/test_serve_readiness.py`
- `docs/program/tasks/DEBT-READYZ-ERRORS-01.md`
- `docs/program/DEBT-READYZ-ERRORS-01.md`

## Forbidden hotspots

Contracts, migration head, root dependency/lock files, `Makefile`, every `infra/**` file other than `infra/deploy/serve.py`, the composition root (`src/auditmanager/bootstrap/**`, `web/src/_app/providers.tsx`), `web/**`, global styles, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `origin/main`, tags and the deployment host.

## Non-goals

No new environment variable, no new port, no change to `/healthz`, to the `200` body of `/readyz` or to the paths. No change to how a database refusal is classified (the SQLSTATE map, the codes, the details screening). No edit of `D-196`/`D-129` rows in the register (the integrator closes them), of `infra/deploy/README.md` (which still quotes only the `200` body), or of the QA harness's own two-plane wait in `tests/integration/qa_w55b/qa_support.py` (it stays correct and is now redundant belt and braces). No real-socket test of `serve.py`: the only existing pattern is the QA harness, which needs a database lane.

## Deliverables

- `build_health_app(application, *, serving=None)` with `503` `{"status": "starting", "wired": ...}` until `serving()` is true; `None` keeps the old wiring-only answer for a plane polled alone.
- `serve.py` builds the API `uvicorn.Server` first and passes `lambda: api_server.started`; the same object is the one `run()` blocks on.
- `auditmanager.shared.db.public` re-exporting `DBAPIError`; `errors.py` importing it from there.
- Tests: `tests/unit/api/test_readiness_waits_for_the_listener.py` (5), `tests/unit/api/test_errors_module_uses_the_database_boundary.py` (16 collected), `tests/integration/composition/test_serve_readiness.py` (2).
- This file and `docs/program/DEBT-READYZ-ERRORS-01.md`.

## Required tests

- `PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/contract/architecture tests/contract/api_v1 tests/unit/api tests/integration/composition/test_serve_readiness.py` with `BS` the bootstrap `site-packages`: expected all pass (369 on the lane).
- `tests/integration/composition/test_deployed_stack_probe.py` (32) and `tests/integration/qa_w55b/test_harness_ports.py` (11) still pass. `tests/integration/api/test_database_refusals.py`, `test_error_envelope.py` and the real-bucket fixtures of `tests/integration/api/**` need PostgreSQL/S3 and did not run.
- Governance of this file: the `governance_findings` one-liner from the lane brief prints `[]`.
- `git diff --check` and the exact allowed-path inventory.

## Integration contract

A consumer of the health plane (a deployment probe, the QA harness, a proxy) may treat `/readyz` `200` as "the API port accepts connections"; `503` with `status: starting` means it does not yet. `/healthz` stays `200` from the moment the thread answers, which is what the container healthcheck (`compose.server.yml`, port 8001) reads. `uvicorn` sets `Server.started` after the lifespan start-up completes and the listener is bound, so a connect made right after a `/readyz` `200` succeeds. After a shutdown signal `started` stays true until the process exits; readiness does not claim to be a drain signal. `from auditmanager.shared.db.public import DBAPIError` is the name an edge uses to recognise a driver refusal; it is the same class as `sqlalchemy.exc.DBAPIError`.

## Failure/idempotency/security cases

A `serving` predicate that raises produces `500`, never a ready answer. A plane built without `serving` keeps answering readiness from wiring alone; the one production caller passes it and `test_serve_readiness.py` fails if it stops, if it passes a constant, or if the server it watches is not the server it runs. An API server that fails to bind exits the process (`uvicorn` exits with `STARTUP_FAILURE`), taking the daemon health thread with it, so `/readyz` never reports a listener that never came up. The refusal classifier maps only the three custom SQLSTATEs and keeps every other refusal as `internal_error`, and never renders driver prose (pinned unchanged).

## Rollback / feature flag

Forward-revert. No flag: the change is a stricter answer from an operational endpoint nothing in `infra/` polls (the compose healthcheck reads `/healthz`).

## Handoff

- changed files: `infra/deploy/serve.py`, `src/auditmanager/api/health.py`, `src/auditmanager/api/routers/errors.py`, `src/auditmanager/shared/db/public.py` (new), three new test files (two under `tests/unit/api/`, one `tests/integration/composition/test_serve_readiness.py`), this file and the report
- commands/results: see `docs/program/DEBT-READYZ-ERRORS-01.md`
- known limits: no real-socket test in the suite; database-dependent suites not run; `infra/deploy/README.md` line 236 still quotes only the `200` body (an `infra/**` file this lane may not touch)
- integration notes: close `D-196` and narrow `D-129` (remove Y F-7) in the register; add the `503 starting` sentence to `infra/deploy/README.md`; the QA harness may drop its API-port probe whenever convenient
