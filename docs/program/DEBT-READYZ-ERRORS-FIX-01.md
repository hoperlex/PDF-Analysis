# DEBT-READYZ-ERRORS-FIX-01 — the API access log comes back; `/readyz` is withdrawn on drain

Task: `docs/program/tasks/DEBT-READYZ-ERRORS-FIX-01.md`. Branch `agent/debt-readyz-errors-fix-01`, based on `1aaa7d57` (`integration/ar-close-1026`).

An independent judge found two defects in the `serve.py` change of `DEBT-READYZ-ERRORS-01` (`D-196`). Both were re-proved on the base tree through the real `serve.main()` before any change (premises P-03 to P-05 in the task file), then fixed.

## Defect 1 — the API access log was silenced

`uvicorn.Config.__init__` calls `configure_logging()`. With `access_log=False` that empties the handlers of the process-global `uvicorn.access` logger. The `D-196` change built the API `Config` (`access_log=True`) first and the health plane's (`access_log=False`) last, so the health `Config` won and the API logged nothing. Measured through the real `serve.main()` (stand-in application factories only): `GET /projects` to the API answered `200` and the child's output had no access line. At `354a9092` the line is written.

The repair, `infra/deploy/serve.py`: the health `Config`/`Server` is built first and the API `Config`/`Server` last, so the API's `access_log=True` is the one that stands. The health app needs the API server before it exists, so `serving` is a small object, `_ApiListener`, whose `.server` is set to the API `Server` right after it is built; `api_server.run()` is the same object. The health thread starts after that binding. No port, log format or `access_log` value changed.

After the repair, the same real-socket run: the child's output contains `"GET /projects HTTP/1.1" 200 OK` (see below).

## Defect 2 — `/readyz` was never withdrawn

uvicorn assigns `started = True` once and never clears it. `handle_exit` sets `should_exit` on SIGTERM (and `force_exit` on a second SIGINT); the listener closes. `_ApiListener` now answers `started and not (should_exit or force_exit)`, and `False` while no server is bound.

Measured through the real `serve.main()` with a 3 s in-flight request holding the drain open: SIGTERM, then a new API connection refused and `/readyz` `200` before; `/readyz` `503` after.

| line of the real-socket run | before (`1aaa7d57`) | after (this lane) |
| --- | --- | --- |
| `API GET /projects` | 200 | 200 |
| draining: API accepts a new connection | False | False |
| draining: `/readyz` | 200 | 503 |
| access-log line for `/projects` present | False | True |

Side effect to know: restoring the order restores the pre-`D-196` logging exactly, so the health plane's own probes (`GET /healthz`, `GET /readyz`) are access-logged again (the health `Config`'s `access_log=False` never took effect there either, because the global logger is shared). That is the behaviour of `354a9092` and was not changed; making the health plane quiet would be a separate settings change.

## Tests

- New `tests/integration/composition/test_serve_logging_order.py` (3 cases), with the real `uvicorn.Config` and a recording `Server` stand-in; the three uvicorn loggers are snapshotted, the access logger is emptied first (so earlier state cannot make a pass vacuous) and everything is restored:
  - `test_the_api_access_log_survives_the_health_plane_config`: handlers non-empty, `propagate` false after `serve.main` built its configs.
  - `test_the_api_config_is_built_after_the_health_plane_config`: the build order is `["health", "api"]`.
  - `test_premise_the_config_built_last_decides_the_access_log`: an `access_log=True` config attaches the handler, a later `access_log=False` strips it, a later `access_log=True` restores it. It is the control that says the two guards above still mean something under the installed uvicorn.
- `tests/integration/composition/test_serve_readiness.py`: the stand-in server gains `should_exit`/`force_exit`; `test_readyz_is_withdrawn_when_the_api_server_starts_to_exit[should_exit|force_exit]` (200 then 503 with `started` still true, `/healthz` 200 throughout) and `test_the_listener_predicate_follows_the_server_it_is_bound_to` (unbound, not started, serving, draining, forced exit).
- `tests/unit/api/test_readiness_waits_for_the_listener.py`: unchanged and green (the plane honours any predicate; the uvicorn-specific predicate lives in `serve.py`).

## Verification

From `/root/projects/PDF-Analysis/.local/worktrees/debt-readyz-errors-fix-01`, `BS` the bootstrap `site-packages`, `.venv` symlinked to the main checkout's, `PYTHONPATH=src:$BS`:

| command | result |
| --- | --- |
| `python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/composition/test_serve_readiness.py tests/integration/composition/test_serve_logging_order.py tests/unit/api tests/integration/composition/test_deployed_stack_probe.py tests/contract/architecture` | 65 passed, exit 0 |
| the three directly touched files (`test_serve_readiness.py`, `test_serve_logging_order.py`, `test_readiness_waits_for_the_listener.py`) | 13 passed |
| governance one-liner for the task file | `[]` |
| `git diff --check` | clean |

No database, S3, docker or network was used. No test in this lane needs one. `ruff` and `mypy` are not installed in this environment and were not run; new code follows the surrounding style and the existing `# type: ignore[no-untyped-def]` pattern for untyped pytest fixtures.

## Every new guard shown red

Red before the repair (the new tests run against `git show 1aaa7d57:infra/deploy/serve.py`): 5 failed, 3 passed. The five: both `test_readyz_is_withdrawn...` cases, the predicate case, `test_the_api_access_log_survives...` (`AssertionError: the process has no access-log handler after serve.main built its configs (built in the order ['api', 'health']); the API's access_log=True was overridden`) and `test_the_api_config_is_built_after...`. The passes are the two old wiring cases and the premise case.

Red under one mutation each on the repaired code (applied, tests run, reverted; `cmp` against the saved fixed file confirmed restoration):

| mutation in `serve.py` | red |
| --- | --- |
| API `Config`/`Server` block moved before the health block (the original defect) | `test_the_api_access_log_survives_the_health_plane_config`, `test_the_api_config_is_built_after_the_health_plane_config` (2 failed, 6 passed) |
| predicate `not (server.should_exit or server.force_exit)` becomes `not server.force_exit` | `...withdrawn...[should_exit]`, the predicate case (2 failed) |
| predicate becomes `not server.should_exit` | `...withdrawn...[force_exit]`, the predicate case (2 failed) |
| unbound listener `return False` becomes `return True` | the predicate case (1 failed) |
| `listener.server = api_server` becomes `listener.server = health` (watching the wrong server) | the two old wiring cases and both `withdrawn` cases (4 failed) |
| premise case, scratch run with `uvicorn.config.Config.configure_logging` patched to a no-op (a uvicorn that no longer touches the logger) | `test_premise_...` (`an access_log=True config attaches the access handler`) and the survives case (2 failed) |

## Risks and limits

- No real-socket test of `serve.py` is added to the suite (the existing pattern is the QA harness, which needs a database lane); the real-socket evidence is the scratch run in the task file (P-04, P-05) and the table above. The wiring and logging tests pin the mechanism with real `uvicorn.Config` objects.
- uvicorn's `limit_max_requests` ends the main loop without setting `should_exit`; `serve.py` configures none, so readiness is not withdrawn on that path. Not modelled.
- The logging case depends on `Config.__init__` configuring the global logger as uvicorn 0.53.0 does; the premise case fails first if a uvicorn upgrade changes that.

## Integrator actions

1. Merge `agent/debt-readyz-errors-fix-01`. `agent/debt-readyz-errors-01` is already an ancestor of the base `1aaa7d57` (`290dcacc`), so there is no ordering constraint with it. No other lane is known to touch `serve.py` or `health.py`.
2. No register change from this lane. If `D-196` is closed on the strength of `DEBT-READYZ-ERRORS-01`, cite this lane for the access-log correction and for `/readyz` withdrawal on drain.
3. Optional on a database lane: start the real stack once and confirm an API request appears in the container log, and that `/readyz` turns `503` on `docker stop` while a slow request is in flight.
