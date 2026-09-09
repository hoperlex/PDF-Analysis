# Task P2-API-01 — frozen OpenAPI v1 surface and typed transport edge

> **Status: specified; not dispatchable.** Planned for P02. Sole owner of the P02 API
> contract family.

## Outcome

One frozen OpenAPI document and its implementation expose exactly the PC-01 journey with
opaque identities, the domain error envelope and idempotency-key handling, so P03 can build
against a fixed contract.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P2-META-01` — ingest commands and queries
  - `P2-JOB-01` — run commands and the run read model
  - `P2-FND-01` — finding queries and the decision ledger

## Frozen inputs

- domain contract: `error-codes.json`, `error-envelope.schema.json` and `identifiers.json`
- API contract: none exists before this task; it creates and freezes `contracts/api/v1/**`
- migration head: the P02 head, read only
- base commit: the accepted integration commit carrying META, JOB and FND

## Allowed paths

- `contracts/api/v1/**`
- `src/auditmanager/api/routers/**`, `src/auditmanager/api/schemas/**`,
  `src/auditmanager/api/errors.py`, `src/auditmanager/api/idempotency.py`
- `tests/contract/api_v1/**`
- `docs/program/tasks/P2-API-01.md`
- `docs/navigation/entries/p2-api-01.json`

## Forbidden hotspots

- `src/auditmanager/api/app.py` and `api/composition.py`, owned by `P2-INT-00`
- `contracts/{domain,analysis,events,comparison}/v1/**`
- `db/migrations/**`, root locks, the `Makefile`, every bounded-context module and `web/**`

## Non-goals

- No authentication, tenancy, role model, rate limiting, WebSocket or server-sent events.
- No CSV or export rendering, which belongs to P03, and no business logic in a router.
- No generated TypeScript client: `P3-API-01` generates it from the frozen document.

## Deliverables

- a frozen OpenAPI document covering exactly: create and list projects; upload one PDF; get
  a version; stream version content for the viewer; start a run; get run status with
  per-stage state; list findings with evidence; get finding detail; append a decision; list
  decision history; request an export and fetch its content
- write commands accepting an idempotency key passed through to the owning command handler
  and never re-derived in the router
- a central mapping from typed domain errors to the error envelope with the catalog's pinned
  retryable flag and a correlation identity on every response
- run status exposing the contract vocabulary and never `succeeded`
- cursor pagination on findings and decision history

## Required tests

- Command: `.venv/bin/pytest tests/contract/api_v1`
  Expected: exit `0`. The suite asserts that the generated schema equals the committed
  document so drift fails; that every error response validates against the envelope and
  carries a catalog code with the catalog's retryable value; that no response body, header
  or error detail contains a bucket name, object key, filesystem path or credential; that
  every identity matches its contract pattern; that a repeated write under one idempotency
  key returns the original resource; that the same key with a different body returns
  `idempotency_key_reuse`; and that an unknown identity returns `not_found` without
  revealing existence.
- Command: `.venv/bin/pytest tests/integration/ingest tests/integration/jobs tests/integration/findings`
  Expected: exit `0`; consumer regression with no provider behavior changed.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

The frozen document is the P03 dispatch precondition. A breaking change requires a new
contract version rather than an edit. Routers hold no business logic and no transaction.

## Failure/idempotency/security cases

- Validation, conflict, not-found, state-transition, idempotency and dependency failures
  each carry a distinct code and a safe message.
- `partial_result_not_publishable` is surfaced verbatim rather than translated into a
  generic internal error.

## Rollback / feature flag

Contract-versioned. Revert the router commit; the contract file remains the record of what
was frozen.

## Estimate

P50 1.5 days, P80 3 days.

## Handoff

- the endpoint table with codes and the frozen contract version
- the idempotency header contract
- the client-generation instruction for `P3-API-01`
