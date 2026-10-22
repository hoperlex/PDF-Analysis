STATUS: items 1-4 and 6 written and committed; container-free checks green; DB tests wait for the lane stack (13:35 +05)

# EXEC-PULL-01 report, server half (in progress)

Worktree `.local/worktrees/exec-pull`, branch `agent/exec-pull-01`, based on `agent/exec-http-01` at
`8e36b0ef` and merged with `agent/exec-line-01` (EXEC-SEAL-01 final, `a72bf243`) at `66c670d5`.
R-144b minimal checks: no complete gate, no whole directory, no live journey, no paid call. Covers
Work 1, 2, 3, 4 and 6 and the contract for the runner operations. Not here: the web screens (UI
lane) and Work 5 (`agent/exec-tools-01`, the bridge, the skill, the workspace).

## What was built

| Work | Where | Result |
|---|---|---|
| 1 migration `0031_executor_pull_channel` | `db/migrations/versions/20261022_0031_*.py` | `executor_runner_token` (SHA-256 only, `amr_` + 8 character prefix, expiry, write-once revoke, last seen and address) and `executor_task` (state `open -> claimed -> answered / failed`, `expired` and `cancelled` from `open` or `claimed`; lease; `deadline_at`; payload and answer cleared 7 days after the end). Frozen and write-once triggers, shape CHECKs, identity-format CHECK on every id column, the composite FK that keeps a token to its own connection. Downgrade refuses once any row exists. |
| 2 runner API + admin ops | `executors/runner.py`, `runner_repository.py`, `answers.py`, `api/routers/runner.py`, `bootstrap/runner.py`, `api/security.py` | `claimExecutorTask` (long poll <= 25 s), `extendExecutorTaskClaim`, `submitExecutorTaskAnswer`, `failExecutorTask`; admin `issueRunnerToken`, `revokeRunnerToken`. A runner token is its own principal in the seam (`RUNNER_OPERATIONS`, `RunnerIdentity`): it reaches those four operations only and every other operation refuses it as `authentication_required`; a user credential on a runner operation is refused alike. Token metadata and the open task count are on `getExecutorConnection` (pull only). |
| 3 pull adapter + probe | `executors/pull.py` | `PullAdapter.complete` writes a task and waits (LISTEN + poll) until `min(revision deadline, watchdog remaining - 60 s)`. Never claimed: `ProxyDispatchError` `not_sent`, `dependency: no_executor_online`, `retry_safe False`. Claimed and not answered, or failed by the runner: `outcome_unknown`. `identity_basis = declared`; the response carries the declared model (`R-133` unchanged) and no cost. `probe_pull`: a synthetic echo task a runner must claim in 120 s and answer in 120 s; `no_runner_online`, `ok`, `timeout`, `protocol_error`. |
| 4 nginx | `proxy/nginx.conf`, `proxy/tls-server.conf` | Two zones declared once: `runner_channel` per token prefix (60 r/m, burst 30) and `runner_address` per address (300 r/m, burst 120), both empty for every path but `/api/v1/runner/tasks/`; `limit_req` lines inside `location /api/v1/` and the upload location of both files; no `auth_request`. |
| 6 `runs/scope.py` | `src/auditmanager/runs/scope.py` | The entry stays; its wording names the runner channel as carrying model calls only. `test_w53c_exec_closure.py` stays green. |
| contract | `contracts/api/v1/openapi.json`, `contracts/domain/v1/*`, `web/openapi`, generated client, `FRONTEND_LOCK.json` | 87 paths / 99 operations / 284 schemas (+6 / +12); identifiers `ern` and `ext`; notes for the new `conflict_reason`s and the 422 `model_identity_mismatch`; no error code added. |
| pins | `tests/support/expected_facts.json`, prose counts, `product_purge.py`, `schema_coverage.py` | head `0031_executor_pull_channel`; `executor_task` PRODUCT, `executor_runner_token` KEEP, two KEEP command types. |

## Decisions the integrator should know

1. **One `bearerAuth` scheme, a second principal.** The document still declares a single bearer
   scheme (six guards in `tests/contract` and `tests/integration/api` pin that); the runner token
   rides in it and the four operations declare `401` and no `403` (a runner holds no role).
2. **`422` for `model_identity_mismatch` on submit** (the tools branch's accepted deviation). The
   catalog's status for that code is 502; the router answers the one case itself with the
   envelope at 422, because a runner treats 5xx as transient and would retry. The catalog note says so.
3. **`issueRunnerToken` is keyed, and a repeat is `conflict` / `token_shown_once`.** The value is
   not stored, so an identical retry cannot return it; the administrator revokes and re-issues.
4. **A lapsed lease is not a lost claim until someone sweeps.** `claim` returns lapsed claims to
   `open` first; a late submit by the old claimant succeeds if nobody has taken the task and the
   deadline holds, and is `claim_lost` once another claim took it. A token whose connection allows
   one claim at a time is given the same task again (re-delivery); with `max_claimed_tasks > 1` it
   is not (parallel claim loops would otherwise all get the same task).
5. **An answer is checked against the task's schema by a small validator** (`answers.py`): the
   runtime lock carries no JSON Schema library and a root dependency is not this slice's. It
   supports exactly the keywords the three stage schemas use and refuses any other keyword when
   the task is written (`SchemaNotSupported` -> `not_sent`), so an unjudgeable schema is never
   waved through. A violation names a location and a keyword, never the text; a name the answer
   invented is reported at its parent.
6. **The extra address zone.** The brief asked for the throttle keyed on the token. A caller who
   invents a fresh well-formed prefix per request never meets a token bucket and costs one indexed
   lookup each, so a second zone per address bounds that. Drop `runner_address` if unwanted: three
   `limit_req` lines per file and one map/zone pair.
7. **`Date` header:** uvicorn sends it on every response (`test_runner_client_wire.py` proves the
   shipped client derives claim time from it). No `Retry-After` on nginx's 429 (a `location` may
   not add a header); the client's 30 s default applies.

## Integration notes (for the HTTP lane's resolver and the integrator)

* The resolver's `pull` branch calls `executors.public.build_pull_adapter(session_factory=,
  revision=, context=<AttemptContext>, engine=)`; the worker's probe runner calls
  `executors.public.probe_pull(session_factory, revision, probe_id, engine=)` and writes the
  `ProbeResult` with `record_probe_result`. `identity_basis` per kind is already
  `IDENTITY_BASIS_BY_KIND['pull'] = 'declared'`; billing `not_metered` gives the unmetered basis.
* The adapter relies on `AttemptContext.run_id/attempt_id/call_id`; `call_id` may be `None`
  (the column is nullable).
* Files shared with other lanes were edited additively: `executors/public.py` (imports and
  `__all__`), `bootstrap/adapters.py` (one hook in `get_connection` and one helper at the end),
  `bootstrap/composition.py` (one import and one `runner=` argument), `jobs/events.py` (a separate
  `_SAFE_KEYS |= ...` line), `api/routers/__init__.py`, `ports.py`, `security.py`, `app.py`.
* The stand needs the proxy reloaded (`deploy.sh` does it) and tokens issued from the UI;
  `docs/program/DEPLOYMENT_RUNBOOK.md` section 14 has the steps.
* `CURRENT_STATE.md` still states head `0029` and 73/83/242: two guards in
  `tests/contract/api_v1/test_doc_prose_facts.py` stay red until the integrator updates it. They
  were already red on the base (head `0030`, 81/93/272).
