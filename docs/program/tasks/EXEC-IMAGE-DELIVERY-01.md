# Task EXEC-IMAGE-DELIVERY-01 — deliver one verified PNG to a pull executor

task_id: EXEC-IMAGE-DELIVERY-01

## Outcome

An image-capable pull agent can receive one task-scoped PNG over outbound HTTPS,
verify its digest and size, and pass it to the ChatGPT-authenticated Codex CLI as
an image. A text-only runner refuses an image task explicitly. Existing text
analysis and its route remain unchanged; the W56b image stage will create the
first image task after its prompt, budget and evidence policy is frozen.

## Depends on

- `EXEC-PULL-01` — completed pull tasks, tokens and API.
- `EXEC-AGENT-01` — completed unattended agent.
- `W56B-INT-SELECTIVE-CROP-READ-01` — completed checked one-crop reader.

## Frozen inputs

- base commit: `b5e089b5c6a07a7bb53f6b60007c9f5041ebff8d`
- API contract: `1.0.0`, SHA-256 `53d289eceaa4e1b77b1bf86c4bdca0c0be693f81669ded299a02c5122685b9ee`;
- stage registry SHA-256: `9680a3a1e40c7c24a00b3939071bfa83bb15e5edd6ae5ef0322f1a6e0ab20faa`;
- crop manifest SHA-256: `bf6014b00ac9b9eeec0cc945e754e078ce04b07940a690f9229cccdda18eaee7`;
- migration head: `0031_executor_pull_channel`.

## Enumerator ownership

- enumerated_set_changed: yes
- enumerator_path: `contracts/api/v1/openapi.json`
- enumerator_owner: `EXEC-IMAGE-DELIVERY-01`
- totality_query: list every OpenAPI operationId and compare with the served router and regenerated client.

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

- `docs/program/tasks/EXEC-IMAGE-DELIVERY-01.md`
- `docs/program/EXEC-IMAGE-DELIVERY-01.md`
- `docs/program/CURRENT_STATE.md`
- `docs/program/ALPHA_ROADMAP.md`
- `docs/program/P02_SEAMS.md`
- `docs/program/CONTRACT_PIN_REGISTRY.md`
- `docs/program/dispatch/EXECUTOR-CONNECTIONS-PLAN.md`
- `contracts/**`
- `src/auditmanager/executors/**`
- `src/auditmanager/bootstrap/runner.py`
- `src/auditmanager/bootstrap/composition.py`
- `src/auditmanager/api/routers/runner.py`
- `src/auditmanager/api/routers/ports.py`
- `src/auditmanager/api/routers/__init__.py`
- `src/auditmanager/api/routers/declarations.py`
- `src/auditmanager/api/routers/errors.py`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/api/app.py`
- `src/auditmanager/api/README.md`
- `src/auditmanager/api/security.py`
- `infra/deploy/proxy/nginx.conf`
- `infra/deploy/proxy/tls-server.conf`
- `infra/deploy/README.md`
- `infra/deploy/serve.py`
- `src/auditmanager/analysis/engine/result.py`
- `src/auditmanager/api/health.py`
- `tools/executor-runner/**`
- `tests/integration/executors/**`
- `tests/unit/executor_runner/**`
- `tests/unit/executors/**`
- `tests/contract/api_v1/**`
- `tests/contract/test_proxy_rate_limits.py`
- `tests/contract/domain_p02/**`
- `tests/integration/api/**`
- `tests/support/expected_facts.json`
- `web/openapi/openapi.json`
- `web/src/shared/api/credentialed-forward.ts`
- `web/src/shared/api/authorization.ts`
- `web/src/app/bff/v1/[...path]/route.ts`
- `web/src/shared/api/generated/**`
- `web/FRONTEND_LOCK.json`
- `web/tests/contract/**`
- `web/tests/guards/**`
- `web/tests/unit/**`
- `VERSION`

## Forbidden hotspots

Database migrations, root dependency and lock files, unrelated composition
roots and global styles. No deployed runtime files, runtime token or `origin/main`.

## Non-goals

No W56b model prompt, vision judgment, route/assignment, finding publication,
provider price or live paid call. This task grants transport only. It does not
replace the saved crop custody check or change the active `text_analysis` stage.

## Deliverables

Task-scoped image descriptor and binary read on the runner API, server and
client byte checks, image-capable Codex command, explicit refusal from text-only
clients, versioned contract/client reseal, focused tests and paired report.

## Required tests

- Focused executor runner unit and integration tests: pass.
- API document, generated client, route/authorization and contract-version checks: pass.
- Python compile, web typecheck, `git diff --check`, allowed-path handoff: pass.
- Full `make gate`: deferred under `R-135` for intermediate development work.

## Integration contract

The future image stage passes one already checked saved-crop Blob reference and
its content digest/size under a current Attempt. The pull task stores only the
reference, never a second copy of the PNG. The claim names the image; the same
runner token may fetch its bytes only while it owns the live claim. The API
verifies the saved bytes before returning `image/png`. The agent verifies them
again, writes a private temporary file and passes it as a Codex `--image` input.

## Failure/idempotency/security cases

Wrong token, connection, task, image or revoked claim: refuse without bytes.
Expired deadline, stale Attempt, wrong digest/size, oversized image or
unsupported client: fail closed. Redelivery of a claim and a repeated image
fetch are idempotent. No token, prompt, image bytes, internal object key or
temporary path enters a log or error message.

## Rollback / feature flag

The image field is optional and no current stage emits it, so the active text
path remains callable. Roll back this slice before activating W56b image work;
existing text tasks and task table rows remain valid.

## Handoff

- Changed files, checks, contracts, limitations and integration instructions:
  paired report.
