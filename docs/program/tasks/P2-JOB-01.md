# Task P2-JOB-01 — AuditRun, Job and Attempt, command idempotency and the local orchestrator

> **Status: specified; not dispatchable.** Planned for P02.

## Outcome

An accepted audit command creates one durable audit run with its job and first attempt, a
single local process drives the four stages through the declared transitions, and a restart
leaves no run falsely `running`.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until the
first is accepted and integrated, and it may not be accepted until the other two are:

  - `P2-DOM-01` — the P02 migration head and the transition guard
  - `P2-META-01` — supplies the input-manifest query this orchestrator consumes
  - `P2-ENG-01` — supplies the stage-runner seam this orchestrator drives

## Frozen inputs

- domain contract: the audit run, job, attempt and command idempotency machines, and the
  `run_lifecycle` rules of `stage-registry.json` recording owner decision PD-03
- analysis contract: the stage order `source_preparation`, `page_geometry_extraction`,
  `document_context_build`, `text_analysis`
- migration head: the P02 head, read only
- base commit: the accepted `P2-DOM-01` integration commit, plus the seam signatures frozen
  in `PROTOTYPE_EXECUTION_PLAN.md`

## Allowed paths

- `src/auditmanager/jobs/**`
- `tests/integration/jobs/**`
- `docs/program/tasks/P2-JOB-01.md`
- `docs/navigation/entries/p2-job-01.json`

## Forbidden hotspots

- `db/migrations/**`, root locks, the composition root and the `Makefile`
- `src/auditmanager/{documents,ingest,storage,analysis,findings,decisions,api}/**`
- `contracts/**`, `fixtures/**`, `tests/integration/{db,storage,foundation}/**`

## Non-goals

- No automatic retry, backoff, dead-letter queue, distributed lease, heartbeat, outbox or
  remote worker.
- No resume of an interrupted run, no cancel endpoint, no cross-run matching.
- No stage implementation and no model call.

## Deliverables

- a run command handler implementing PD-03: a new key creates a run, job and first attempt;
  the same key with the same payload returns the existing run and mints nothing, including
  for a terminal run; the same key with a different payload returns `idempotency_key_reuse`;
  and a new key over a terminal run creates a new run while the old row stays unchanged
- the frozen-at-creation set persisted on the run: the version and blob set, the analysis
  profile and the prompt bundle; the norms snapshot stays null and is never populated
- a sequential in-process orchestrator walking `created` to `queued` to `running` to
  `validating` to a terminal state, with the job self-leasing to a fixed local worker and
  one attempt carrying an opaque execution token
- a publication fence comparing the token for equality inside the publishing transaction
  and refusing publication on mismatch
- one stage result row per attempt and stage
- startup reconciliation marking a `running` attempt with no live process as `lost`, its
  job and run `failed` with a typed error, and an unresolvable in-progress command record
  as `abandoned` so a repeat under that key returns `idempotency_key_stale`

## Required tests

- Command: `make foundation`
  Expected: exit `0`.
- Command: `.venv/bin/pytest tests/integration/jobs`
  Expected: exit `0`. The suite asserts a full happy path over a stubbed stage runner
  reaching `published`; that the same key and payload returns identical run, job and
  attempt identities and inserts no row; that a changed payload returns
  `idempotency_key_reuse`; that a new key over a terminal run creates a new run and leaves
  the old row byte-identical; that every attempt to move a terminal run back to `queued`,
  `running` or `validating` returns `state_transition_not_allowed`; that a simulated kill
  during `running` followed by reconciliation yields a lost attempt, a failed job and a
  failed run with a typed error and never `running`; that a repeat under the abandoned key
  returns `idempotency_key_stale`; and that a stale execution token cannot publish.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Provides the start-audit command and the run and stage read model, and consumes the stage
runner seam. Only this module writes the audit run, job, attempt, command record and stage
result tables.

## Failure/idempotency/security cases

- `GJ-02-EO-01` is honored in its non-silent half only: a stale `running` becomes an
  explicit terminal state. PC-01 does not resume, because the profile defers resume.
- Progress is a projection and never authorizes publication.

## Rollback / feature flag

Not applicable: no prior behavior. Revert the module; runs are disposable in P02.

## Estimate

P50 2.5 days, P80 4.5 days.

## Handoff

- the public command and query API and the transition table actually implemented
- the restart contract and the reconciliation command
- states declared but unreachable in PC-01
