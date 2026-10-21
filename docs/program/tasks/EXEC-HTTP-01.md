# Task EXEC-HTTP-01 — HTTP API connections end to end: UI, probe on the worker, run path, R-133

task_id: EXEC-HTTP-01

## Outcome

An administrator opens «Исполнители», where the tabs are «Подключения», «Процессы» and
«Назначения». In «Подключения» the administrator:

1. creates an `http_api` connection: the address, the flavour, a model from the pinned set,
   and the transport (`direct` or `vpn`);
2. pastes the key into a field whose value never becomes a JavaScript value;
3. presses «Проверить». The worker runs the probe and the screen names the outcome in
   Russian: «IP стенда не допущен» (HTML 403), «ключ отклонён» (JSON 401/403), «отвечает
   другая модель», «нет ответа», «адрес недоступен», or «готово» with the reported model
   and latency;
4. assigns the connection to «Анализ текста».

Then, with `AUDITMANAGER_PROVIDER_SOURCE=database`:

- a run freezes that revision at start, and its calls go through it;
- every `model_call` and `provider_call_effect` row records `connection_revision_id`;
- a response whose reported model differs from the pinned one fails as
  `model_identity_mismatch` and publishes nothing (`R-133`, now enforced on the run path).

`python -m auditmanager.executors import-env` turns today's `PROXY_LLM_*` into the first
connection. The `api` container no longer receives the private material. The word
«исполнитель» on «Диспетчер» becomes «ответственный» (plan §8).

## Depends on

- `EXEC-SEAL-01` — merged; the composition-root slot handed over.

## Frozen inputs

- base commit: `origin/dev` at the integrator's freeze, after `EXEC-SEAL-01`;
- the operations and tables that `EXEC-SEAL-01` reports;
- plan §3 (the resolver seam, run-start freeze, two defects, long waits), §4.1 (probes on
  the worker; `api` public-only), §5, §6 (the source switch, `import-env`);
- `R-133`, `R-135`, `R-143b`; `W48-PROXY-01` and `R-67` (the base-URL rule); the existing
  secret form pattern (`web/src/features/change-password/ui/change-password-form.tsx`, a
  server component posting natively to the BFF).

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: web/src/app/bff/v1/[...path]/route.ts
- enumerator_owner: EXEC-HTTP-01 (one new reserved BFF door for the secret form)
- totality_query: `grep -n "function .*Door\|_SEGMENT" 'web/src/app/bff/v1/[...path]/route.ts'`

An unconfigured route is refused by `startRun` and `reauditRun` with `dependency_unavailable`
(503, already declared on both) and the safe detail `dependency: executor_route_missing`. No contract change is
needed.

**The secret form needs a new reserved BFF door**, because the generic credentialed
forward sends JSON and does not read a native form post. The precedent is
`changeThePassword` (`route.ts:1172-1188`): the door reads the form, refuses a cross-site
post exactly as the existing doors do, and sends the JSON body to `setExecutorSecret` with
the session's credential. The API enforces the admin role. The door is listed in the
slice report and the runbook. `EXPOSURE-REVIEW-01.md` is a dated review and is not
rewritten.

## Captured premise evidence

- premise: `R-133` is not enforced on the run path, and `ModelResponse` has no reported model

### P-01 — R-133 is declared but never raised on the run path
- captured_at: 2026-10-22
- command: `grep -rn "MODEL_IDENTITY_MISMATCH\|model_identity_mismatch" src/auditmanager --include=*.py`
- captured_output:
  ```text
  src/auditmanager/api/schemas/models.py:450:    added ``model_identity_mismatch``; the
  src/auditmanager/api/schemas/models.py:481:    MODEL_IDENTITY_MISMATCH = "model_identity_mismatch"
  src/auditmanager/shared/errors/codes.py:48:    MODEL_IDENTITY_MISMATCH = "model_identity_mismatch"
  ```
- interpretation: the code exists only as a declaration; no `raise` site in `src/`. The
  identity check of `tools/provider/identity_probe.py` and the norms runner is outside
  the run path.

### P-02 — the model response carries no reported model
- captured_at: 2026-10-22
- command: `grep -n "reported_model\|class ModelResponse" src/auditmanager/analysis/text/adapter.py`
- captured_output:
  ```text
  56:class ModelResponse:
  ```
- interpretation: `reported_model` is absent and must be added to `ModelResponse`, filled
  by `proxy.py` from the response `model` and by `live.py` from the SDK response.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `src/auditmanager/executors/**`
- `src/auditmanager/analysis/text/**`
- `src/auditmanager/runs/**`
- `src/auditmanager/workers/**`
- `src/auditmanager/jobs/repository.py`
- `src/auditmanager/dashboard/repository.py`
- `tests/integration/dashboard/**`
- `src/auditmanager/jobs/lease.py`
- `src/auditmanager/jobs/public.py`
- `src/auditmanager/jobs/events.py`
- `scripts/recovery/product_purge.py`
- `src/auditmanager/bootstrap/**`
- `src/auditmanager/api/**`
- `infra/deploy/compose.server.yml`
- `infra/deploy/env/alpha.env.example`
- `infra/deploy/env/provider.env.example`
- `infra/deploy/readiness.sh`
- `infra/deploy/README.md`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `tests/integration/executors/**`
- `tests/unit/executors/**`
- `tests/integration/analysis_text/**`
- `tests/integration/runs/**`
- `tests/integration/jobs/**`
- `tests/integration/recovery/**`
- `tests/integration/workers/**`
- `tests/integration/composition/**`
- `tests/integration/api/**`
- `tests/contract/**`
- `web/src/_pages/workers/**`
- `web/src/_pages/dispatcher/**`
- `web/src/widgets/worker-list/**`
- `web/src/widgets/executor-connections/**`
- `web/src/widgets/executor-routes/**`
- `web/src/widgets/assignment-board/**`
- `web/src/features/manage-executor-connection/**`
- `web/src/features/set-executor-secret/**`
- `web/src/features/transition-assignment/**`
- `web/src/entities/executor-connection/**`
- `web/src/entities/execution/**`
- `web/src/app/bff/**`
- `web/src/shared/api/catalog-message.ts`
- `web/src/shared/api/query-keys.ts`
- `web/tests/**`
- `docs/program/EXEC-HTTP-01.md`

## Forbidden hotspots

`contracts/**`, `db/migrations/**` and dependency and lock files (`pyproject.toml`,
`uv.lock`, `web/package*.json`, `web/FRONTEND_LOCK.json`). Also forbidden: global styles
(`web/src/app/globals.css`, so use module CSS and `--am-*` tokens), the screen registry
(the tabs live inside `/workers`; there is no new route), `norms/**`, `tools/**`,
`CURRENT_STATE.md`, `DEBT_REGISTER.md`, refs, tags and the stand.

## Non-goals

- No `pull`, `ssh_command` or `ssh_tunnel` behaviour: those kinds can be created but are
  refused at «Проверить» with the probe outcome `kind_not_served`, and at route time with
  `validation_failed`, `constraint: kind_not_served`.
- No parking of Attempts.
- No move of the norms CLI, and no tariff entry.
- No paid call: every test uses a local fake OpenAI-compatible server, and the Anthropic
  flavour uses the SDK against a fake base URL.

## Work

1. **The resolver seam** (plan §3): `_build_provider` returns a resolver.
   - With source `environment` the run path is today's, apart from two deliberate changes
     (plan §6). `R-133` is enforced. Both credential demands in `settings.py:253-278`, the
     proxy branch and the live branch, are skipped for `EXECUTION_ROLE=api` and for
     source `database`. The
     existing composition tests prove the rest unchanged.
   - With source `database`, `AUDITMANAGER_PROVIDER_MODE` must be `live`.
   - With source `database`, `start_run` freezes the route's revision and the input budget
     follows that revision's pinned model.
   - The worker opens the secret per Attempt, with `open_secret(secret_id, destination)`
     recomputing the destination from the frozen revision.
   - **`AttemptContext`** carries `run_id`, `attempt_id`, the effect or call id,
     `started_monotonic` and the watchdog seconds. It is built where the heartbeat starts
     (`executor.py:935`) and passed to the adapter factory. `jobs/public.py` exports
     `ATTEMPT_WATCHDOG_SECONDS` (`lease.py:20`). `EXEC-PULL-01` relies on it for the
     deadline and the task's references, so no later slice edits `runs/**`.
   - `jobs/repository.py` `prepare_provider_call` (`:814`) and the two inserts (`:141`,
     `:218`) take `connection_revision_id` and `identity_basis`.
   - A standby is used only at run start, as plan §2 says, and is journaled.
   - The source switch refuses to start if `PROXY_LLM_*` or `ANTHROPIC_API_KEY` is set
     while the source is `database`.
2. **`R-133`.** Add `ModelResponse.reported_model`, filled by both adapters. A revision
   carries two fields, and neither is derived from the other (plan §3):
   - the pin id, which gives tariffs and the budget;
   - the gateway model name, which is sent and compared.

   `stage.py` compares the reported model with the gateway name. The check applies only
   to provider mode `live`: a `recorded` response is a replayed fixture, and `recorded` is
   the default mode (`alpha.env.example:219`). Under `environment` the
   expected value is `PROXY_LLM_MODEL`; with the stub `proxy` the stage fails closed, and its
   stored error message names `model_not_selected` (the envelope carries only the code's `safe_detail_keys`; such a word goes into the stored stage error message). A mismatch, or no reported model, is
   `model_identity_mismatch`: the stage fails and nothing is published.

   The identity and rate check becomes `executors/identity.py`. It is ported from
   `tools/provider/identity_probe.py:67-112`; `tools/` is not imported, because the image
   does not copy it. The rate check (±20 %) applies only to a `metered` revision whose
   gateway reports a cost. Without a reported cost it is recorded as `not_reported`, not
   failed, so Ollama, vLLM and the Anthropic SDK can pass.

   The meter (`cost.py`) and `stage.py:411` write cost basis `unmetered` for a
   `not_metered` revision. The integration notes must tell the operator to set an
   explicit `PROXY_LLM_MODEL` before this reaches the stand.
3. **Probes on the worker.**
   - The worker service picks up `executor_probe` rows in state `requested`, through
     LISTEN or a poll.
   - It sends the smallest completion and maps the result as plan §4 says: HTML 403 →
     `ip_refused`; JSON 401/403 → `credential_refused`; then model, timeout and DNS or
     connect.
   - It stores a scrubbed, truncated detail.
   - Only a revision with an `ok` probe on its current secret can be routed or used.
   - A probe still `requested` after 120 s gets the outcome `no_worker`.
     A draining worker takes no new probes.
   - Destination rules (plan T-9) are enforced in the probe and in the call:
     - refused by default: compose service names, loopback, link-local and the compose
       network;
     - a private range is accepted only for `transport: vpn`;
     - for `transport: ssh_tunnel` the rule applies to the SSH endpoint. The tunnel
       target is resolved on the remote host, so a remote `localhost` (Ollama) is
       allowed;
     - an optional `AUDITMANAGER_EXECUTOR_ALLOWED_HOSTS` narrows further.
4. **UI.**
   - Tabs in `/workers`.
   - Forms in the house style (no form library).
   - The secret form is a server component posting natively to a BFF route, so the key
     never becomes a JavaScript value; a unit test asserts there is no client directive.
   - The model is chosen from a select of pinned models.
   - The route editor shows a standby only when one is configured.
   - The notice of connection changes in the last 7 days (plan T-1).
   - Russian copy throughout. Latin product names (HTTP API, OpenRouter, VPN) are added
     to the rendered-language guard's justified list with reasons.
5. **`import-env` and infra.**
   - `import-env` is idempotent: a second run is a no-op that names the existing
     connection.
   - `rewrap` re-seals every current secret to the active kid by inserting new rows
     (`executor_secret` is immutable). Each new row keeps its destination, and a test
     shows the call still opens after a rewrap.
   - **The run-level cost rule.** It keeps the frozen "three fields move together"
     invariant (`runs.py:150-157`), because the run did call a provider:
     - when every call is unmetered: `cost_micros` 0, basis `unmetered`, call count n;
     - when unmetered and metered calls mix: the metered sum, basis `estimated`.

     The rule applies at `cost.py:76`, `runs/repository.py:161` and the dashboard
     aggregate (`dashboard/repository.py:103`, `:199`).
   - `compose.server.yml`: the `api` service stops loading `provider.env` and receives
     `AUDITMANAGER_SECRETS_PUBLIC_KEYS`.
   - `readiness.sh` checks the source, the ring and the public keys.
   - The runbook section «Подключения» covers generating the ring, the import, the
     switch and rotation.
6. **Proofs.** The sentinel test extends to the probe and call path. Every new guard is
   shown failing under a quoted mutation.

## Deliverables

The code, the screen, the infra edits, the runbook section, and the report
`docs/program/EXEC-HTTP-01.md` with screenshots of the three tabs taken through the static
preview (the `cdp.mjs` route).

## Required tests

- command: `python3 -m pytest -q tests/contract/api_v1 tests/contract/program` plus the contract guards the changed files are pinned by (container-free; `R-135`)
- expected: all passed.
- command: `python3 -m pytest -q tests/unit/executors tests/integration/executors tests/integration/analysis_text tests/integration/runs/test_full_chain.py tests/integration/jobs tests/integration/workers tests/integration/composition` on the lane's own containers
- expected: all passed. These include a run through a fake HTTP connection, a mismatch
  run, an `ip_refused`/`credential_refused` probe pair, a source-switch refusal and the
  `environment` regression.
- command: `npm --prefix web run lint -- --quiet && npm --prefix web run typecheck && npm --prefix web test -- --run web/tests/unit/workers web/tests/guards`
- expected: green.
- The full frontend suite, the live journey and a complete gate are deferred under
  `R-135`, and the report says so. `infra/**` is `AGENTS.md` §8 case 3; the integrator
  records the gate decision.

## Integration contract

- `EXEC-PULL-01` and `EXEC-SSH-01` plug a new kind into the resolver by registering an
  adapter factory for the kind in `executors`; nothing else in the run path changes for
  them.
- The default source stays `environment` until the operator imports and switches.
- **Merging still changes stand behaviour in two ways** (plan §6):
  - runs fail closed unless `PROXY_LLM_MODEL` is explicit and matches what the gateway
    reports;
  - the `api` no longer reads `provider.env`.

  The integration notes give the operator's order: set the model, deploy, verify one run.

## Failure/idempotency/security cases

- A rotation mid-run is picked up at the next Attempt.
- A revision archived after a run froze it still serves that run.
- `secret_unreadable` refuses the call as `dependency_credential_refused`; the stored
  stage error message names `secret_unreadable`.
- A probe never logs a header.
- An expert sees connections without secrets and without the controls.
- No silent fallback: a standby is used only if configured, and each use is an event plus
  the call row's revision.

## Rollback / feature flag

`AUDITMANAGER_PROVIDER_SOURCE=environment` restores today's path; the stand keeps
`provider.env` until the operator switches. Revert the merge to remove the code.

## Handoff

- changed files: tabulated with the reason for each;
- commands/results: each with its exit status;
- known limits: the deferred suites;
- integration notes: the operator steps for the stand, which are not run by the lane.
