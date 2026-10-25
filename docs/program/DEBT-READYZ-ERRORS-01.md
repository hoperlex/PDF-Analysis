# DEBT-READYZ-ERRORS-01 — `/readyz` waits for the API listener; errors module off SQLAlchemy

Task: `docs/program/tasks/DEBT-READYZ-ERRORS-01.md`. Branch `agent/debt-readyz-errors-01`, based on `1703d5ba`.

Both rows were re-measured on the base tree before any change and were still open (premises P-01 to P-04 in the task file). Neither was already fixed.

## D-196 — `/readyz` answered before the API port accepted

`infra/deploy/serve.py` ran the health plane on a daemon thread and the API on the main thread, and `build_health_app` knew nothing of the API socket. The window is the API's lifespan start-up time. Measured on the base tree through the real `serve.main()` with the application factories stood in (the real lifespan connects to PostgreSQL) and a 0.3 s stand-in lifespan: `/readyz` answered 200 **286 to 291 ms** before the API port accepted a connection, three runs of three.

The repair:

- `src/auditmanager/api/health.py`: `build_health_app(application=None, *, serving=None)`. With `serving` given, `/readyz` answers `503` `{"status": "starting", "wired": ...}` until `serving()` is true, then the old `200` body byte for byte. `/healthz` never consults it. An exception from `serving` is a `500`.
- `infra/deploy/serve.py`: the API `uvicorn.Server` is constructed first, the health app gets `serving=lambda: api_server.started`, and `api_server.run()` is the same object. `uvicorn` sets `started` after the lifespan start-up completes and the listener is bound.

After the change, the same measurement (three runs): `/readyz` status changes `[(503, ~1.0 s), (200, ~1.3 s)]`, and a connect made in the same poll step right after the first 200 succeeded every time (before: it was refused for ~290 ms after the first 200).

`None` for `serving` keeps the wiring-only answer so existing callers that poll the plane alone (`tests/integration/api/test_served_document_and_health_plane.py`) are unchanged. The one production caller passes it, and the serve test fails if it stops.

## D-129 Y F-7 — the router imported the persistence library

`api/routers/errors.py:39` had `from sqlalchemy.exc import DBAPIError`. `shared/db` had no public name for it, so `src/auditmanager/shared/db/public.py` is new and holds the single re-export (`DBAPIError`, the same class object). `errors.py` imports it from there. Classification is untouched. After the change `git grep sqlalchemy -- src/auditmanager/api` is empty.

## Verification

All from `/root/projects/PDF-Analysis/.local/worktrees/debt-readyz-errors-01`, `BS` = the bootstrap `site-packages`, `PYTHONPATH=src:$BS`, `.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider`:

| paths | result |
| --- | --- |
| `tests/contract/architecture tests/contract/api_v1 tests/unit/api tests/integration/composition/test_serve_readiness.py` | 369 passed |
| `tests/integration/composition/test_deployed_stack_probe.py` | 32 passed |
| `tests/integration/qa_w55b/test_harness_ports.py` | 11 passed |
| `tests/contract/program` | 28 passed |
| `tests/integration/api/test_served_document_and_health_plane.py` | 8 passed, 1 failed, 1 error; **identical on the base tree** (checked in a detached worktree at `1703d5ba`): the failure compares operation-ID sets and the error needs an S3 bucket; neither touches the health plane |
| governance one-liner for the task file | `[]` |

Not run (need PostgreSQL and/or S3, no stack may be started in this lane): `tests/integration/api/test_database_refusals.py`, `test_error_envelope.py`, `test_router_and_body_rules.py`, `test_the_documentation_routes_are_behind_the_seam.py` and the rest of `tests/integration/api/**`. They fail at fixture setup with `DATABASE_URL is not set` / `S3_ENDPOINT_URL` missing, before any code of this change runs. The integrator should re-run `tests/integration/api/test_database_refusals.py` and `test_error_envelope.py` on a database lane: they are the real-trigger counterpart to the hand-built refusals in the new unit test.

## Every new guard shown red under a mutation

Each mutation applied to the committed code, the named tests run, then reverted (tree clean afterwards).

| mutation | red |
| --- | --- |
| `health.py`: `if serving is not None and not serving():` becomes `if False:` | 3 unit cases (refused while not serving; turns on with the flag; failing flag) and the serve wiring case |
| `serve.py`: `build_health_app(application, serving=...)` becomes `build_health_app(application)` | `test_readyz_is_refused_until_the_api_server_the_process_runs_has_started` |
| `serve.py`: `serving=lambda: api_server.started` becomes `serving=lambda: True` | the same case |
| `serve.py`: `api_server.run()` becomes a freshly built `uvicorn.Server(...).run()` | both serve cases (a different server than the one watched) |
| `health.py`: `/healthz` answers 503 when `serving` is false | `test_liveness_never_consults_the_flag` |
| `errors.py`: the import back to `from sqlalchemy.exc import DBAPIError` | `test_no_module_of_the_api_package_imports_sqlalchemy` |
| `public.py`: `class DBAPIError(Exception): ...` in place of the re-export | `test_the_edge_name_is_the_driver_class_itself` and four classification cases |

The import guard's detector is itself shown able to fail: four parametrized cases feed it each spelling of a `sqlalchemy` import and require a finding, and a control feeds it the boundary name and requires none.

## Risks and limits

- No real-socket test of `serve.py` is in the suite (the only existing pattern is the QA harness, which needs a database lane). The real-socket evidence is the scratch measurement above; the unit and wiring tests pin the mechanism (the flag is the run server's own `started`).
- `Server.started` stays true during a graceful shutdown until the process exits; readiness is not a drain signal. Not requested, not changed.
- `infra/deploy/README.md` line 236 describes only the `200` body of `/readyz`; that file is under `infra/**` and outside this lane.
- The QA harness (`tests/integration/qa_w55b/qa_support.py`) still waits for both planes. That is now redundant and harmless; changing it is outside this lane.

## Integrator actions

1. Merge `agent/debt-readyz-errors-01` after any lane that edits `serve.py` or `health.py` (none known).
2. Register: close `D-196`; remove "Y F-7" from `D-129`'s remaining list. Check commands: `git grep -n sqlalchemy -- src/auditmanager/api` (empty) and the three test files above.
3. Optionally add one sentence on the `503 starting` answer to `infra/deploy/README.md`.
4. On a database lane run `tests/integration/api/test_database_refusals.py` and `tests/integration/api/test_error_envelope.py`, and the QA harness once, to see a real `serve.py` start report `503` and then `200`.
