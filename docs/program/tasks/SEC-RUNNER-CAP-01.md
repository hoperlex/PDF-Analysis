# Task SEC-RUNNER-CAP-01 — bound the runner long poll and refuse plain-http model destinations

task_id: SEC-RUNNER-CAP-01
status: completed in development candidate (two findings of `EXPOSURE-REVIEW-02.md`, `F-06` and `F-15`; report `docs/program/SEC-RUNNER-CAP-01.md`)

## Outcome

`F-06` (MED): one runner token can no longer hold the API's synchronous thread pool. `claim_task` sleeps in a pool thread, so a sleeping claim now needs a slot of `LongPollSlots`: one waiting claim per token and 16 in all, which leaves 24 of the pool's 40 threads to every other request. A claim over either bound looks once at the rows (what `wait_seconds: 0` does) and answers a task or the contract's existing empty `204`; the runner protocol is unchanged. `F-15` (LOW): `refuse_plain_http` refuses a plain `http://` model destination unless the host is a loopback name or address, or a private literal on `transport: vpn`, with the existing `validation_failed` / `base_url` / `base_url_invalid`; it runs when a revision is written and again where a key is bound for a call, so a connection stored with an `http://` public destination is still read but is not used.

## Depends on

- `EXEC-PULL-01` (the pull channel and `claimExecutorTask`), `EXEC-HTTP-01` (`destinations.py`, the probe and the call path), `EXEC-SEAL-01` (`model.py`) — completed, in the tree at the base commit.
- `PROD-15-EXPOSURE-REVIEW-02` — completed; its findings `F-06` and `F-15` are this task's input.

## Frozen inputs

- domain contract: `contracts/domain/v1/error-codes.json` (read only; no new code, no new constraint value)
- API contract: `contracts/api/v1/openapi.json` (read only; `claimExecutorTask` keeps its `200`, `204`, `401`, `422`, `500`, `503`)
- analysis/comparison/event contract: not_applicable
- migration head: `0033_ar_v3_cite_stage_id` (unchanged)
- base commit: `16a6596fd80db5f607b44b151c43207775f22cfc` (`integration/ar-close-1026`)

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

No route, screen, error code, migration or constraint value is added. The refusal reuses the constraint `base_url_invalid`, which `contracts/domain/v1/error-codes.json` already lists for `base_url`.

## Captured premise evidence

- premise: the base commit, the sleeping line and the unbounded loop in `executors/runner.py`, the scheme test in `executors/model.py`, the nginx zones (and the absence of `limit_conn`), the size of the synchronous pool and that nothing resizes it, that the API serves from one process, the runner contract's wording of `204`, and who calls `destination_for` and `validate_settings`; all re-read at the base commit on 2026-10-26

### P-01 — the base commit is the tip of `integration/ar-close-1026`

- captured_at: 2026-10-26
- command: `git rev-parse integration/ar-close-1026 && git merge-base HEAD 16a6596fd80db5f607b44b151c43207775f22cfc`
- captured_output:
  ```text
  16a6596fd80db5f607b44b151c43207775f22cfc
  16a6596fd80db5f607b44b151c43207775f22cfc
  ```
- interpretation: the lane branch `agent/sec-runner-cap-01` started at the tip of the integration branch. Nothing newer existed in this repository when the lane ran.

### P-02 — `F-06`: the claim sleeps in its thread and nothing bounds the number of sleepers

- captured_at: 2026-10-26
- command: `git show 16a6596fd80db5f607b44b151c43207775f22cfc:src/auditmanager/executors/runner.py | grep -n "_POLL_SECONDS\|sleep(\|def claim_task\|MAX_WAIT_SECONDS: Final"`
- captured_output:
  ```text
  95:MAX_WAIT_SECONDS: Final[int] = 25
  104:_POLL_SECONDS: Final[float] = 1.0
  351:def claim_task(
  393:        sleep(min(_POLL_SECONDS, remaining))
  ```
- interpretation: the review's `runner.py:351-393` and `time.sleep` are as stated (`_POLL_SECONDS` is on line 104, the review says 105: a one-line drift, cosmetic). The loop between 369 and 393 has no counter, so every concurrent claim sleeps. The handler is synchronous (`api/routers/runner.py`, `def claim_executor_task`), so it runs in the pool.

### P-03 — `F-06`: the proxy limits requests per second, not concurrent claims

- captured_at: 2026-10-26
- command: `grep -n "limit_req zone=runner\|limit_conn" infra/deploy/proxy/nginx.conf`
- captured_output:
  ```text
  344:        limit_req zone=runner_channel burst=30 nodelay;
  345:        limit_req zone=runner_address burst=120 nodelay;
  393:        limit_req zone=runner_channel burst=30 nodelay;
  394:        limit_req zone=runner_address burst=120 nodelay;
  ```
- interpretation: one token may burst 30 requests and each may sleep 25 s; there is no `limit_conn`. A `limit_conn` on `/api/v1/runner/` is the `PROD-05` lane's (`infra/**` is forbidden here), so the bound must be in the application.

### P-04 — `F-06`: the pool is 40 threads and nothing in the application resizes it

- captured_at: 2026-10-26
- command: `/root/projects/PDF-Analysis/.venv/bin/python -I -c "import anyio,anyio.to_thread;exec('async def m(): print(anyio.to_thread.current_default_thread_limiter().total_tokens)');anyio.run(m)"; grep -rn "total_tokens\|CapacityLimiter" src infra/deploy --include=*.py`
- captured_output:
  ```text
  40
  ```
- interpretation: 40 is anyio's default for a synchronous handler as installed, and `grep` found no line that sets another figure (empty output after the 40). Two tests of this slice keep both facts true (`test_the_pool_figure_is_the_one_anyio_really_has`, `test_nothing_in_the_application_resizes_the_pool`).

### P-05 — `F-06`: the API is one process, so the state held by a process is the state of the pool

- captured_at: 2026-10-26
- command: `grep -c "workers" infra/deploy/serve.py; grep -n "uvicorn.Config(api_app" infra/deploy/serve.py`
- captured_output:
  ```text
  0
  133:        uvicorn.Config(api_app, host=bind_host, port=api_port, access_log=True)
  ```
- interpretation: `serve.py` builds the API once and passes no `workers`, so there is one process and one pool. The bound is written so that it also holds if that changes: each process counts its own sleepers against its own pool (see the report, section "Several processes").

### P-06 — the runner contract: `204` is the answer past a limit, and a runner claims again at once

- captured_at: 2026-10-26
- command: `sed -n 103,111p tools/executor-runner/RUNNER_API.md`
- captured_output:
  ```text
  - **204** - nothing arrived within `wait_seconds`; empty body. The runner claims again at
    once (the 25 s wait is the pacing) unless it asked for `wait_seconds` 0, in which case it
    sleeps at least 5 s between claims.
  - 401, 422 (`wait_seconds`), 429, 5xx as in section 1.

  Server notes (not required of runners): a claim by a token that already holds an unexpired
  claim SHOULD return that same task again (same payload, lease refreshed), so that a lost
  response or a restarted runner does not strand a task until the lease lapses. A token may
  hold at most the connection's `max claimed tasks`; beyond that the server answers `204`.
  ```
- interpretation: the contract already answers `204` for a claim past a limit, so the typed answer needs no new shape. It also says the runner re-claims at once after a `204`: a runner kept at the bound polls at the proxy's rate until nginx answers `429` and it waits `Retry-After`. That cost is a limit in the report, not a contract change.

### P-07 — `F-15`: the scheme test accepts `http://` for any host

- captured_at: 2026-10-26
- command: `git show 16a6596fd80db5f607b44b151c43207775f22cfc:src/auditmanager/executors/model.py | sed -n 161,172p`
- captured_output:
  ```text
      if "?" in base_url or "#" in base_url or any(ch.isspace() for ch in base_url):
          raise _refuse("base_url", "base_url_invalid")
      if not base_url.startswith(("http://", "https://")):
          raise _refuse("base_url", "base_url_invalid")
      try:
          parts = urllib.parse.urlsplit(base_url)
          port = parts.port
      except ValueError:
          raise _refuse("base_url", "base_url_invalid") from None
      host = parts.hostname
      if not host or parts.username is not None or parts.password is not None:
          raise _refuse("base_url", "base_url_invalid")
  ```
- interpretation: `http://` and `https://` are treated alike; the module already refuses credentials in the URL (kept). `destinations.py` classifies addresses by transport and has no notion of a scheme: its `check` is called with `(host, port, transport=...)` only. Before the change `http://openrouter.ai/api/v1`, `http://93.184.216.34/v1` and `http://169.254.169.254/x` were all accepted by `validate_settings` and bound by `destination_for` (probe in the report).

### P-08 — `F-15`: the module that classifies addresses, and where a stored revision is written and used

- captured_at: 2026-10-26
- command: `grep -rn "validate_settings(" src --include=*.py | grep -v "def validate_settings"; grep -rn "destination_for(" src --include=*.py | grep -v "^src/auditmanager/executors/model.py\|def destination_for\|import"`
- captured_output:
  ```text
  src/auditmanager/executors/commands.py:190:    checked = validate_settings(connection.kind, settings, pinned_model_ids=pinned_model_ids)
  src/auditmanager/executors/probe_runner.py:159:                        destination=destination_for(
  src/auditmanager/executors/probe_runner.py:181:                            destination=destination_for(connection.kind, revision.settings,
  src/auditmanager/executors/resolver.py:223:        destination=destination_for(connection.kind, revision.settings, entry.purpose),
  src/auditmanager/executors/resolver.py:238:                destination=destination_for(connection.kind, revision.settings, purpose),
  src/auditmanager/executors/commands.py:251:    destination = destination_for(connection.kind, revision.settings, purpose)
  src/auditmanager/executors/commands.py:293:    destination = destination_for(connection.kind, revision.settings, "ssh_private_key")
  src/auditmanager/bootstrap/adapters.py:4672:            bound = destination_for(kind, revision.settings, secret.purpose) == secret.destination
  ```
- interpretation: `validate_settings` runs only when a revision is written (`reviseExecutorConnection`, `import_env`), so a stored revision is never re-validated by a read. `destination_for` runs where a key is bound for a call (`resolver.py`, evaluated as an argument of `open_secret`, i.e. before the key is opened), for a probe, when a secret is set, and in the secret view (which catches `DomainError`). `destination_for` is therefore the one seam on the call path that lies inside the allowed paths; `http_adapter.py`, `resolver.py` and `probe_runner.py` are not.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

`EXPOSURE-REVIEW-02.md` is not edited; its rows `F-06` and `F-15` stay as written. The integrator updates the debt rows (`D-236`, `D-242`).

## Publication authority
- development_target: none
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/executors/runner.py`
- `src/auditmanager/executors/model.py`
- `src/auditmanager/executors/destinations.py`
- `tests/unit/executors/**`
- `tests/unit/executor_runner/**`
- `tests/integration/executors/**`
- `docs/program/tasks/SEC-RUNNER-CAP-01.md`
- `docs/program/SEC-RUNNER-CAP-01.md`

`destinations.py` was permitted "only if the premise shows the smallest change needs it". It was not needed and is not changed: `refuse_plain_http` asks `DestinationPolicy.check` and `classify` as they are.

## Lane resources

The tests of this task that need PostgreSQL ran on a private database created and dropped by the lane (`sec_runner_cap_01_*`, migrated to head with the literal `alembic upgrade head`); the integrator's lane database was not written to, reset or dropped. No S3, no container, no network.

## Forbidden hotspots
- `contracts/**`, `db/migrations/**`, `infra/**`, `web/**`, every other `src/**` file (in particular `api/routers/runner.py`, `executors/http_adapter.py`, `executors/probe_runner.py`, `executors/resolver.py`, `bootstrap/**`), every other `tests/**` directory
- root dependency/lock files, migration head, composition root, global styles
- `docs/program/DEBT_REGISTER.md`, `docs/program/CURRENT_STATE.md`, the plan, the rulings, the ADRs, `EXPOSURE-REVIEW-02.md`

## Non-goals
- No `limit_conn`, no change to `nginx.conf`, no shorter poll or asynchronous handler (`PROD-05`, and the review's own "shorten the poll or make it asynchronous" alternative).
- No new error code or constraint value (the contract is not this lane's); no `Retry-After` on the `204` (the router is outside the allowed paths and the contract's `204` has no body or header).
- No change to the probe worker, the adapters, the resolver or the web form; no migration of stored revisions.
- No second classification of addresses: the rule asks `destinations.py`.

## Deliverables
- `src/auditmanager/executors/runner.py`: `LongPollSlots`, the process's instance, the constants, `claim_task(..., slots=)`.
- `src/auditmanager/executors/model.py`: `refuse_plain_http`, called from `validate_settings` and `destination_for`.
- `tests/unit/executors/test_runner_long_poll_cap.py`, `tests/unit/executors/test_model_plain_http.py`, `tests/integration/executors/test_plain_http_destination.py`; the modified tests listed in the report.
- This task file and `docs/program/SEC-RUNNER-CAP-01.md`.

## Required tests
- command: `BS=$(ls -d /root/projects/PDF-Analysis/.venv/bootstrap/lib/python3*/site-packages); PYTHONPATH=src:$BS /root/projects/PDF-Analysis/.venv/bin/python -m pytest -c pyproject.toml --rootdir=. -q -p no:cacheprovider tests/unit/executors tests/unit/executor_runner`
- expected: all pass except the five cases of `tests/unit/executor_runner/test_ssh_forced_command.py`, which fail for a reason outside this diff (the shell script answers exit 65 "claude returned an incomplete answer" in this environment; the file imports nothing of `auditmanager` and `tools/` is unchanged)
- command: the same with `tests/integration/executors/` (all files except the two SSH ones) on a private migrated database: `DATABASE_URL=<private> ... -m pytest ... tests/integration/executors/<the files in the report>`
- expected: all pass
- command: `... -m pytest ... tests/contract/architecture tests/contract/program tests/contract/api_v1/test_doc_prose_facts.py tests/contract/api_v1/test_surface_counts_in_prose.py` on a committed tree, then `git diff --check 16a6596f..HEAD`
- expected: all pass; no output
- command: the governance one-liner of the wave file: `PYTHONPATH=src:$BS python -c "import sys;sys.path.insert(0,'tests/contract/program');import test_wave_governance as t;print(sorted(t.governance_findings(open('docs/program/tasks/SEC-RUNNER-CAP-01.md',encoding='utf-8').read())))"`
- expected: `[]`

## Integration contract

- `claimExecutorTask` keeps its wire: `200` with a task, `204` with an empty body, `401`, `422` for `wait_seconds` outside 0..25. What changes is when the `204` comes: at once for a claim that cannot have a slot. A runner that polls again gets the semantics it had; a runner kept at the bound re-claims at once and meets nginx's `429` (P-06).
- `reviseExecutorConnection` and `import_env` refuse a plain `http://` destination with `422 validation_failed`, `details.field = base_url`, `details.constraint = base_url_invalid`; the web sentence for that constraint already asks for `https://`.
- A key is not opened for a stored `http://` public revision (`destination_for` refuses before `open_secret`): a Run's stage fails with that same `validation_failed`; `setExecutorSecret` on it is refused the same way; the secret view shows `bound_to_current_revision: false`; the probe ends `protocol_error` (limit in the report).
- Shared test helpers changed: `FakeGateway.vpn_url()` (new), `http_support.settings()` defaults `transport` to `vpn` for an `http://` URL. Other lanes that seed an `http_api` connection with `http://` and `transport: direct` through the commands will be refused and should use `vpn_url()`.

## Failure/idempotency/security cases

- A claim whose body raises (database down) gives its slot back (`test_a_slot_is_given_back_when_the_claim_raises`).
- A refusal carries `field` and `constraint` only, never a part of the address (`test_the_refusal_carries_no_part_of_the_address`, and the wire test).
- A name is never resolved by the rule (`test_the_module_does_not_resolve_a_name`).
- A replayed `reviseExecutorConnection` answers the stored outcome without re-validating (unchanged).

## Rollback / feature flag

Not applicable as a flag: the change is two refusals. Rollback is `git revert` of the two code commits; no data was written or migrated. The numbers `MAX_WAITING_CLAIMS_PER_TOKEN` and `MAX_WAITING_CLAIMS_TOTAL` are constants of `runner.py`.

## Handoff

- changed files: see `docs/program/SEC-RUNNER-CAP-01.md`, section 1
- commands/results: the report, section 5
- known limits: the report, section 7
- integration notes: the report, section 8
