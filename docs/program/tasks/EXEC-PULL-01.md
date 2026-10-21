# Task EXEC-PULL-01 — the pull channel: a Claude Code session in VSCode takes run tasks

task_id: EXEC-PULL-01

## Outcome

The flow has five steps.

1. **The administrator prepares a `pull` connection.** They create it with client
   `claude_code_session` and a declared pinned model, issue a runner token (shown once),
   and route «Анализ текста» to the connection.
2. **The owner connects a Claude Code session.** In VSCode they add the stdio MCP bridge
   from `tools/executor-runner/` (`claude mcp add …`, with the token in an environment
   variable) and start the skill.
3. **A run's `text_analysis` call becomes a task.** The worker writes an `executor_task`
   and waits.
4. **The session answers.** It claims the task through the bridge, answers it and submits
   the answer.
5. **The worker completes the call.** The run finishes with the session-declared model;
   the cost is recorded as unmetered and shown as «не тарифицируется».

If no session claims the task before the revision's answer deadline (capped below the
900 s Attempt watchdog), the call fails as `dependency_unavailable` with
`dependency: no_executor_online`. It never moves to another connection unless an administrator
configured a standby.

## Depends on

- `EXEC-HTTP-01` — merged (the resolver seam, `R-133` on the run path, probes on the
  worker).
- `EXEC-ADR-01` — merged (the addendum admitting the inbound runner surface).

## Frozen inputs

- base commit: `origin/dev` at the integrator's freeze, after `EXEC-HTTP-01`;
- this task takes migration `0031` and the contract slot;
- plan §2 (the `pull` kind), §3 (long waits: one Job per run, lease 60 s, watchdog 900 s,
  `slots=1`, drain 270 s), §4.3 T-2 and T-7, §5 (`R-133` with the declared model), §8 (pins
  for session models);
- `R-143a`, `R-143c`, `R-133`, `R-135`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: tests/support/expected_facts.json
- enumerator_owner: EXEC-PULL-01 (migration head and API surface, after the integrator hands over both slots)
- totality_query: `python3 -c "import json;d=json.load(open('tests/support/expected_facts.json'));s=d['surface'];print(s['path_count'],len(s['operations']),len(s['schema_names']),d['migration_head'])"`

## Captured premise evidence

- premise: none

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `db/migrations/versions/**`
- `contracts/api/v1/**`
- `contracts/domain/v1/**`
- `src/auditmanager/executors/**`
- `src/auditmanager/api/**`
- `src/auditmanager/bootstrap/**`
- `src/auditmanager/jobs/events.py`
- `src/auditmanager/runs/scope.py`
- `tests/integration/runs/test_w53c_exec_closure.py`
- `scripts/recovery/product_purge.py`
- `tests/integration/recovery/**`
- `src/auditmanager/shared/identity/**`
- `scripts/recovery/schema_coverage.py`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `infra/deploy/README.md`
- `infra/deploy/serve.py`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/docs/PC01_UI_SEAM.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/P02_SEAMS.md`
- `tools/executor-runner/**`
- `tests/support/**`
- `tests/contract/**`
- `tests/integration/db/**`
- `tests/integration/api/**`
- `tests/integration/composition/**`
- `tests/integration/executors/**`
- `tests/unit/executors/**`
- `web/openapi/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/**`
- `web/src/_pages/workers/**`
- `web/src/widgets/executor-connections/**`
- `web/src/features/issue-runner-token/**`
- `web/src/entities/executor-connection/**`
- `web/tests/**`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/EXEC-PULL-01.md`

## Forbidden hotspots

The following stay closed:

- dependency and lock files: the bridge and the skill use the Python standard library only;
- global styles;
- the screen registry;
- `src/auditmanager/analysis/**`: the pull adapter implements the existing
  `ModelAdapter` protocol inside `executors`;
- the reclaim rule in `src/auditmanager/jobs/repository.py` (`:486-608`): there is no
  parking, so it does not change;
- `CURRENT_STATE.md`, `DEBT_REGISTER.md`, refs, tags and the stand.

## Non-goals

- No parking of an Attempt while a session thinks; a debt row is recorded instead.
- No image payloads, because no run stage sends one today.
- No change to the P02 lock. If the owner's session model is not pinned, the manual check
  uses a pinned model, or stops and reports (plan §8).
- No paid call.

## Work

1. **Migration `0031`:**
   - `executor_runner_token`: hash only, a shown prefix, expiry (default 30 days),
     `revoked_at`, `last_seen_at`, `last_seen_address`;
   - `executor_task`: `ext_<ULID>`, connection, revision, run, Attempt and effect
     references, the request payload, state `open → claimed → answered | expired |
     cancelled`, claim lease, `deadline_at`, answer, declared model, and declared tokens
     if any.
     - It is PRODUCT in `product_purge.py`.
     - The payload and the answer are cleared 7 days after the task becomes terminal.
     - A claim joins the current Attempt and `deadline_at`, so a dead Attempt's task is
       never served.
2. **The runner API on the `api` process**, authenticated by a runner token as its own
   principal type in `api/security.py` (never a user session):
   - `claimExecutorTask`: a long poll of 25 s or less, returning the system prompt, the
     user text and the output JSON schema;
   - `extendExecutorTaskClaim`;
   - `submitExecutorTaskAnswer`;
   - `failExecutorTask`.

   Admin operations: `issueRunnerToken` (the body is returned once), `revokeRunnerToken`.
   Token metadata is readable through `getExecutorConnection`. The `api` writes the rows;
   the remote party only calls HTTP (`R-143c`).
3. **The pull adapter (worker).**
   - `complete()` inserts the task, NOTIFYs, and waits with LISTEN plus a poll, until
     answered or the deadline.
   - The deadline is `min(revision deadline, watchdog remaining − 60 s)`, computed from
     `EXEC-HTTP-01`'s `AttemptContext`; this slice edits no `runs/**`.
   - On expiry it raises `ProxyDispatchError` (from `analysis/public.py`) with
     `dependency_unavailable` and `retry_safe=False` (plan §3). The dispatch class
     depends on the task:
     - a task **never claimed** is not-sent, `dependency: no_executor_online`;
     - a task claimed but not answered is outcome-unknown: the model may have run.
   - Call rows get `identity_basis: declared`.
   - **«Проверить»** for a `pull` revision posts a synthetic task. A runner must claim it
     within 120 s and answer a fixed echo while declaring the revision's model.
     Otherwise the outcome is `no_runner_online`. Only an `ok` probe lets the
     connection be routed (`EXEC-HTTP-01`'s rule).
   - Its `ModelResponse` carries the declared model, so `R-133` applies unchanged.
   - The answer is validated against the same output schema as `http_api`.
   - Cost is `None`, with `cost_basis` unmetered as the run shows it.
4. **nginx** (`nginx.conf:284-293`, `tls-server.conf:117-131`; guarded by
   `tests/contract/test_proxy_rate_limits.py:559`).
   - **No new `location`.** Add a `map` key and a dedicated zone, then a `limit_req`
     line inside the existing `location /api/v1/` in **both** files, as the
     `token_exchange` zone is done.
   - Size the rate for the long-poll cadence: one 25 s claim, plus extend and submit
     calls, per runner. The existing 6 r/m zones are far too tight. Show the chosen rate
     against a scripted runner.
   - No `auth_request` user-session gate, because the token is the credential.
5. **`tools/executor-runner/`.**
   - `mcp_bridge.py`: a stdio MCP server using the standard library only, with tools
     `claim_task`, `submit_answer` and `report_failure`. The token comes from
     `PDF_ANALYSIS_RUNNER_TOKEN` and is never written into a file by the bridge.
   - `workspace/`: the dedicated, empty workspace the session runs in.
     - Its `.claude/settings.json` denies every built-in tool through permission rules,
       so only the bridge's MCP tools remain (plan T-7).
     - Its `.claude/skills/pdf-analysis-runner/SKILL.md` is the session loop. It states
       the exact model id on submit.
   - `README.md`: the setup and revocation steps.
     - The documented command is `claude mcp add --env PDF_ANALYSIS_RUNNER_TOKEN=… --transport stdio pdf-analysis-runner -- python3 <path>/mcp_bridge.py --origin <stand>`.
       Another option must sit between `--env` and the name, per the Claude Code MCP
       docs.
     - The scope is `local`.
     - The README says the token lands in `~/.claude.json` in clear.
6. **`runs/scope.py:63`.** The entry stays: the worker is still local, and there is no
   JobPackage or ResultPackage transport. Amend its wording to name the runner channel,
   which carries model calls only (`R-143c`), and keep
   `tests/integration/runs/test_w53c_exec_closure.py:279` green.
7. **UI.**
   - Issue a token: the token is shown once with a copy button, and the screen warns that
     it will not be shown again.
   - Revoke a token.
   - «на связи» when a claim was made in the last 60 s.
   - The number of open tasks.

## Deliverables

The code, the bridge, the skill, the runbook section, and the report
`docs/program/EXEC-PULL-01.md`. The report includes a scripted end-to-end run in which a
test client speaks MCP JSON-RPC to the bridge, which talks to the lane API. It also records
the manual check: a real Claude Code session against the lane stand, run by the planning
session or the owner, with its transcript excerpt. If the manual check was not run, the
report says so explicitly.

## Required tests

- command: `python3 -m pytest -q tests/contract/api_v1 tests/contract/program tests/contract/test_proxy_rate_limits.py` plus the contract files the reseal moves (container-free; `R-135`)
- expected: all passed.
- command: `python3 -m pytest -q tests/unit/executors tests/integration/executors tests/integration/composition` on the lane's own containers
- expected: all passed. The tests must include:
  - an answered task completes a run;
  - a wrong declared model is `model_identity_mismatch`;
  - an expired deadline is `no_executor_online`;
  - a revoked token gets 401;
  - a token of another connection cannot claim;
  - a forged answer that violates the schema is refused;
  - the sentinel token never appears in responses, events or logs.
- command: `python3 -m pytest -q tests/integration/runs/test_w53c_exec_closure.py tests/integration/recovery -k "purge or exec_closure"`
- expected: green. `infra/**`, contract and migration are `AGENTS.md` §8 case 3; the
  integrator records the gate decision under `R-135`.

## Integration contract

`EXEC-AGENT-01` reuses the runner API and the task table unchanged. Client `agent` is a
second value of the same `pull` kind. `EXEC-SSH-01` needs nothing from this slice.

## Failure/idempotency/security cases

- **Submission and claims.**
  - A double submit is idempotent on the task id: the same answer is accepted, a
    different answer gets a `conflict`.
  - A claim lease lost before the submit returns the task to `open`.
  - A worker that dies while waiting leaves the effect ambiguous, exactly as a proxy call
    does today (`provider_outcome_unknown`). A late answer to an `expired` task is refused.
- **Tokens.** They are compared in constant time, stored as hashes only, and never logged.
- **Payloads.** The payload is visible only to a token of the routed connection. A
  connection without `allow_client_documents` still receives only test data on a
  closed-beta stand (`R-141c`). The flag is enforced at task creation for any project
  marked as real client data, once such a marker exists; until then it is shown and
  recorded.

## Rollback / feature flag

Remove the route to the `pull` connection, and the runner surface serves nothing. Revoke
every token. To take the surface away, revert the merge; the migration downgrade refuses
once data exists.

## Handoff

- changed files: tabulated with the reason for each;
- commands/results: each with its exit status;
- known limits: no parking; `slots=1` blocks the queue during a wait;
- integration notes: the nginx reload and token issuance steps for the stand.
