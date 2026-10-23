# EXEC-SSH-CROPS-01 — handoff

Base: `4ad7e470b493bd97fbfaf755037216c205e13f5d` (`origin/dev`).
Publication target: `origin/dev`; no authority for `origin/main`.

## Result

The `ssh_command` executor is wired into routing and probes. A call checks
the selected crop's PNG bytes against its saved descriptor, checks the SSH
destination, dials its checked IP, requires the revision's pinned host key,
and sends one bounded JSON task on stdin. The remote `custom_command` or the
supplied Claude Code forced command returns a bounded JSON answer with its
reported model. The existing run-level identity check still applies. A probe
first shows an unpinned host key for operator confirmation and never sends a
model task until the pin matches. It checks the reported model and, when a
metered price and cost are available, the pinned rate. No route is changed.

The supplied `ssh-forced-command.sh` turns a verified PNG into a Claude Code
stream-JSON image content block. It preserves the output JSON schema and
normalizes the CLI's single `modelUsage` model, token counts and cost. An
answer with no model or several models fails closed. The custom-command
profile accepts the same JSON task and must return the documented JSON result.

## Files

| Path | Change |
| --- | --- |
| `docs/program/tasks/EXEC-SSH-CROPS-01.md` | Task boundary and frozen inputs |
| `src/auditmanager/executors/ssh_adapter.py` | Checked PNG task, bounded SSH call, typed answer |
| `src/auditmanager/executors/ssh_probe.py` | Host-key pin and model/rate probe |
| `src/auditmanager/executors/kinds.py` | Register `ssh_command` factory |
| `src/auditmanager/executors/probe_runner.py` | Open SSH purpose and record observed key |
| `src/auditmanager/executors/probes.py` | Carry the observed host key in probe result |
| `src/auditmanager/executors/usability.py` | Describe the served set |
| `tools/executor-runner/ssh-forced-command.sh` | Stream-JSON image and normalized result |
| `tests/unit/executors/test_ssh_adapter.py` | Crop, destination, pin and model cases |
| `tests/unit/executors/test_ssh_forced_command.py` | Stub CLI text, PNG, schema and model cases |
| `tests/unit/executors/test_ssh_wiring.py` | Secret purpose and observed-key persistence |
| `tests/unit/executors/test_pull_wiring.py` | Registry expectation after SSH registration |
| `tests/integration/executors/test_ssh_local_image.py` | Opt-in real local `sshd` PNG/probe smoke |
| `docs/program/DEPLOYMENT_RUNBOOK.md` | Operator setup and tunnel limit |
| `docs/program/EXEC-SSH-CROPS-01.md` | This report |

## Checks

- `python -m pytest -q tests/unit/executors` — **426 passed** in a
  socket-enabled local test environment.
- `EXEC_LOCAL_SSHD=1 python -m pytest -q
  tests/integration/executors/test_ssh_local_image.py` — **passed** against
  a temporary loopback OpenSSH server; it is terminated by the fixture.
- `bash -n tools/executor-runner/ssh-forced-command.sh`, Python compile,
  `git diff --check` — **passed**.
- Full beta `make gate` is deferred under `R-135`; the owner explicitly waived
  the full gate for this hotfix. `ruff` is not installed in the local venv.

## Contracts, risks, integration

No API contract, migration, root dependency/lock file, composition root,
global style or generated client changed. The image descriptor and
`ModelRequest.image_bytes` contract are unchanged. Roll back by removing an
SSH route or reverting this commit; no data migration is needed.

The real Claude CLI is absent on this development machine, so the wrapper
was checked with a stub CLI and the transport with a real local `sshd`; a
production `claude --version` and one real structured/image response remain
operator checks before assigning that profile. A `custom_command` remote
program must implement the JSON envelope exactly. Existing SSH servers need
the public key installed in `authorized_keys` and a saved, confirmed host
key. The application image already contains `openssh-client`.

`http_api` over `ssh_tunnel` remains unserved in this slice. It needs two sealed
secrets. The follow-on slice can use the probe request time to require that a
successful check began after both current secrets were issued, preventing a
stale `ok` after either key rotates without a migration. The image
stage still cannot create crop tasks until the other session supplies the
approved AR prompt and evidence policy; this slice changes only delivery.

Integrator: merge this candidate into `origin/dev`, deploy its worker image,
configure and probe the SSH command connection, then assign it in
«Исполнители → Назначения» if desired. Preserve existing OpenRouter and Codex
routes unless an administrator explicitly changes them. `origin/main` and
production deployment are outside this task.
