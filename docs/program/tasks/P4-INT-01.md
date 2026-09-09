# Task P4-INT-01 — PC-02 validation report and acceptance record

> **Status: specified; not dispatchable.** Planned for P04, after the sessions and ledger
> are accepted.

## Outcome

One report stating, per criterion, whether PC-02 passed, failed or is blocked, with every
figure carrying the command and the tree that produced it, plus an owner acceptance
record in the `FF-01 ACCEPTED` form.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P4-BHV-01` — labelled session dataset accepted
  - `P4-OPS-01` — measurement ledger accepted

## Frozen inputs

- the labelled dataset and ledger at their accepted commits, read only
- the PC-02 criteria in `PROTOTYPE_EXECUTION_PLAN.md`, frozen before `P4-BHV-01` starts;
  a threshold is never set after seeing data
- `CHECKPOINT_REGISTRY.md` prototype-checkpoint conventions
- migration head: not touched

## Allowed paths

- `docs/program/validation/PC-02_REPORT.md`
- `artifacts/validation/PC-02/checkpoint-report.md`
- `artifacts/validation/PC-02/known-risks.md`
- `docs/program/CHECKPOINT_REGISTRY.md` — creates and maintains the PC-02 row; no such row exists yet
- `docs/program/CURRENT_STATE.md` — creates and maintains the PC-02 status line
- `docs/INDEX.md` — creates and maintains the PC-02 entry
- `docs/navigation/entries/p4-int-01.json`
- `docs/navigation/INDEX.md` — regeneration only, as the integration owner of the P04
  batch and the fifth writer in the sequence
- `docs/navigation/incidents/p4-int-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P4-INT-01.md`

## Forbidden hotspots

- `artifacts/validation/PC-02/sessions/**` and `.../ledger/**`: evidence is read, never
  edited
- `artifacts/checkpoints/CP-00/**` and every Git tag
- `docs/navigation/entries/**` owned by other tasks, and the navigation schema and tooling
- `PROTOTYPE_FOUNDATION_FREEZE.md`, profile foundation invariants, `contracts/**`,
  `src/**`, `web/**`

## Non-goals

- No architecture decision, roadmap or candidate disposition — that is P05.
- No threshold adjusted to make a criterion pass.
- No repair of a defect the report identifies.

## Deliverables

- the PC-02 report: each criterion with its measured value, the command and tree that
  produced it, and a verdict of `PASS`, `FAIL`, `FAIL-PRODUCT`, `BLOCKED` or `OBSERVATION`
- the sample-size statement from the execution plan reproduced verbatim
- ranked capability-gap and friction findings, each traceable to named session records
- every rate in the instrument-validity and product-floor gates computed over **measurable
  documents only**; negative-envelope documents are reported as a separate
  refusal-observation count and never enter a denominator
- the list, by path, of the evidence inputs `P5-ARC-01` may cite
- the regenerated `docs/navigation/INDEX.md`, and the navigation incident summary for the
  P04 batch with its zero-versus-absent determination
- the owner acceptance record, quoted verbatim
- registry and state row updates
- measured P02/P03/P04 throughput handed to `P5-META-01`

## Required tests

- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `.venv/bin/python tools/validation/ledger_report.py --validate-sessions
  artifacts/validation/PC-02/sessions`
  Expected: exit `0`; the report never aggregates an incomplete dataset.
- Command: `.venv/bootstrap/bin/python tools/navigation/validate_navigation.py`
  Expected: exit `0`; every P04 fragment validates and no `implemented` entry names a path
  that does not exist.
- Command: `.venv/bootstrap/bin/python tools/navigation/generate_index.py --check`
  Expected: exit `0`; the committed index is byte-identical to a fresh generation.
- Command: `git diff --check`
  Expected: exit `0`.
- Manual check: every numeric claim names the command and the tree that produced it, and
  no static count is presented as a measurement. Expected: pass.
- Manual check: the criteria table is byte-identical to the criteria frozen before
  `P4-BHV-01`. Expected: pass.

## Integration contract

P05 is dispatchable only on an accepted PC-02 record. `P5-ARC-01` may cite only evidence
listed in this report's inputs section.

## Failure/idempotency/security cases

- A `FAIL-PRODUCT` on the product floor does not authorize foundational architecture
  change; it routes to P05 as the leading evidence.
- No secret, expert identity or unanonymized quotation enters the report.
- Regenerating the report from the same evidence tree produces the same values.

## Rollback / feature flag

Documentation only. Revert the integration commit; the session evidence stands under its
own accepted commit.

## Estimate

Effort P50 2.5 person-days, P80 5.0 person-days. Basis: aggregation over a validated
dataset plus one owner-response cycle. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- changed files and containment proof
- commands/results
- criteria outcomes and unresolved owner decisions
- measured P02/P03/P04 throughput for the `P5-META-01` recalibration
