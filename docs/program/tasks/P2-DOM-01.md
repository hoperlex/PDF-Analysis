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

  - `P2-INT-00` — pins and the environment contract accepted
  - owner decision `OD-12`, the decision author identity, because this task writes the
    migration head that must carry its column; deciding it later is a schema change

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
- `docs/navigation/incidents/p2-dom-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
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
  knowledge base, outbox, lease, export or job/attempt execution.

## Deliverables

- forward migrations creating the project, document, document version, input manifest,
  blob metadata, audit run, command record, stage result, finding, finding observation,
  finding evidence, model call, expert decision event and audit event tables. There is no
  job, attempt, lease or export table: PC-01 has no Job and no Attempt, and the CSV export
  is computed on request rather than stored
- prefixed identifier types generating exactly the contract prefixes and matching the
  contract identifier pattern
- a transition guard for the audit run, blob, import and command idempotency machines that
  encodes the **declared state topology** — the initial state, the allowed transitions and
  the terminal set — and refuses any undeclared transition with
  `state_transition_not_allowed`. It does **not** claim generated coverage of every
  predicate in `state-machines.json`: the `job` and `attempt` machines are not instantiated
  in PC-01 at all, and the `audit_run` guards listed under `OD-24` are recorded as
  unevaluated in this prototype rather than generated and silently left unreachable
- the twenty-code error catalog as a closed enum plus the error envelope, with `retryable`
  pinned to the catalog value
- database-level append-only enforcement on the expert decision and audit event tables
- constraints encoding that a `succeeded` stage result carries no error, that the run state
  is in the declared set, and that a command key is unique per command type

## Required tests

- Command: `make up && make migrate && make migrate && make check-db`
  Expected: exit `0`; the second migration is a no-op and the P02 head is reported.
- Command: `.venv/bin/pytest tests/contract/domain_p02`
  Expected: exit `0`. The suite asserts three things and claims no more: the declared
  topology of each instantiated machine, that every undeclared transition is refused with
  `state_transition_not_allowed` — including moving a `published` run back to `running` or
  `queued` — and that each guard **applicable to PC-01** fires on its violation. Guards
  listed as unevaluated under `OD-24` are asserted absent, not asserted passing, so the
  suite never reports coverage it does not have.
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

Effort P50 1.75 person-days, P80 3.5 person-days. It narrowed when the job and attempt
tables and their guards left PC-01 scope. Basis: one migration head plus typed primitives generated from the frozen contracts. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- the P02 migration head identifier and the table and constraint list
- the identifier and guard APIs
- error codes not used by PC-01, naming `execution_token_invalid` and `stale_attempt`
  explicitly, since PC-01 has no Job or Attempt to raise them
- declared identifiers PC-01 does not allocate — `job_id`, `attempt_id`, `lease_id`,
  `worker_id`, `export_id`, `comparison_id`, `sheet_link_id`, `norms_snapshot_id`,
  `erasure_request_id`, `import_id` — recorded so the catalog does not silently promise an
  aggregate nobody builds
