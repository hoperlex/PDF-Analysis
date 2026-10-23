# EXEC-SSH-TUNNEL-CROPS-01 — handoff

Base: `d4cd2ac3` (`origin/dev`). Target: `origin/dev` only.

## Result

`http_api` over `ssh_tunnel` now serves both `openai_chat` and
`anthropic_messages`. The worker validates the SSH destination, dials its
checked IP with a pinned host key, opens a short-lived loopback forward, then
uses the existing HTTP image adapter. The configured HTTP host remains the
Host header and TLS server name; only its TCP dial goes to the forward. One
verified PNG is delivered as the flavour's image content block.

The adapter opens the sealed HTTP key and SSH key for their distinct bound
destinations. A successful probe tests both keys and the actual HTTP model.
Readiness requires its request time to be after both current secrets' issue
times. Rotating either secret invalidates the old `ok` probe without a schema
change. Missing or unreadable keys, an unpinned/changed host key, an invalid
PNG and a redirected HTTP destination all fail closed. No route changes.

## Changed files

| Path | Purpose |
| --- | --- |
| `docs/program/tasks/EXEC-SSH-TUNNEL-CROPS-01.md` | Task boundary and frozen inputs |
| `src/auditmanager/executors/kinds.py` | Register tunnel and extra-secret factory input |
| `src/auditmanager/executors/resolver.py` | Open both bound secrets for one Attempt |
| `src/auditmanager/executors/ssh_tunnel_adapter.py` | Short-lived tunnel and original HTTP identity |
| `src/auditmanager/executors/ssh_probe.py` | SSH host and HTTP model probe through tunnel |
| `src/auditmanager/executors/probe_runner.py` | Open second key and dispatch tunnel probe |
| `src/auditmanager/executors/usability.py` | Invalidate probes issued before a key rotation |
| `tests/unit/executors/test_ssh_tunnel_adapter.py` | Both HTTP flavours, PNG, secrets, rotation, pin |
| `tests/integration/executors/test_ssh_local_image.py` | Real local OpenSSH command and HTTP tunnel smoke |
| `docs/program/DEPLOYMENT_RUNBOOK.md` | Operator setup and key rotation rule |
| `docs/program/CURRENT_STATE.md` | Served transport status |
| `docs/program/EXEC-SSH-TUNNEL-CROPS-01.md` | This report |

## Verification

- Full `tests/unit/executors` with local TCP sockets: **435 passed** before
  the final repr-sentinel addition. The focused tunnel suite after that
  addition and host-key failure check: **11 passed**.
- `EXEC_LOCAL_SSHD=1 ... test_ssh_local_image.py`: **1 passed** against a
  temporary OpenSSH server and local HTTP model. It tested the command PNG,
  command probe, tunnel PNG and tunnel probe. No external/paid model call.
- Python compile and `git diff --check`: **passed**.
- The beta `make gate` remains deferred under `R-135`, as the owner directed
  for this hotfix.

## Contracts, risks and integration

No API contract, migration, dependency/lock file, composition root, generated
client, global style or server compose file changed. The existing
`executor_probe.requested_at` and `executor_secret.set_at` bind readiness to
both secrets. A local PostgreSQL integration run is unavailable because the
local database is down and Docker cannot start under this host's snap setup;
the readiness rule is covered with store-level tests. The live stand and its
real model have not been probed by this task.

The remote account should allow port forwarding only to the saved HTTP
target using `permitopen`. A custom target resolved by the SSH host remains
under that remote restriction. The forward is opened per call and closed at
the end; connection setup adds latency. TLS checks the original HTTP host.

Integrator: publish this exact commit to `origin/dev` by fast-forward, deploy
the worker image, enter both secrets in «Подключения», confirm the SSH host
key, run «Проверить» after the last secret change, and only then select the
connection in «Назначения». No user route is changed automatically. The
separate graphical-analysis stage still needs its approved AR prompt and
evidence policy from the other session before any crop task can run.

Rollback: remove the tunnel route or revert the commit. No data migration.
`origin/main` is outside this task; the owner said they will transfer the
verified development candidate themselves.
