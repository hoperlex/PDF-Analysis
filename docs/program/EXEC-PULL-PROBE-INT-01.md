# EXEC-PULL-PROBE-INT-01 — worker probe wiring for pull connections

## Diagnosis

On 2026-10-23 the production UI showed one worker online, heartbeating and
accepting new runs. Three checks of the `Codex` pull connection stayed in
`requested` and finished as `no_worker`; during the same interval the local
Codex agent made authenticated claims and received empty queues. This
distinguishes the application worker's probe loop from the outbound agent.

At base `3bc7dae1`, `build_worker_runtime` omitted its `probe_runner` when
`secrets_private_ring` was absent. `WorkerService.start` then omitted the probe
loop, while heartbeat and run dispatch still ran. A pull probe needs no key;
`ProbeRunner._evaluate` handles it before `open_secret`. The production
worker's private-ring setting has not been independently inspected, so this
is a code defect consistent with the observed symptoms, not yet a proven
production root-cause statement.

## Change

The composition root now constructs a probe runner with an optional ring in
both cases. The existing `open_secret` path continues to report
`secret_unreadable` for a keyed connection without private material. No API,
database, contract, migration, token, routing or UI behavior changed.

## Verification

| Check | Result |
| --- | --- |
| `tests/unit/executors/test_probe_loop.py tests/unit/executors/test_pull_wiring.py` | 20 passed |
| `tests/unit/executors` with loopback sockets allowed | 389 passed |
| `git diff --check` | passed |
| Production check after deployment | pending |

The first full unit run inside the network-restricted sandbox had 44 socket
permission failures at `127.0.0.1`; rerunning with local loopback allowed
passed all 389 tests.

## Publication and acceptance

This task publishes its clean candidate to `origin/dev`. The main deployment
still requires the owner's separate instruction for the exact candidate and
the complete `make gate` under `MAIN_AUTODEPLOY_POLICY.md`. After deployment,
press «Проверить» on `Codex`: the worker must take the probe, the agent must
receive the synthetic task, and the UI must finish with «готово» before any
route is assigned.

## Handoff

- Changed paths: `src/auditmanager/bootstrap/composition.py`,
  `tests/unit/executors/test_probe_loop.py`, this report and
  `docs/program/tasks/EXEC-PULL-PROBE-INT-01.md`.
- Contracts: unchanged, version `1.0.0`; API 87/99/284; migration head
  `0031_executor_pull_channel`.
- Forbidden hotspots: `contracts/**`, migrations, root dependency and lock
  files, global styles, `web/**`, `infra/**`, and other composition files were
  not edited.
- Operational limit: production acceptance remains pending; the worker
  environment and its probe logs require deployment-host access if the check
  still fails after rollout.
