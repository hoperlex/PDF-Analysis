# Integration policy

## Branches

- `main` — last accepted integration/checkpoint-capable line;
- `integration/<wave>` — single convergence branch;
- `agent/<task_id>` — isolated implementation branch/worktree.

## Merge order

1. contract commit/freeze;
2. low-level providers/adapters and independent test scaffolding;
3. application use cases;
4. API provider;
5. generated client;
6. frontend consumer;
7. observability/ops wiring;
8. integration-only composition/migration reconciliation;
9. E2E/manual evidence.

Actual order may vary if dependencies are explicit, but consumer never precedes missing contract freeze in `main/integration`.

## Conflict ownership

Agent resolves conflicts only within its allowed paths. Conflict in hotspot is handed to integrator. Repeated conflict indicates task decomposition failure and should change next wave design.

## Migration ownership

One migration owner per wave. Parallel lanes submit requested schema changes as contract artifacts/tests; migration owner serializes them from one head.

## Generated code

Generated OpenAPI client is regenerated once per frozen API contract by owner/integrator. Agents must not hand-edit generated files.

## Integration rejection

Integration task rejects a branch if:

- tests were not run or cannot be reproduced;
- it changed a frozen contract without authorization;
- it introduces a new direct data writer;
- it depends on local uncommitted state;
- it exposes S3 keys/secrets;
- retry/idempotency behavior is undefined;
- TODO silently bypasses a required failure/security gate.
