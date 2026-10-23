# Task EXEC-ENV-OPENROUTER-01 — selectable baseline OpenRouter and crop transport

task_id: EXEC-ENV-OPENROUTER-01

## Outcome

When the worker has a complete `PROXY_LLM_*` configuration and the provider source is
`database`, it records one baseline OpenRouter-compatible HTTP connection and requests its
probe. After an `ok` probe, the existing «Исполнители → Назначения» selector offers it.
Registration never changes an existing route, including Codex. Its OpenAI Chat transport
delivers a verified PNG as an image block, as in `EXEC-IMAGE-CHANNELS-01`.

## Depends on

- `EXEC-HTTP-01` — completed HTTP source and import command.
- `EXEC-IMAGE-CHANNELS-01` — completed image transport for OpenAI Chat HTTP.

## Frozen inputs

- base commit: `994404a9131da3c8c6e573f2b158fcff7c3bdd98`;
- API contract `1.1.0`, SHA-256 `889ac164ad356674471da8de734597d118b6799f352808b80da74d2b6f295a87`;
- stage registry SHA-256 `0ca693ff1abde4016af51fac9c0465800cb2659a0047207b84299ed0929d861e`;
- crop manifest SHA-256 `0d66634a6668edf87189720644fc3c651ad09fccb7418d0c1209d2a6a6e3da7e`;
- migration head `0031_executor_pull_channel`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- `bootstrap/settings.py` refuses all `PROXY_LLM_*` under `database`;
- `widgets/executor-routes` only lists persisted executor connections;
- `import-env` creates one but must be invoked manually and routes `text_analysis`.

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `docs/program/tasks/EXEC-ENV-OPENROUTER-01.md`
- `docs/program/EXEC-ENV-OPENROUTER-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md`
- `infra/deploy/env/alpha.env.example`
- `infra/deploy/env/provider.env.example`
- `infra/deploy/readiness.sh`
- `src/auditmanager/bootstrap/settings.py`
- `src/auditmanager/executors/operations.py`
- `src/auditmanager/workers/__main__.py`
- `tests/unit/executors/test_provider_source_settings.py`
- `tests/integration/executors/test_http_operations.py`
- `tests/unit/executors/test_http_adapter.py`
- `tests/unit/executors/test_probe_loop.py`
- `tests/unit/runs/test_serving_start_sweeps_temporaries.py`
- `tests/integration/composition/test_readiness_command.py`

## Forbidden hotspots

`contracts/**`, `db/migrations/**`, composition roots, root dependency and lock files,
global styles, deployed runtime files, tags and `origin/main`.

## Non-goals

No paid OpenRouter call, no route switch without an administrator, no new image stage or
prompt/evidence policy, no SSH implementation and no contract or schema change.

## Deliverables

Automatic one-time env connection registration on the worker, safe startup validation,
queued probe, OpenRouter-labelled option in the existing selector, focused regression tests,
deployment instructions and a handoff report.

## Required tests

Focused settings, import, worker startup and HTTP PNG tests; Python compile and
`git diff --check`. Full `make gate` deferred by `R-135` for this development slice.

## Integration contract

`database` remains the only run source. The env triplet is a worker-only bootstrap input;
its key is sealed into the connection database exactly once. Once created, administrators
manage the connection in UI. An existing text route is not changed. The existing route
command chooses the connection by its normal ID after a successful current-key probe.

## Failure/idempotency/security cases

Incomplete env triplets and misplaced API credentials refuse startup. A repeated worker
start neither duplicates the connection nor resets an edited one. No key, image bytes or
address appears in logs or journals. The queued probe obeys the existing destination policy.

## Rollback / feature flag

Remove the env triplet to disable bootstrapping; the persisted connection remains and can
be archived after any route is moved away. Revert code to restore the prior startup rule.

## Handoff

The paired report lists changed files, checks and host steps.
