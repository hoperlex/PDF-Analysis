# Task P2-DOM-01 — P02 migration head and contract-encoded domain primitives

> **Status: specified; not dispatchable.** Planned for P02. Sole owner of the P02
> migration head.

## Outcome

One migration head creates every PC-01 table with its invariants encoded as database
constraints, and typed identity, state and error primitives make the frozen contracts
executable.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until it is
accepted and integrated:

  - `P2-INT-00` — window 1 pins and composition root accepted

## Frozen inputs

- domain contract: `identifiers.json`, `state-machines.json`, `error-codes.json` and
  `error-envelope.schema.json`
- analysis contract: the stage identity and StageResult status enums in
  `stage-registry.json`
- migration head: the P01 baseline; this task is its sole P02 extender
- base commit: the accepted `P2-INT-00` integration commit

## Allowed paths

- `db/migrations/**`
- `src/auditmanager/shared/db/**`, `src/auditmanager/shared/identity/**`,
  `src/auditmanager/shared/errors/**`, `src/auditmanager/shared/statemachine/**`
- `tests/contract/domain_p02/**`, `tests/integration/domain_p02/**`
- `docs/program/tasks/P2-DOM-01.md`
- `docs/navigation/entries/p2-dom-01.json`

## Forbidden hotspots

- root locks, `Makefile`, `infra/local/**`, the composition root and
  `src/auditmanager/storage/**`
- every bounded-context module: documents, ingest, jobs, analysis, findings, decisions, api
- `contracts/**`, `fixtures/**`, `tests/integration/{db,storage,foundation}/**`

## Non-goals

- No repository, use case, router or stage.
- No generic base repository or ORM framework, and no table for comparison, norms,
  knowledge base, outbox, lease or export.

## Deliverables

- forward migrations creating the project, document, document version, input manifest,
  blob metadata, audit run, job, attempt, command record, stage result, finding, finding
  observation, finding evidence, model call, expert decision event and audit event tables
- prefixed identifier types generating exactly the contract prefixes and matching the
  contract identifier pattern
- a transition guard generated from `state-machines.json` for the audit run, job, attempt,
  blob, import and command idempotency machines, refusing any undeclared transition with
  `state_transition_not_allowed`
- the twenty-code error catalog as a closed enum plus the error envelope, with `retryable`
  pinned to the catalog value
- database-level append-only enforcement on the expert decision and audit event tables
- constraints encoding that a `succeeded` stage result carries no error, that the run state
  is in the declared set, and that a command key is unique per command type

## Required tests

- Command: `make up && make migrate && make migrate && make check-db`
  Expected: exit `0`; the second migration is a no-op and the P02 head is reported.
- Command: `.venv/bin/pytest tests/contract/domain_p02`
  Expected: exit `0`; every declared transition is accepted and every undeclared one is
  refused, including moving a `published` run back to `running` or `queued`.
- Command: `.venv/bin/pytest tests/integration/domain_p02`
  Expected: exit `0` against PostgreSQL; UPDATE and DELETE on the decision ledger are
  refused by the database itself.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Consumers receive tables, identifier factories, the transition guard and the error
envelope. No lane writes DDL; a schema need is submitted to this task as a test plus a
requested constraint.

## Failure/idempotency/security cases

- Re-running the head changes no row.
- An identifier failing the contract pattern is rejected at construction, not at insert.
- A guard bypass is a test failure rather than a warning, per `GJ-03-EO-09` and
  `GJ-03-EO-10`.

## Rollback / feature flag

Forward-only. Before consumers exist, rollback is a revert of the migration commit and a
drop of the disposable local database; never automatic on a populated database.

## Estimate

P50 2 days, P80 4 days.

## Handoff

- the P02 migration head identifier and the table and constraint list
- the identifier and guard APIs
- error codes not used by PC-01
