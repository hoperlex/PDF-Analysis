STATUS: step 6 report written, checks in the table below (16:15 +05)

# EXEC-CANDIDATE-2 - the pull channel wired end to end (R-144b basic acceptance)

Branch `agent/exec-cand2`, worktree `.local/worktrees/exec-cand2`, built on candidate 1
(`89bd8b1b`, then `agent/exec-line-01` again at `928a6aba`). It adds `agent/exec-pull-01`
(`EXEC-PULL-01`, the server lane: migration `0031`, six runner operations, the runner-token
principal, the pull adapter, the nginx throttles) and wires it into the run path, the worker's
probe loop and the «Подключения» screen. Owner rulings `R-143`, `R-144`, `R-144b` (basic functional
checks, no live journey, no paid call). Every run below was `nice -n 19 ionice -c3`, one test
process at a time, memory available and disk available checked against 2500 MiB before each
(a small wrapper waited when either was short). The lane stack was `auditmanager-exec-line`
(57660 / 61460 / 61461, database `auditmanager_exec_line`, bucket `auditmanager-exec-line`),
migrated to `0031_executor_pull_channel`; the stray database `auditmanager_exec_pull` was dropped.

## What works end to end

An administrator creates a `pull` connection (client `claude_code_session` or `agent`, a pinned
model, billing `not_metered`), issues a runner token in the card (shown once, copy button), presses
«Проверить», routes «Анализ текста» to it, and starts a run. Proven with real PostgreSQL and S3, no
model and no network beyond loopback:

1. **The worker takes the probe.** `ProbeRunner` hands a `pull` probe to a thread of its own
   (`PULL_PROBE_THREADS` = 4; a runner needs up to 240 s and the one probe thread would starve the
   HTTP probes) and calls `probe_pull`. The `api` sweep no longer ends a running pull probe before
   its 240 s window (`PULL_PROBE_WINDOW_SECONDS`). A runner answering the echo task gives `ok`
   (`identity_basis: declared`); none gives `no_runner_online` and the connection cannot be routed.
2. **A route to it is allowed on a probe taken on no secret** (`is_probed_ok` asks for
   `secret_id IS NULL` for a kind that keeps no key). A start freezes its revision.
3. **The resolver builds the task adapter** (`register_channel_kind`; `bind_connection` takes a
   `KindRuntime`, no key is opened). The run's `text_analysis` call becomes an `executor_task`
   joined to the run, the Attempt and the model call; the deadline is
   `min(revision deadline, watchdog remaining - 60 s)` from the Attempt's context.
4. **The runner answers** (a played runner through the real application, and `agent.py` as a
   subprocess): the run is `published`, the call row has `identity_basis: declared`, provider =
   the client (`claude_code_session` / `agent`), `cost_basis: unmetered`, cost 0; the run's cost is
   `0` with basis `unmetered`.
5. **Nobody answers**: never claimed -> `dependency_unavailable`, `dependency: no_executor_online`,
   effect `not_processed` / `not_sent`, the task `expired` with `claim_count` 0, no call row, no
   cost, no other connection. Claimed and not answered, a revoked token, or a runner `fail` ->
   effect `outcome_unknown`, `dependency: executor_deadline` / `executor_task_failed`.
6. **The agent**: `tools/executor-runner/agent.py` runs as a subprocess against the lane app (uvicorn
   on a loopback port, `/api/v1` mounted, real seam and rows) with a stub local command; it answers
   the probe, then a real run's `text_analysis` task. A garbage command output fails the task
   (`outcome_unknown`); a declared model other than the pin is failed as `model_mismatch` before the
   command runs. The token appears in neither stream of the agent.
7. **The screen** (card of a `pull` connection): «Выпустить токен» (lifetime in days, 1 to 365),
   the token in a read-only box with «Скопировать» and a warning that it is shown once and not shown
   again; the list (prefix, issued, expires, revoked, last seen and its address); «на связи» when a
   token was seen less than 60 s ago, in the card's heading and in the panel; the number of open
   tasks; «Отозвать» with a confirmation. An expert reads all of it and is given no control.

## Changed files (reason)

| Area | Files | Why |
|---|---|---|
| merge of the PULL lane | whole of `agent/exec-pull-01` | conflicts: `DEPLOYMENT_RUNBOOK.md` (both section 14s kept; the runner channel is now section 15), `composition.py` (both imports), `executors/README.md` (both module lists), `test_every_port_implementation_is_whole.py` (both ports); `contracts/domain/v1/identifiers.schema.json` merged cleanly but listed the five executor ids twice (candidate 1's fix and the PULL lane's own): the duplicates removed. The web client and `FRONTEND_LOCK.json` needed no regeneration (`frontend-lock` guard green). |
| kind registry | `executors/kinds.py`, `runtime.py` | `register_channel_kind`, `KindRuntime`; `pull` registered |
| resolver and usability | `executors/resolver.py`, `usability.py` | channel kinds build from the runtime with no key; the probe rule asks for no secret |
| probe loop | `executors/probe_runner.py`, `model.py`, `repository.py` | pull probe branch on its own thread; the sweep window |
| composition | `bootstrap/composition.py`, `providers.py` | the worker's session factory and engine reach the pull adapter and the probe loop |
| web | `entities/executor-connection/**` (runner-token model, readiness: `pull` is served, words, refusals), `features/manage-executor-connection/**` (hooks, `RunnerTokenPanel`, `IssuedTokenView`, pull hints), `widgets/executor-connections/ui/connection-card.tsx` | step 3. The panel lives in the existing feature slice (its hooks are already in the dashboard-invalidation map as `false`), not in a new `issue-runner-token` slice |
| docs | `CURRENT_STATE.md` (87 / 99 / 284, head `0031`), runbook section 15, `executors/README.md`, `tools/executor-runner/README.md` (button labels) | step 5 |
| tests (new) | `tests/unit/executors/test_pull_wiring.py`, `tests/integration/executors/test_pull_run_path.py`, `test_agent_e2e.py`, `web/tests/unit/workers/executor-runner-tokens.test.ts` | the evidence above |
| tests (changed) | `test_http_operations.py`, `test_http_probe_worker.py` (the unserved kind is now `ssh_command`), `test_authorization.py` (`runner.py` joins the routers that read the subject), web `seam-operations`, `pc01-error-codes`, `authorization-state` (the two token writes are keyed; the four runner operations are 401-only), fixtures, `rendered-language` guard (the issued-token box), `executor-commands`, `executor-connections`, `tests/e2e/pc01/journey/manifest.json` (comment only: no new read, the two writes are named) | the merged contract and the served kind |

## Commands, exit codes, counts

| # | Command | Exit | Result |
|---|---|---|---|
| 1 | `git diff --check origin/dev...HEAD` | 0 | clean |
| 2 | `python3 -m pytest -q -p no:cacheprovider tests/unit/executors tests/unit/executor_runner` | 0 | 484 passed, 68 s |
| 3 | `python3 -m pytest -q -p no:cacheprovider tests/contract --ignore=tests/contract/test_cp00_candidate.py --ignore=tests/contract/test_cp00_final_state.py --ignore=tests/contract/test_validate_bootstrap.py tests/e2e/test_pc01_journey_conformance.py` | 0 | 1111 passed, 19283 subtests, 86 s. Earlier on the same tree it showed two reds, both mended: the clean-tree test (uncommitted `CURRENT_STATE.md`) and `test_process_acceleration` (the live entry was **122 lines on candidate 1's tree**, the budget is 120; it is 120 now) |
| 4 | `npm --prefix web run typecheck` / `lint -- --quiet` | 0 / 0 | clean |
| 5 | `npm --prefix web test -- --run tests/unit/workers` | 0 | 9 files, 143 tests |
| 6 | `npm --prefix web test -- --run tests/guards` | 0 | 21 files, 288 tests, 105 s (before the candidate 1 merge) |
| 7 | `npm --prefix web test -- --run tests/unit/styles`, `tests/contract`, `tests/unit/api` | 0 | 57, 184 and 130 tests |
| 8 | whole web suite `nice -n 10 npm --prefix web test -- --run --no-cache` | see "Whole web suite" | |
| 9 | lane stack, `tests/integration/executors/test_pull_run_path.py` | 0 | 5 passed, 52 s |
| 10 | `tests/integration/executors/test_agent_e2e.py` | 0 | 3 passed, 55 s |
| 11 | `test_http_run_path.py`, `test_http_operations.py`, `test_http_probe_worker.py` | 0 | 27 passed |
| 12 | `test_runner_channel.py`, `test_runner_seam.py`, `test_runner_client_wire.py`, `test_runner_bridge_e2e.py` | 0 | 56 passed |
| 13 | `test_executor_commands.py`, `test_executor_surface.py`, `test_secret_never_leaves.py`, `test_http_sentinel.py` | 0 | 46 passed |
| 14 | `tests/integration/db/test_executor_pull_migration.py`, `test_schema_invariant_inventory.py` (lane env exported) | 0 | 20 passed |
| 15 | `tests/integration/composition/test_every_port_implementation_is_whole.py` (whole file) | 0 | 31 passed, 577 s |
| 16 | `tests/integration/api/test_role_register.py`, `test_authorization.py`, `test_served_document_and_health_plane.py` | 1, then 0 | 69 passed and 1 red (`runner.py` is a router that reads the subject: the expected list now names it); `test_authorization.py` alone 36 passed |

## Decisions the integrator should know

1. **No polling of its own.** The card refreshes on open, on tab return, after a command and by
   «Обновить». The `no-second-polling-loop` guard (candidate 1's `604c6718`) allows exactly one
   `refetchInterval` (the 3 s probe poll); «на связи» can therefore be up to the last read old.
   The judgement is made against the page's clock and the server's `last_seen_at`.
2. **«На связи» is any authenticated call of a runner of the connection**, not strictly a claim:
   the server stamps `last_seen_at` at authentication. An idle runner claims every 25 s, so the two
   readings agree to within a poll.
3. **`R-133` at stage level is still pending** (`a4a11938` + `agent/exec-http-01-r133`): the pull
   adapter attaches the declared model to `ModelResponse` as soon as the field exists
   (`_with_reported_model`), and until then the server holds the declared model equal to the
   revision's pin when it accepts an answer (`422 model_identity_mismatch`).
4. **The worker must be up** for «Проверить» (it takes the probe), and the single slot is held
   while a runner thinks: the card says so.
5. **Stand steps** (runbook section 15): reload the proxy (`deploy.sh` does) for the two runner
   throttle zones, issue the token in the UI, give it to the client in an environment variable.

## Not run, or not proven

- **The manual check with a real Claude Code session** (README section A.6: Bash and Read denied,
  `/pdf-analysis-runner`, a probe and a run answered by `claude-opus-5` / `claude-sonnet-5`): needs
  the owner's login and a stand with `api`, `worker` and `web`; none was built here. Pending.
- The agent killed mid-task (claim back to `open`): the server half is
  `test_a_lapsed_claim_returns_the_task_to_open...` in `test_runner_channel.py` (passes); the
  subprocess version was not written.
- `tests/integration/executors/test_ssh_sshd.py` (needs the sshd container of `EXEC-SSH-01`);
  `tests/integration/db` beyond the two migration files; `tests/integration/recovery`; the live
  journey (`e2e:pc01`); `make gate`; any paid call.
- The Python changes are covered by the lane stack runs above; the `web/` changes were typechecked,
  linted and run in vitest; no browser saw the card.
