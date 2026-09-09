# Task P2-RUN-01 — persisted AuditRun, sequential local execution and restart reconciliation

> **Status: specified; not dispatchable.** Planned for P02. It replaces the withdrawn
> `P2-JOB-01`: PC-01 has no Job, no Attempt, no lease, no heartbeat, no fencing token, no
> resume, no retry and no outbox.

## Outcome

An accepted audit command creates one durable `AuditRun`, one sequential local executor
drives the four stages and persists a `StageResult` for each, the evidence gate chooses the
terminal state, and a restart leaves no run falsely `running`.

## Depends on

- none complete at plan time

Planned predecessors and dispatch conditions — this task is not dispatchable until each is
accepted and integrated:

  - `P2-DOM-01` — the P02 migration head, the identifier types and the transition guard
  - `P2-FND-01` — the evidence gate this executor calls for terminal selection. The gate
    exists **before** the runner deliberately: the runner never selects `published` itself
    and is never authored against a stub that pretends to.
  - `P2-META-01` — the input-manifest query
  - `P2-ENG-01` and `P2-AI-01` — the four stages the executor drives

## Frozen inputs

- domain contract: the `audit_run` and `command_idempotency` machines, and the
  `run_lifecycle` rules of `stage-registry.json` recording owner decision PD-03
- analysis contract: the stage order `source_preparation`, `page_geometry_extraction`,
  `document_context_build`, `text_analysis`
- migration head: the P02 head, read only
- base commit: the accepted `P2-FND-01` integration commit
- owner decision `OD-10` for the reconciliation vocabulary of a stale `running` run

## Allowed paths

- `src/auditmanager/runs/**`
- `tests/integration/runs/**`
- `docs/program/tasks/P2-RUN-01.md` status/handoff
- `docs/navigation/entries/p2-run-01.json`

## Forbidden hotspots

- `db/migrations/**`, root locks, the composition root and the `Makefile`
- `src/auditmanager/{documents,ingest,storage,analysis,findings,decisions,exports,api}/**`
- `contracts/**`, `fixtures/**`, `tests/integration/{db,storage,foundation}/**`

## Non-goals

- **No Job and no Attempt entity, no lease, no heartbeat, no execution token and no
  fencing.** PC-01 runs one execution per run in one process, so there is no second
  attempt that could supersede a first or deliver a stale result.
- No automatic retry, backoff, dead-letter queue, resume, outbox or remote worker.
- No cancel endpoint, no cross-run matching, no stage implementation and no model call.
- No terminal selection: that belongs to the evidence gate.

## Deliverables

- a run command handler implementing the PD-03 rules that PC-01 exercises: a new
  idempotency key creates a run; the same key with the same payload returns the existing
  run and creates nothing, including for a terminal run; the same key with a different
  payload returns `idempotency_key_reuse`; a new key over a terminal run creates a new run
  and leaves the old row unchanged
- the frozen-at-creation set persisted on the run: the version and blob set, the analysis
  profile and the prompt bundle; the norms snapshot stays null and is read by no PC-01 path
- a sequential in-process executor walking `created` to `queued` to `running` to
  `validating`, calling the evidence gate at `validating` and recording the terminal the
  gate returns
- one `StageResult` row per run and stage, conformant to `stage-result.schema.json`, which
  requires no attempt authority
- startup reconciliation turning a leftover `running` run into the explicit terminal fixed
  by `OD-10`, with a typed interrupted reason, and marking an unresolvable in-progress
  `CommandRecord` `abandoned` so a repeat under that key returns `idempotency_key_stale`
- a recorded scope note: PC-01 implements the `audit_run` guards that do not reference Job
  or Attempt, and does not implement the two attempt-fencing guards, because the hazard they
  defend against cannot occur with one execution per run

## Required tests

- Command: `make foundation`
  Expected: exit `0` on this lane's instance.
- Command: `.venv/bin/pytest tests/integration/runs`
  Expected: exit `0`. The suite asserts a full happy path reaching the terminal the gate
  returns; that the same key and payload returns the identical run identity and inserts no
  row; that a changed payload returns `idempotency_key_reuse`; that a new key over a
  terminal run creates a new run and leaves the old row byte-identical; that every attempt
  to move a terminal run back to `queued`, `running` or `validating` returns
  `state_transition_not_allowed`; that a simulated kill during `running` followed by
  reconciliation yields the explicit interrupted terminal and never `running`; and that a
  repeat under the abandoned key returns `idempotency_key_stale`.
- Command: `.venv/bin/pytest tests/integration/runs -k "terminal_selection_is_delegated"`
  Expected: exit `0`; proves the executor records the gate's terminal and has no code path
  that selects `published` on its own.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

Provides the start-audit command and the run and stage read model, and consumes the
evidence gate for terminal selection. Only this module writes the `audit_run`,
`command_record` and `stage_result` tables. It publishes no `JobPackage` and no
`ResultPackage`, so it makes no conformance claim to those two schemas.

## Failure/idempotency/security cases

- `GJ-02-EO-01` is honored in its non-silent half: a stale `running` becomes an explicit
  terminal state. PC-01 does not resume, because the profile defers resume.
- Progress is a projection and never authorizes publication.
- A run whose gate call fails is terminal-failed with a typed error, never left running.

## Rollback / feature flag

Not applicable: no prior behavior. Revert the module; runs are disposable in P02.

## Estimate

Effort P50 1.5 person-days, P80 3.0 person-days. It is narrower than the withdrawn
`P2-JOB-01` by exactly the durable-execution machinery PC-01 does not need. Basis: one sequential executor over an existing gate, with reconciliation. Calibration pending.

## Handoff

- the public command and query API and the transition table actually implemented
- the restart contract and the reconciliation command
- the scope note naming the two unimplemented guards and the schemas not claimed
