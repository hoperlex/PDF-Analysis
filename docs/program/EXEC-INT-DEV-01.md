# EXEC-INT-DEV-01 — Claude Code subscription-session channel on dev

**Status:** candidate accepted locally; `origin/dev` publication is the last step.
**Inputs:** `agent/exec-cand2` (`f51aeb62`), `agent/exec-http-01-r133`
(`8801814e`), remote dev base `7a2270fa`. The source implementation and its
DB/S3 evidence are recorded in `EXEC-CANDIDATE-2.md` and `EXEC-PULL-01.md`.

## User-visible path

The administrator creates a `pull` connection with client
`claude_code_session` and a pinned Claude model, issues a runner token in the
connection card, and gives it to the session owner. The owner signs into Claude
Code in VSCode, installs `tools/executor-runner/mcp_bridge.py` as a stdio MCP
server in the isolated workspace, selects the exact model and starts
`/pdf-analysis-runner`. The owner or administrator presses «Проверить»; after
the runner answers its probe, the administrator routes «Анализ текста» to the
connection. The running session claims tasks over HTTPS and submits schema
validated answers. The UI shows token status and the number of open tasks.
The process holds no Claude API key; it uses the owner's interactive session.

This is a model-call channel only. The worker retains the run and its document
custody. An absent runner yields `no_executor_online`; the server does not
silently switch providers. The token can be revoked in the UI. See
`tools/executor-runner/README.md` for exact setup, denial rules and the real
session acceptance checklist.

## Integration and checks

The integration merge brings the completed `EXEC-PULL-01` owned migration
`0031`, API surface (87 paths / 99 operations / 284 schemas), runner principal,
pull adapter, MCP bridge, UI and tests. The `EXEC-HTTP-01` cherry-pick adds the
stage-level `R-133` reported-model check. The only direct code-area edit in this
task corrects the README's setup order: probe before routing.

| Check on the integration tree | Result |
| --- | --- |
| `pytest tests/unit/executors tests/unit/executor_runner` | 498 passed |
| Focused API/program/proxy contract checks | 427 passed |
| `npm --prefix web run typecheck` | passed |
| `npm --prefix web run lint -- --quiet` | passed |
| `npm --prefix web test -- --run tests/unit/workers` | 143 passed |
| Full `npm --prefix web test -- --run --no-cache` | 185 files, 2827 passed |
| `npm --prefix web run build` | passed |
| Full `pytest tests/contract` with the three gate-specific ignores | 993 passed, 19,283 subtests passed |

The prior source candidate's lane-backed tests (PostgreSQL, S3, real API and
worker, simulated runner, bridge and migration) passed as enumerated in
`EXEC-CANDIDATE-2.md`. This integration did not reuse another task's running
lane. A real Claude Code login/session and its tool-denial check remain manual
acceptance before routing customer work. No paid call was made.

The first contract run found the new task's strict metadata fields and the
release guard's clean-tree requirement. After fixing the fields and committing
the tree, the whole contract run passed. `make gate-preflight` refused to start
the complete gate: the host had 3209 MiB free against its 6144 MiB requirement.
`R-135` permits bounded acceptance
for a development candidate. This does not satisfy the `origin/main` policy's
literal `GATE OK` requirement.

## Codex and GPT options

These are follow-up designs; no OpenAI model is pinned in the current
`docs/program/P02_LOCK.json`, and the `pull` client enum currently has only
`claude_code_session` and `agent`. They require a separate contract/model-pin
task before the UI can route a GPT model.

1. **Interactive Codex session, pull/MCP.** Reuse `mcp_bridge.py` and the runner
   API; add a `codex_session` client, an isolated Codex workspace/skill, and
   model pins. Codex CLI and IDE support stdio MCP servers. The owner starts
   the session loop under their own ChatGPT/Codex login. This is closest to
   the Claude subscription-session UX, but the real Codex session and its
   tool policy must be validated. Source:
   <https://developers.openai.com/learn/docs-mcp>.
2. **ChatGPT plan OAuth with Codex app-server or Responses.** For an eligible
   open-source app or approved private client, Sign in with ChatGPT can grant
   plan-backed Responses access after user consent. Codex app-server accepts
   that OAuth access token and exposes a persistent local thread/turn protocol.
   This is the stronger route for unattended GPT tasks using a subscription;
   it needs registration, consent, secure token storage/refresh, model
   eligibility checks and a new adapter. It does not read the user's existing
   ChatGPT conversations. Sources:
   <https://developers.openai.com/siwc/quickstart>,
   <https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server>,
   <https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations>.
3. **OpenAI API key, Responses or Agents API.** Suitable for unattended use
   without a subscription session, billed as API usage. The app has an
   `http_api`/OpenAI-compatible seam already, but a GPT model pin and provider
   adapter/response verification still need explicit work. Source:
   <https://developers.openai.com/api/docs/guides/agents-api/overview>.

The OAuth preview currently requires `store: false` and `stream: true` for
direct Responses requests and restricts several fields and hosted tools. A
design for option 2 must use that request contract; treating a ChatGPT login
as an API key is incorrect.

## Contracts, risks and integrator instructions

- New contracts are the imported `EXEC-PULL-01` additive runner operations and
  token/task schemas; this task directly changes none. Migration head is
  `0031_executor_pull_channel`. No error code was added.
- The model reported by a session is a declaration; `R-133` rejects a value
  different from the pin, but the server cannot cryptographically prove which
  model the person's session used. Manual `/model` and the isolated workspace
  are required.
- A long-running interactive skill consumes subscription usage and must be
  started by the owner. The bridge's token is stored by Claude Code in local
  configuration; the README describes that exposure and revocation.
- Before publication, take `.local/handoff/dev.lock`, fetch the live remote
  `dev`, require it to be an ancestor of the exact clean candidate, then
  fast-forward `origin/dev` and verify the remote SHA. Never publish this task
  to `origin/main`; that requires a separate exact-SHA owner instruction,
  complete `make gate` and deployment verification.
- The integration imports only completed source-task changes in contracts,
  migration and composition. Direct edits for this task are confined to its
  allowed paths. Root dependency/lock files and global styles are untouched.

## Complete changed-file list against the frozen dev base

- `contracts/api/v1/openapi.json`
- `contracts/domain/v1/error-codes.json`
- `contracts/domain/v1/identifiers.json`
- `contracts/domain/v1/identifiers.schema.json`
- `db/migrations/versions/20261022_0031_executor_pull_channel.py`
- `docs/manual-tests/PC-01_prototype.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/DEPLOYMENT_RUNBOOK.md`
- `docs/program/EXEC-CANDIDATE-2.md`
- `docs/program/EXEC-INT-DEV-01.md`
- `docs/program/EXEC-PULL-01.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/tasks/EXEC-INT-DEV-01.md`
- `infra/deploy/README.md`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `infra/deploy/serve.py`
- `scripts/recovery/product_purge.py`
- `scripts/recovery/schema_coverage.py`
- `src/auditmanager/analysis/text/live.py`
- `src/auditmanager/analysis/text/stage.py`
- `src/auditmanager/api/README.md`
- `src/auditmanager/api/app.py`
- `src/auditmanager/api/health.py`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/api/routers/declarations.py`
- `src/auditmanager/api/routers/errors.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/routers/runner.py`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/api/security.py`
- `src/auditmanager/bootstrap/adapters.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/bootstrap/providers.py`
- `src/auditmanager/bootstrap/runner.py`
- `src/auditmanager/executors/README.md`
- `src/auditmanager/executors/answers.py`
- `src/auditmanager/executors/kinds.py`
- `src/auditmanager/executors/model.py`
- `src/auditmanager/executors/probe_runner.py`
- `src/auditmanager/executors/public.py`
- `src/auditmanager/executors/pull.py`
- `src/auditmanager/executors/repository.py`
- `src/auditmanager/executors/resolver.py`
- `src/auditmanager/executors/runner.py`
- `src/auditmanager/executors/runner_repository.py`
- `src/auditmanager/executors/runtime.py`
- `src/auditmanager/executors/usability.py`
- `src/auditmanager/jobs/events.py`
- `src/auditmanager/runs/scope.py`
- `src/auditmanager/shared/identity/__init__.py`
- `src/auditmanager/shared/identity/ids.py`
- `tests/contract/api_v1/test_openapi_conformance.py`
- `tests/contract/api_v1/test_surface_counts_in_prose.py`
- `tests/contract/api_v1/test_w55b_portal_bundle_seal.py`
- `tests/contract/domain_p02/test_openapi_document.py`
- `tests/contract/test_proxy_rate_limits.py`
- `tests/e2e/pc01/journey/manifest.json`
- `tests/integration/api/test_authorization.py`
- `tests/integration/api/test_role_register.py`
- `tests/integration/api/test_served_document_and_health_plane.py`
- `tests/integration/composition/test_every_port_implementation_is_whole.py`
- `tests/integration/db/test_downgrade_chain_round_trip.py`
- `tests/integration/db/test_executor_pull_migration.py`
- `tests/integration/db/test_migration_lifecycle.py`
- `tests/integration/db/test_schema_invariant_inventory.py`
- `tests/integration/db/test_schema_shape.py`
- `tests/integration/executors/test_agent_e2e.py`
- `tests/integration/executors/test_http_operations.py`
- `tests/integration/executors/test_http_probe_worker.py`
- `tests/integration/executors/test_http_run_path.py`
- `tests/integration/executors/test_pull_run_path.py`
- `tests/integration/executors/test_runner_bridge_e2e.py`
- `tests/integration/executors/test_runner_channel.py`
- `tests/integration/executors/test_runner_client_wire.py`
- `tests/integration/executors/test_runner_seam.py`
- `tests/integration/recovery/test_product_purge.py`
- `tests/support/expected_facts.json`
- `tests/unit/executors/test_identity_stage.py`
- `tests/unit/executors/test_pull_adapter.py`
- `tests/unit/executors/test_pull_wiring.py`
- `tests/unit/executors/test_runner_answers.py`
- `tests/unit/executors/test_runner_tokens.py`
- `tools/executor-runner/README.md`
- `tools/executor-runner/RUNNER_API.md`
- `web/FRONTEND_LOCK.json`
- `web/openapi/openapi.json`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/src/entities/executor-connection/index.ts`
- `web/src/entities/executor-connection/model/failure.ts`
- `web/src/entities/executor-connection/model/readiness.ts`
- `web/src/entities/executor-connection/model/runner-tokens.ts`
- `web/src/entities/executor-connection/model/vocabulary.ts`
- `web/src/features/manage-executor-connection/index.ts`
- `web/src/features/manage-executor-connection/model/use-manage-executor-connection.ts`
- `web/src/features/manage-executor-connection/ui/runner-token-panel.tsx`
- `web/src/features/manage-executor-connection/ui/settings-fields.tsx`
- `web/src/shared/api/authorization.ts`
- `web/src/shared/api/generated/client.gen.ts`
- `web/src/shared/api/generated/index.ts`
- `web/src/shared/api/generated/operations.gen.ts`
- `web/src/shared/api/generated/types.gen.ts`
- `web/src/widgets/executor-connections/ui/connection-card.tsx`
- `web/tests/contract/pc01-error-codes.contract.test.ts`
- `web/tests/contract/seam-operations.contract.test.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/unit/api/authorization-state.test.ts`
- `web/tests/unit/workers/executor-commands.test.ts`
- `web/tests/unit/workers/executor-connections.test.ts`
- `web/tests/unit/workers/executor-fixtures.ts`
- `web/tests/unit/workers/executor-runner-tokens.test.ts`
