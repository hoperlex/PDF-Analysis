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

- premise: under the database source the settings refuse PROXY_LLM_*, the route selector lists only persisted connections, and import-env is a manual command that routes text_analysis

### P-01 — settings refuse PROXY_LLM_* under the database source
- captured_at: 2026-10-26
- command: `git grep -n -A 22 'if source == "database":' 994404a9131da3c8c6e573f2b158fcff7c3bdd98 -- src/auditmanager/bootstrap/settings.py; git grep -n -E '^PROXY_(BASE_URL|TOKEN|MODEL)_ENV' 994404a9131da3c8c6e573f2b158fcff7c3bdd98 -- src/auditmanager/bootstrap/settings.py`
- captured_output:
  ```text
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py:321:    if source == "database":
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-322-        # One source of truth, never two. Every connection is a live transport, so the mode is
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-323-        # `live` without the key that mode demands from the environment, and a variable of the
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-324-        # old path that is still set is refused rather than silently ignored.
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-325-        if mode != "live":
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-326-            raise ConfigurationError(
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-327-                f"{PROVIDER_SOURCE_ENV} is database but {PROVIDER_MODE_ENV} is {mode!r}; "
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-328-                "connections are live transports, so the mode must be live"
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-329-            )
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-330-        leftovers = [name for name, value in (
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-331-            (PROXY_BASE_URL_ENV, proxy_base_url), (PROXY_TOKEN_ENV, proxy_token),
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-332-            (PROXY_MODEL_ENV, env.get(PROXY_MODEL_ENV, "").strip() or None),
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-333-            (API_KEY_ENV, api_key),
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-334-        ) if value is not None]
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-335-        if leftovers:
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-336-            raise ConfigurationError(
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-337-                f"{PROVIDER_SOURCE_ENV} is database but {', '.join(leftovers)} "
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-338-                "is still set; the connections are the one source of truth. Remove the "
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-339-                "variable(s) (import them first with `python -m auditmanager.executors "
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-340-                "import-env`) or switch the source back to environment"
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-341-            )
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-342-        if role in ("worker", "all") and not env.get(SECRETS_KEYS_ENV, "").strip():
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py-343-            raise ConfigurationError(
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py:110:PROXY_BASE_URL_ENV: Final[str] = "PROXY_LLM_BASE_URL"
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py:111:PROXY_TOKEN_ENV: Final[str] = "PROXY_LLM_TOKEN"
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/bootstrap/settings.py:112:PROXY_MODEL_ENV: Final[str] = "PROXY_LLM_MODEL"
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 994404a9131da3c8c6e573f2b158fcff7c3bdd98 with git grep against that tree (not at dispatch time). At the base, bootstrap/settings.py:321 opens the source == "database" branch; it builds leftovers from PROXY_BASE_URL_ENV, PROXY_TOKEN_ENV, PROXY_MODEL_ENV and API_KEY_ENV (330-334) and raises ConfigurationError when any is still set (335-341). The second command shows those constants name PROXY_LLM_BASE_URL, PROXY_LLM_TOKEN and PROXY_LLM_MODEL (110-112). So under database a set PROXY_LLM_* variable refuses startup at the base. Dispatch-time record (quoted from the original section, which carried this bullet without a command or output): `bootstrap/settings.py` refuses all `PROXY_LLM_*` under `database`;

### P-02 — the route selector lists persisted connections only
- captured_at: 2026-10-26
- command: `git grep -n -E 'useExecutorConnections|list\.data\?\.items|PROXY|OpenRouter' 994404a9131da3c8c6e573f2b158fcff7c3bdd98 -- web/src/widgets/executor-routes/ui/executor-routes.tsx`
- captured_output:
  ```text
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:web/src/widgets/executor-routes/ui/executor-routes.tsx:37:  useExecutorConnections,
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:web/src/widgets/executor-routes/ui/executor-routes.tsx:196:  const list = useExecutorConnections();
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:web/src/widgets/executor-routes/ui/executor-routes.tsx:198:  const items = list.data?.items ?? [];
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 994404a9131da3c8c6e573f2b158fcff7c3bdd98 with git grep against that tree (not at dispatch time). At the base, widgets/executor-routes/ui/executor-routes.tsx obtains its rows from useExecutorConnections() (import 37, call 196) and uses list.data?.items (198). There is no hit for PROXY or OpenRouter in the file (absence of hits), so the selector has no environment-derived option; whether the list endpoint returns only persisted rows is not shown here. Dispatch-time record (quoted from the original section, which carried this bullet without a command or output): `widgets/executor-routes` only lists persisted executor connections;

### P-03 — import-env is a manual command that routes text_analysis
- captured_at: 2026-10-26
- command: `git grep -n -E 'import-env|import_env|work_kind="text_analysis"' 994404a9131da3c8c6e573f2b158fcff7c3bdd98 -- src/auditmanager/executors/operations.py src/auditmanager/executors/__main__.py src/auditmanager/workers/__main__.py`
- captured_output:
  ```text
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/__main__.py:1:"""``python -m auditmanager.executors import-env | rewrap | reach`` -- the operator's commands.
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/__main__.py:7:Exit codes: ``0`` done (or nothing to do), ``2`` refused (the message says why), ``3`` import-env
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/__main__.py:22:    import_env,
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/__main__.py:54:        "import-env", help="turn PROXY_LLM_* into the first connection (idempotent)")
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/__main__.py:73:        if arguments.command == "import-env":
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/__main__.py:74:            result = import_env(sessions, environ, ring=ring, policy=policy,
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/__main__.py:77:                print(f"import-env: already imported as {result.connection_id}; nothing changed")
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/__main__.py:79:            print(f"import-env: created {result.connection_id}; probe {result.probe_outcome}; "
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:1:"""The operator's commands: ``import-env``, ``rewrap`` and ``reach`` (plan section 6, `EXEC-HTTP-01`).
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:7:``import_env``
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:62:    "import_env",
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:67:#: The display name that marks the connection ``import-env`` made; its presence is what makes a
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:102:# -- import-env ---------------------------------------------------------------------------------
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:112:def import_env(
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:150:                idempotency_key="import-env:connection", actor_uid=actor_uid,
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:154:                pinned_model_ids=pins, roles=_ADMIN, idempotency_key="import-env:revision",
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:159:                ring=sealing, roles=_ADMIN, idempotency_key="import-env:secret",
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:164:                idempotency_key="import-env:probe", actor_uid=actor_uid,
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:177:                session, work_kind="text_analysis",
  994404a9131da3c8c6e573f2b158fcff7c3bdd98:src/auditmanager/executors/operations.py:179:                roles=_ADMIN, idempotency_key="import-env:route", actor_uid=actor_uid,
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 994404a9131da3c8c6e573f2b158fcff7c3bdd98 with git grep against that tree (not at dispatch time). At the base, executors/__main__.py registers the import-env sub-command (54, help 'turn PROXY_LLM_* into the first connection (idempotent)') and runs import_env on it (73-74); operations.py defines import_env (112) and sets the route for work_kind="text_analysis" (177-179). workers/__main__.py has no hit for import-env or import_env (absence of hits), so at the base nothing in worker startup invokes it and it must be run by an operator. Dispatch-time record (quoted from the original section, which carried this bullet without a command or output): `import-env` creates one but must be invoked manually and routes `text_analysis`.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

This section was added on 2026-10-26 by `DEV-TASK-GOVERNANCE-01` so the programme governance guard can read this task; the original task text did not carry it. It records no correction and rewrites no history.

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
