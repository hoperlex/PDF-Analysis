# Task P5-META-01 — beta/v1 roadmap and recalibrated forecast

> **Status: specified; not dispatchable.** Planned for P05, after the evidence
> disposition is accepted.

## Outcome

A beta/v1 roadmap containing only ratified `adopt` and `simplify` work, with a P50/P80
table whose basis is measured P01–P04 throughput rather than assumption, and whose totals
are the arithmetic sum of their rows.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until it is
accepted and integrated:

  - `P5-ARC-01` — evidence disposition accepted

## Frozen inputs

- the `P5-ARC-01` disposition table at its accepted commit
- measured throughput handed off by `P1-INT-01` for P01 and by `P4-INT-01` for P02–P04:
  elapsed wall-clock per stage, per-task authoring elapsed time and rejection/remediation
  rounds per accepted task, each with the command and tree that produced it
- the FF-01 §9 estimate style: rows, an explicit arithmetic-sum statement and a statement
  of what is parallel inside a row
- migration head: not touched

## Allowed paths

- `docs/program/BETA_ROADMAP.md`
- `docs/program/ROADMAP.md` — the `## Estimates` section only
- `docs/navigation/incidents/p5-meta-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P5-META-01.md`
- `docs/navigation/entries/p5-meta-01.json`

## Forbidden hotspots

- `docs/program/P05_EVIDENCE_DISPOSITION.md` and every proposed ADR
- `PROTOTYPE_FOUNDATION_FREEZE.md`, profile foundation invariants, all PC-02 evidence
- `docs/program/CHECKPOINT_REGISTRY.md`, `docs/program/CURRENT_STATE.md` and
  `docs/INDEX.md`, owned by `P5-INT-01`
- `docs/stages/S00`–`S10`: no bulk rewrite

## Non-goals

- No estimate for work not disposed as `adopt` or `simplify`.
- No velocity extrapolated from the repository's pre-pivot planning activity.
- No production-readiness or pilot-date commitment.

## Deliverables

- the beta/v1 roadmap: stages, gates, checkpoints and entry requirements
- a P50/P80 table with one row per beta task, the arithmetic-sum statement and per-row
  parallelism
- a calibration section replacing the pending block: for each measured figure, the value,
  the command and the tree
- an explicit list of beta rows that remain uncalibrated because they have no analogue in
  P01–P04, marked as such rather than filled in
- disposition of the S00–S10 backlog by reference, without rewriting those files

## Required tests

- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.
- Manual arithmetic check: each stated total equals the sum of its rows at P50 low, P50
  high, P80 low and P80 high, checked independently.
  Expected: four exact matches, no rounding.
- Manual check: every calibrated row names a command and a tree, and no row cites
  pre-pivot activity. Expected: pass.

## Integration contract

`P5-INT-01` accepts the roadmap as the PC-03 deliverable. No implementation is dispatched
from it before PC-03 acceptance.

## Failure/idempotency/security cases

- A row without a measurement is marked uncalibrated with its named trigger, never filled
  with an invented figure.
- Recomputing the totals from the rows reproduces the stated totals exactly.
- No customer, expert-identity or cost-contract detail enters the roadmap.

## Rollback / feature flag

Documentation only. Revert the integration commit; the prior `ROADMAP.md` estimates
section is restored intact.

## Estimate

Effort P50 2.5 person-days, P80 4.0 person-days. Basis: roadmap authoring plus one calibration pass over four
stages of measured data. This is the task that ends the calibration-pending state.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- changed files and the arithmetic check results
- calibrated versus uncalibrated rows
- unresolved owner decisions
