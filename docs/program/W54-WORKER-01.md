# W54-WORKER-01 — hand-back report

- Task: `docs/program/tasks/W54-WORKER-01.md`; grant: `dispatch/W54-PLAN.md` §4 Stage B item 5,
  with the task file's exceptions and additions. Owner ruling `R-105`; freeze decision D-150
  (`W54-FREEZE-01`).
- Branch `agent/w54-worker-01`, worktree `.local/worktrees/w54-worker`, base `196a8d6`
  (`integration/w54`, Stage A merged). Commits `3ff6841` (implementation), `bbac8d3` and `76ce5c6`
  (review fixes); this report is the last commit.
- Checks follow `R-102` (light acceptance). **No container was started.** Every database- or
  object-store-backed test is written and listed in §5 for the owner's window.

## 0. What was built

| Plan item (§3.6, §3.7) | Where |
|---|---|
| `python -m auditmanager.workers serve` (and `health`) on the API image | `workers/__main__.py`, `workers/service.py` |
| Registry: new `wrk` identity per start, heartbeat 20 s, stale 90 s / offline 600 s derived on read, `slots`, `intake_enabled` | `workers/registry.py` |
| `EXECUTION_ROLE ∈ {all, api, worker}`; unset = `all` (W53 behaviour, every test); invalid refused | `bootstrap/settings.py` |
| Only the worker claims: `api` gets a reclaim-only carrier, `all` keeps `DurableCarrier`; the API refuses `worker`, the worker refuses anything else | `runs/carrier.py` (`ReclaimingCarrier`), `bootstrap/composition.py` (`build_worker_runtime`, `WorkerRuntime`) |
| Both reclaim (every 30 s; worker inside its dispatch loop, API in its carrier thread) | `runs/carrier.py`, `workers/service.py` |
| Claim records `lease.worker_id`; refused while that worker's intake is off (`FOR SHARE` on the worker row vs `setWorkerIntake`'s row lock) or the worker is unregistered | `jobs/repository.py` (`JobRepository(worker_id=…)`) |
| `LISTEN/NOTIFY` on a dedicated (pool-detached) connection; `NOTIFY` from `enqueue`, unpause, a requeueing reclaim, intake on; a lost connection is a logged WARNING, the 5 s poll continues, re-establishment is logged | `jobs/repository.py` (`JOB_WAKEUP_CHANNEL`), `workers/service.py` (`JobWakeup`) |
| Drain: `SIGTERM` stops claims and waits ≤ 270 s; compose `stop_grace_period: 300s` | `workers/__main__.py`, `compose.server.yml` |
| Token exemption: the worker starts without `AUDITMANAGER_API_TOKEN` and **refuses** to start with it | `bootstrap/settings.py`, `compose.server.yml` |
| A schema reset under a running worker (registry row gone) stops its intake and makes it exit to re-register | `workers/service.py` |
| `listWorkers` / `setWorkerIntake` real bodies (admin check in the command too; idempotent; journalled `execution.worker_intake_changed`) | `bootstrap/adapters.py`, `workers/commands.py` |
| D-141: commit after the text stage's binding, so the final transaction locks the Lease only in `finish_execution`; the heartbeat extends the lease while the evidence gate runs | `runs/executor.py` (one commit) |
| D-150: reclaim settles a recorded `prepared` effect `not_processed`/`not_sent`; no recorded effect blocks the resume; live unchanged | `jobs/repository.py` `reclaim_expired` |
| D-152: the order-sensitive composition test reclaims, parks every foreign queued Job before and again right before unpausing, and puts its own Job first | `test_the_run_leaves_the_request_thread.py` |
| Compose `worker` service; `deploy.sh` guard `execution-role-declared` (pre-`docker`) and worker health; `verify-deployed.sh` compares the worker container; `reset.sh` stops/starts the worker around drop and restore | `infra/deploy/**` |
| Stub marks removed from the three composition sweeps; `listWorkers` added to the query-surface sweep (it was missing there since SEAL) | tests |
| Light acceptance maps `workers`, `execution`, and `jobs` to their suites | `scripts/light_acceptance.py` |

## 1. Changed files

`git diff --name-only 196a8d6..HEAD` — 52 paths:

- **Source:** `src/auditmanager/workers/{__init__,__main__,commands,public,registry,service}.py`
  (new), `workers/README.md`; `jobs/{repository,lease,events,public,__init__}.py`, `jobs/README.md`;
  `runs/{carrier,public,scope}.py`, `runs/executor.py` (D-141 commit only);
  `bootstrap/{settings,composition,adapters,public}.py`; `api/app.py` (lifespan docstring and
  one log line); `api/routers/execution.py` (module docstring only).
- **Deploy:** `infra/deploy/{compose.server.yml,deploy.sh,reset.sh,verify-deployed.sh,README.md}`,
  `infra/deploy/env/provider.env.example`; `docs/program/DEPLOYMENT_RUNBOOK.md` (§10 rows, new §12).
- **Scripts:** `scripts/light_acceptance.py`.
- **Tests (new):** `tests/integration/workers/{conftest,test_worker_composition,test_worker_service}.py`,
  `tests/integration/jobs/{conftest,test_d141_final_transaction_keeps_the_lease,test_d150_and_worker_claims}.py`,
  `tests/integration/execution/{conftest,test_worker_registry_surface}.py`.
- **Tests (changed):** `tests/contract/test_light_acceptance_command.py`;
  `tests/integration/api/{test_query_surface,test_authorization}.py`;
  `tests/integration/composition/{test_an_absent_parent_is_not_an_empty_page,test_router_answers,test_deploy_script_refusals,test_deploy_image_identity,test_deployed_stack_probe,test_reset_script_refusals,test_session_register_volume,test_the_run_leaves_the_request_thread}.py`;
  `tests/integration/qa_w53/test_queue_and_effect_journal.py` (the D-150 assertion only).
- This report.

## 2. Checks run (container-free), with results

All on the committed tree (`git status --porcelain -uall` empty) unless stated.

| Command | Result |
|---|---|
| `git diff --check 196a8d6..HEAD` | clean |
| `PYTHONPATH=src .venv/bin/python -m compileall -q src/auditmanager tests/integration/{workers,jobs,execution} scripts/light_acceptance.py` | exit 0 |
| `.venv/bin/python -m pytest -q tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py` | **558 passed**, 50 subtests (554 at base + 4 new light-acceptance cases; ALR-05 included) |
| `.venv/bin/python -m pytest -q tests/integration/composition/{test_deploy_script_refusals,test_deploy_image_identity,test_deployed_stack_probe,test_reset_script_refusals,test_session_register_volume,test_every_port_implementation_is_whole,test_proxy_config_follows_checkout,test_minio_image_contract,test_pgvector_image_contract,test_proxy_tls_path}.py tests/integration/workers/test_worker_composition.py` (docker stubbed; the proxy stand is opt-in and skipped) | **252 passed**, 1 skipped (the opt-in stand) |
| the same plus `test_api_token_channel.py test_settings_defaults.py test_composition_root.py`, with a complete **fake** environment (`DATABASE_URL` on closed port 9, fake `S3_*`) | 41 passed — these need only the variables, not the services |
| `bash -n` + `shellcheck` on `deploy.sh`, `reset.sh`, `verify-deployed.sh` | syntax OK; findings identical to base `196a8d6` (deploy 1 SC2016 note, reset 2 SC1087 + 2 SC2016, verify 0) — none new |
| `ruff 0.17.0 check --select F,E9` on every changed `.py` | no new finding (the 6 reported are pre-existing at base: `paginate`, `QueuePosition`, `outcome`, `pathlib`, `json`, an f-string) |
| `pytest --collect-only tests/integration/{workers,jobs,execution}` | 55 collected |

**Shown able to fail:** the base `reset.sh` and `verify-deployed.sh` were put back in the tree and
the new worker cases run: 5 failed (the two reset orderings, three worker-probe cases), the
two no-worker controls passed; files restored with `git checkout --`. The deploy guard has its
deletion mutant in the parametrised `test_deleting_the_guard_removes_the_refusal` and a passing
rollback-shape control. The D-141 test's docstring names its mutation (revert the executor
commit → the heartbeat blocks, `finish_execution` refuses the stale Attempt); it is DB-backed
and runs in the window.

## 3. Contracts

None changed. No migration, no OpenAPI, domain, event or error-catalog edit. `listWorkers` and
`setWorkerIntake` keep SEAL's frozen shapes; `ExecutionWorker.state` is derived on read.
New in-process surface only: `jobs.public.JOB_WAKEUP_CHANNEL`, `JobRepository(worker_id=…)`,
`JobRepository.lease_seconds` / `wake_workers` / `runs_held_by`; `runs.public.{ReclaimingCarrier,
DurableCarrier, run_to_terminal}`; `bootstrap.public.{build_worker_runtime, WorkerRuntime}`;
`AppSettings.{execution_role, worker_state_dir}` and `api_token: str | None` (None only for the
worker); `auditmanager.workers.public`. Execution-journal allow-list gains `worker_id`,
`intake_enabled`. Command type `set_worker_intake` in the command ledger.

## 4. Risks and known limitations

1. **`worker_id` is still in `UNALLOCATED_IN_PC01` — blocked by a contract test outside the
   grant.** `tests/contract/domain_p02/test_identifier_catalog.py::test_the_unallocated_list_covers_the_remaining_deferred_identities`
   requires `"worker_id"` in that list. Removing it from `shared/identity/ids.py` and P02 §9.1
   (both granted) would redden that file (not granted), so neither was changed. The integrator's
   three-line patch: drop `"worker_id",` from `UNALLOCATED_IN_PC01` (`ids.py:321`) and from the
   `WorkerId` docstring's last sentence; drop `` `worker_id`, `` from P02 §9.1
   (`P02_SEAMS.md:757`); drop `"worker_id",` from `required` in that test (line 197).
2. **Nothing DB-backed has run.** 26 new DB-backed tests plus the changed sweeps run first in the
   window (§5). The worker suite uses real threads and timing (bounded waits ≤ 60–90 s, no sleeps
   used as proof except "nothing was claimed in 1.5–2 s").
3. A stopped worker reads `online` for up to 90 s, then `stale`, then `offline`: the registry can
   only move `heartbeat_at` forward and there is no deregistration column. Every start adds one
   row; there is no retention.
4. `deploy.sh` now waits up to 120 s for the worker's first health check, and recreating the worker
   during a long run can take up to `stop_grace_period` (300 s). A run still in flight after the
   270 s drain is left to lease expiry: resumed if recorded, failed `provider_outcome_unknown` if
   a live call was prepared or answered.
5. The "killed worker" tests write the state a `SIGKILL` leaves (a lease naming a silent worker,
   past expiry); a real process kill and a second worker are `W54-REHEARSAL-01`'s *worker* item.
6. `ReclaimingCarrier.drain` waits for every outstanding Job in the database, not only those the
   process accepted (the same rule as `DurableCarrier.drain` under W53).
7. `listWorkers` pages by `started_at` (immutable) newest first, not by state; WORKERS-WEB groups
   online/stale above offline.
8. The worker refuses to start with `AUDITMANAGER_API_TOKEN` present. A developer running
   `python -m auditmanager.workers serve` against a lane must unset it (`env -u …`).

## 5. Integrator instructions

1. Read the diff and this report. Expected overlaps with `W54-CUSTODY-01`:
   `jobs/repository.py` (CUSTODY's D-142 settlement around `settle_terminal_provider_effects`;
   this lane did not touch that method or its SQL) and
   `tests/integration/qa_w53/test_queue_and_effect_journal.py` (this lane changed only
   `test_lease_reclaim_journals_the_effect_outcome`'s final two assertions). Shared with SEAL's
   merged edits: `bootstrap/adapters.py` (stub bodies replaced), the three sweeps.
2. Apply limitation 1's patch if the integrator holds that contract-test path, or record it.
3. **Heavy steps, owner window only** (`free` ≥ 6 GiB available, `df` ≥ increment + 3 GiB, measured
   just before): this lane's private stack on PostgreSQL `57130`, S3 `60730/60731`, a lane `.env`,
   `make up && make migrate` (head `0019_execution_workers`), then from the worktree, one pytest
   at a time:

   ```sh
   set -a; . ./.env; set +a
   .venv/bin/python -m pytest -q tests/integration/jobs tests/integration/execution
   .venv/bin/python -m pytest -q tests/integration/workers
   .venv/bin/python -m pytest -q tests/integration/qa_w53 tests/integration/runs
   .venv/bin/python -m pytest -q tests/integration/api/test_query_surface.py \
       tests/integration/api/test_authorization.py tests/integration/api/test_role_register.py
   .venv/bin/python -m pytest -q tests/integration/composition
   # D-152's own check: the combined run passes twice in a row on one lane database
   .venv/bin/python -m pytest -q tests/integration/runs tests/integration/composition
   .venv/bin/python -m pytest -q tests/integration/runs tests/integration/composition
   ```

   Expected red unrelated to this lane: SEAL's `tests/integration/db/test_schema_invariant_inventory.py`
   until resealed. `W53's drivers under all`: every suite above other than `workers` builds its
   applications without `EXECUTION_ROLE`, i.e. `all`.
4. Stop the lane stack by its own compose project; kill nothing by pattern.

## 6. Deploy-side changes the owner must know

- **A new long-running service `worker`** in `compose.server.yml`: the `${ALPHA_INSTANCE}-api`
  image, `python -m auditmanager.workers serve`, no port, no volume, a 1 MiB tmpfs at
  `/run/auditmanager` (uid 10001), health check `python -m auditmanager.workers health`,
  `stop_grace_period: 300s`, `restart: unless-stopped`, `env/provider.env` like the API.
- **Environment:** the worker gets the API's names **except `AUDITMANAGER_API_TOKEN`**, plus the
  literals `EXECUTION_ROLE: worker` and `AUDITMANAGER_WORKER_STATE_DIR: /run/auditmanager`. The API
  gains the literal `EXECUTION_ROLE: api`. **Nothing is added to `alpha.env`.**
- `deploy.sh` refuses (exit 3, before any `docker` call) a compose file whose `api` or `worker`
  lacks the literal role, names the wrong one, or runs `api` with no worker; it waits for the
  worker's health. `verify-deployed.sh` also compares the worker container against the tree.
  `reset.sh` stops the worker before dropping or restoring the schema and starts it afterwards.
- **Rollback (§3.10):** a forward fix with `EXECUTION_ROLE: all` on `api` and no `worker` service
  is W53's in-process execution; `deploy.sh` accepts exactly that shape.
- Runbook: `DEPLOYMENT_RUNBOOK.md` §12; deploy README "The worker service — `R-105`".

## 7. Containment

- `git diff --name-only 196a8d6..HEAD`: the paths in §1, each inside the `W54-WORKER-01` grant
  (plan §4 Stage B item 5 plus this report). `jobs/repository.py`: no hunk in
  `settle_terminal_provider_effects` or `_SETTLE_TERMINAL_PROVIDER_EFFECTS` (D-142 is CUSTODY's).
  `qa_w53/test_queue_and_effect_journal.py`: one hunk, the D-150 assertion.
- Not touched: `contracts/**`, `db/migrations/**`, `shared/identity/ids.py`, `P02_SEAMS.md` (see
  limitation 1), `DEBT_REGISTER.md`, `OWNER_RULINGS_*.md`, `PORT_REGISTRY.md`, root dependency and
  lock files, `Dockerfile.api`, `serve.py`, other worktrees, refs, tags, the stand, `.local/norms/**`.
- No container, no push, no merge, no tag, no stash, no process killed. `git status --porcelain -uall`
  is empty after this commit.
