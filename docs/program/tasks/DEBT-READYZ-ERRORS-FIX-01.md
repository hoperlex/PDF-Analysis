# Task DEBT-READYZ-ERRORS-FIX-01 — the API access log comes back; `/readyz` is withdrawn when the API starts draining

task_id: DEBT-READYZ-ERRORS-FIX-01
status: completed in development candidate

## Outcome

An independent judge found two defects in the `serve.py` change of `DEBT-READYZ-ERRORS-01` (`D-196`). Both were re-proved on the base tree through the real `serve.main()` and both are fixed:

- **Defect 1 (regression, confirmed):** the API access log was silenced. `uvicorn.Config.__init__` reconfigures the process-global `uvicorn.access` logger, and a `Config` with `access_log=False` (the health plane's) empties its handlers. The `D-196` change built the API `Config` first and the health `Config` last, so a `GET` to the API answered `200` and logged nothing. `serve.main` now builds the health plane's `Config` first and the API's last, as at `354a9092`; the health app reaches the API server (which does not exist yet) through a small late-bound object, `_ApiListener`, bound to the same `Server` that `run()` blocks on.
- **Defect 2 (low):** `/readyz` was never withdrawn. uvicorn never clears `Server.started`; a SIGTERM sets `should_exit` (a second SIGINT sets `force_exit`) and the listener closes, but `started` stays true, so `/readyz` kept answering `200` for a port that refuses new connections. The predicate is now `started and not (should_exit or force_exit)`.

## Depends on

- `DEBT-READYZ-ERRORS-01` — completed in the development candidate (its commit `290dcacc` is in the history of the base `1aaa7d57`); this task corrects its `serve.py` change.

## Frozen inputs

- domain contract: unchanged (27 error codes)
- API contract: unchanged (92 paths / 104 operations / 300 schemas); the health plane is off the contract document by design (`T-3`)
- analysis/comparison/event contract: unchanged
- migration head: `0032_ar_v3_run_group`
- base commit: `1aaa7d57fe719f8859bee7d74065d330a43c1412` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: on the base tree the API access log is empty after `serve.main` builds its configs, and `/readyz` answers `200` while the API listener is closed

### P-01 — the construction order in `serve.py` on the base tree

- captured_at: 2026-10-26
- command: `git show 1aaa7d57:infra/deploy/serve.py | grep -nE "uvicorn\.Server\(|uvicorn\.Config\(|build_health_app\(|threading\.Thread|api_server"`
- captured_output:
  ```text
  28:handed ``lambda: api_server.started`` and answers ``503`` until then. ``/healthz`` does not
  98:    api_server = uvicorn.Server(
  99:        uvicorn.Config(api_app, host=bind_host, port=api_port, access_log=True)
  101:    health_app = build_health_app(application, serving=lambda: api_server.started)
  103:    health = uvicorn.Server(
  104:        uvicorn.Config(health_app, host=bind_host, port=health_port, access_log=False)
  106:    threading.Thread(target=health.run, name="health-plane", daemon=True).start()
  114:    api_server.run()
  ```
- interpretation: the API `Config` (`access_log=True`, line 99) is built before the health `Config` (`access_log=False`, line 104), so the health `Config` is the last to configure logging.

### P-02 — what uvicorn does with the global logger, and what it does on SIGTERM

- captured_at: 2026-10-26
- command: `grep -nE "self\.(started|should_exit|force_exit) = |def handle_exit" /root/projects/PDF-Analysis/.venv/lib/python3.12/site-packages/uvicorn/server.py; sed -n 351,356p /root/projects/PDF-Analysis/.venv/lib/python3.12/site-packages/uvicorn/server.py; sed -n 427,430p /root/projects/PDF-Analysis/.venv/lib/python3.12/site-packages/uvicorn/config.py`
- captured_output:
  ```text
  72:        self.started = False
  73:        self.should_exit = False
  74:        self.force_exit = False
  205:        self.started = True
  351:    def handle_exit(self, sig: int, frame: FrameType | None) -> None:
  354:            self.force_exit = True  # pragma: full coverage
  356:            self.should_exit = True
      def handle_exit(self, sig: int, frame: FrameType | None) -> None:
          self._captured_signals.append(sig)
          if self.should_exit and sig == signal.SIGINT:
              self.force_exit = True  # pragma: full coverage
          else:
              self.should_exit = True
          if self.access_log is False:
              logging.getLogger("uvicorn.access").handlers = []
              logging.getLogger("uvicorn.access").propagate = False
  ```
- interpretation: `started` is assigned `True` once (line 205) and never cleared; SIGTERM sets `should_exit`, a second SIGINT sets `force_exit`. `Config.configure_logging` empties the handlers of the global `uvicorn.access` logger when `access_log` is false (uvicorn 0.53.0).

### P-03 — the judge's reproduction of the order, run again

- captured_at: 2026-10-26
- command: `for o in new old; do /root/projects/PDF-Analysis/.venv/bin/python -I order.py $o; done` (the judge's `order.py`, copied to the lane scratch directory; `new` builds the API `Config` first, `old` builds it last)
- captured_output:
  ```text
  == order=new
  status 200
  == order=old
  INFO:     127.0.0.1:58616 - "GET /projects HTTP/1.1" 200 OK
  status 200
  ```
- interpretation: with the API `Config` first, a `GET` answered `200` and no access-log line was written; with it last the line is written.

### P-04 — both defects through the real `serve.main()` on the base tree

- captured_at: 2026-10-26
- command: `cd <lane worktree at 1aaa7d57> && /root/projects/PDF-Analysis/.venv/bin/python -I drive.py "$PWD" 28810 28811` (scratch, not committed: `drive.py` spawns `child_main.py`, which loads this tree's `infra/deploy/serve.py`, stands in only `create_app`/`create_asgi_app` with a bare ASGI app, and runs the real `main()` with two real uvicorn servers. The parent polls `/readyz` until `200`, sends `GET /projects` to the API, starts a 3 s `GET /slow`, sends SIGTERM to the child it started, then probes a new API connection and `/readyz` while the slow request keeps the server draining, and reads the child's output)
- captured_output:
  ```text
  API GET /projects -> 200
  draining: API accepts a new connection -> False
  draining: /readyz -> 200
  --- child output ---

  access-log line for /projects present: False
  exit code -15
  ```
- interpretation: the API answered `200` and logged nothing (defect 1); while draining, a new API connection was refused and `/readyz` still answered `200` (defect 2). The child's output has no `GET` line at all (the blank line after the header is the filtered output).

### P-05 — the same script on the pre-`D-196` tree (`354a9092`), for comparison

- captured_at: 2026-10-26
- command: `PYTHONDONTWRITEBYTECODE=1 /root/projects/PDF-Analysis/.venv/bin/python -I drive.py /root/projects/PDF-Analysis/.local/worktrees/base-354a 28812 28813`
- captured_output:
  ```text
  API GET /projects -> 200
  draining: API accepts a new connection -> False
  draining: /readyz -> 200
  --- child output ---
  INFO:     127.0.0.1:54256 - "GET /readyz HTTP/1.1" 200 OK
  INFO:     127.0.0.1:38652 - "GET /projects HTTP/1.1" 200 OK
  INFO:     127.0.0.1:52212 - "GET /readyz HTTP/1.1" 200 OK
  INFO:     127.0.0.1:38664 - "GET /slow HTTP/1.1" 200 OK
  access-log line for /projects present: True
  exit code -15
  ```
- interpretation: at `354a9092` the access line is written. The health plane's own probes are logged too there, because the API `Config` re-attached the handler on the global logger and the health `access_log=False` therefore never took effect; that is the pre-`D-196` behaviour and is restored unchanged here (a settings change was out of scope).

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `infra/deploy/serve.py`
- `src/auditmanager/api/health.py`
- `tests/integration/composition/test_serve_readiness.py`
- `tests/integration/composition/test_serve_logging_order.py`
- `tests/unit/api/test_readiness_waits_for_the_listener.py`
- `docs/program/tasks/DEBT-READYZ-ERRORS-FIX-01.md`
- `docs/program/DEBT-READYZ-ERRORS-FIX-01.md`

## Forbidden hotspots

Contracts, migration head, root dependency/lock files, `Makefile`, every `infra/**` file other than `infra/deploy/serve.py`, the composition root (`src/auditmanager/bootstrap/**`, `web/src/_app/providers.tsx`), `web/**`, global styles, `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, `origin/main`, tags and the deployment host.

## Non-goals

No change of ports, log formats, `access_log` values, environment variables or the `200`/`503` bodies of `/readyz`; no change to `/healthz`. No register edit (the integrator owns `D-196`), no `infra/deploy/README.md` edit. No drain-by-`limit_max_requests` handling (uvicorn ends the loop without setting `should_exit` there; no `limit_max_requests` is configured by `serve.py`).

## Deliverables

- `infra/deploy/serve.py`: the health `Config`/`Server` built first, the API `Config`/`Server` built last, `_ApiListener` (a callable holding the API server once it exists; `False` until then) passed as `serving`, `listener.server = api_server` where `api_server` is the object `run()` blocks on, the predicate `started and not (should_exit or force_exit)`. The health thread starts after the binding, so it never reads an unbound listener.
- `src/auditmanager/api/health.py`: docstring only, `serving` is "bound and still accepting".
- `tests/integration/composition/test_serve_logging_order.py` (new, 3 cases, real `uvicorn.Config`, global logger state snapshotted and restored): the access logger has handlers and `propagate` is false after `serve.main` builds its configs; the configs are built in the order health, API; a premise case showing the last `Config` built decides the access log.
- `tests/integration/composition/test_serve_readiness.py`: the stand-in server gains `should_exit`/`force_exit`; two parametrized cases (`should_exit`, `force_exit`) show `/readyz` going `200` to `503` with `started` still true and `/healthz` staying `200`; one case drives `_ApiListener` through unbound, not started, serving, draining, forced exit.
- This file and `docs/program/DEBT-READYZ-ERRORS-FIX-01.md`.

## Required tests

- `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); ln -s /root/projects/PDF-Analysis/.venv .venv; PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/integration/composition/test_serve_readiness.py tests/integration/composition/test_serve_logging_order.py tests/unit/api tests/integration/composition/test_deployed_stack_probe.py tests/contract/architecture`: all pass (result in the report).
- Every new case red under a quoted mutation (report).
- Governance one-liner for this file prints `[]`.
- `git diff --check` and the exact allowed-path inventory.

## Integration contract

`/readyz` answers `200` only while the API server has started and has not been told to exit; it answers `503` `{"status":"starting"}` before the listener is up and again from the moment SIGTERM (or a forced exit) reaches the API server. `/healthz` is unchanged. The API access log is written again for every API request, as before `D-196`. No consumer changes: nothing in `infra/` routes on `/readyz` (the compose healthcheck reads `/healthz`).

## Failure/idempotency/security cases

An unbound `_ApiListener` answers `False` (never ready). An exception from the predicate is still a `500` from the plane, never a ready answer (pinned by the existing unit case). The health thread starts only after the API server is bound, so no request can observe an unbound listener in production.

## Rollback / feature flag

Forward-revert. No flag.

## Handoff

- changed files: `infra/deploy/serve.py`, `src/auditmanager/api/health.py`, `tests/integration/composition/test_serve_readiness.py`, `tests/integration/composition/test_serve_logging_order.py` (new), this file and the report
- commands/results: see `docs/program/DEBT-READYZ-ERRORS-FIX-01.md`
- known limits: no real-socket test in the suite (the real-socket evidence is the scratch run in P-04 and the report); `limit_max_requests` exits are not modelled
- integration notes: `agent/debt-readyz-errors-01` is already an ancestor of the base, so no ordering constraint; no register row is touched by this task
