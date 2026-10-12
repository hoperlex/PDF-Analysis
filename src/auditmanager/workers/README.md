# `workers` boundary

The worker service and its registry (owner ruling `R-105`, `W54-WORKER-01`). Remote
execution never becomes a metadata writer: a worker is a local process of the same release,
against the same database, and the Job/Attempt/Lease authority stays in `jobs`.

| Module | What it owns |
|---|---|
| `registry.py` | the only writer of the `worker` table (migration `0019`): register, heartbeat, intake, reads with the derived state |
| `commands.py` | `set_worker_intake` — the administrator's switch, idempotent under the command ledger |
| `service.py` | `WorkerService` (register, `LISTEN`, claim into slots, reclaim, drain) and `JobWakeup` |
| `__main__.py` | `python -m auditmanager.workers serve` and `health` |
| `public.py` | the cross-context surface |

The claim itself is `jobs`' (`JobRepository(worker_id=…)`), which records the worker on the
Lease and refuses while that worker's intake is off. The run is `runs`' (`run_to_terminal`),
handed to the service by the composition root (`bootstrap.build_worker_runtime`).

Create subfolders/classes only when a real use case requires them. Keep internal APIs private by default.
