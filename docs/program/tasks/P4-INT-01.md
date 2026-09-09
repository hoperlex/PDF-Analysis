# Task P4-INT-01 — PC-02 validation report and acceptance record

> **Status: specified; not dispatchable.** Planned for P04, after the session
> dataset is accepted and the validation period is therefore closed.

## Outcome

One report stating, per criterion, whether PC-02 passed, failed or is blocked, with every
figure carrying the command and the tree that produced it, plus an owner acceptance
record in the `FF-01 ACCEPTED` form.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P4-BHV-01` — labelled session dataset accepted; the validation period is therefore
    closed and its ledger can be extracted for the first time
  - `P4-OPS-01` — measurement tooling and pre-session snapshot accepted

## Frozen inputs

- the labelled session dataset at its accepted commit, read only
- the `P4-OPS-01` tooling at its accepted commit, run **unmodified**: this task produces
  the ledger by invoking accepted tooling, not by writing a second extractor
- the `P4-OPS-01` pre-session snapshot, read only, as the baseline the validation-period
  ledger is differenced against so study activity is distinguishable from what preceded it
- the PC-02 criteria in `PROTOTYPE_EXECUTION_PLAN.md`, frozen before `P4-BHV-01` starts;
  a threshold is never set after seeing data
- `CHECKPOINT_REGISTRY.md` prototype-checkpoint conventions
- migration head: not touched

## Allowed paths

- `artifacts/validation/PC-02/ledger/**` — the **final validation-period ledger**. This
  task is its sole writer, and writes it only after `P4-BHV-01` is accepted: the period is
  the sessions, so the ledger cannot exist before they end. It is produced by running the
  accepted `P4-OPS-01` tooling over the closed period and differencing the pre-session
  snapshot; it is committed before any report prose is written, so the report is derived
  from a committed ledger rather than from numbers that live only in the author's terminal
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

- `artifacts/validation/PC-02/sessions/**`: session evidence is read, never edited
- `artifacts/validation/PC-02/preflight/**`: the pre-session snapshot and gap register are
  read, never edited or merged into the validation-period ledger
- `tools/validation/**`: the accepted tooling is invoked, never modified. A tool defect
  goes back to `P4-OPS-01` with a reproduction rather than being patched here
- `artifacts/checkpoints/CP-00/**` and every Git tag
- `docs/navigation/entries/**` owned by other tasks, and the navigation schema and tooling
- `PROTOTYPE_FOUNDATION_FREEZE.md`, profile foundation invariants, `contracts/**`,
  `src/**`, `web/**`

## Non-goals

- No architecture decision, roadmap or candidate disposition — that is P05.
- No threshold adjusted to make a criterion pass.
- No repair of a defect the report identifies.

## Deliverables

- the **final validation-period ledger** under `artifacts/validation/PC-02/ledger/`,
  produced first and committed before any report prose exists, by running the accepted
  `P4-OPS-01` tooling unmodified over the closed session period and differencing the
  pre-session snapshot. This task is its only writer; `P4-OPS-01` wrote the preflight
  snapshot, never this
- the PC-02 report, derived from that committed ledger: each criterion with its measured
  value, the command and tree that produced it, and a verdict of `PASS`, `FAIL`,
  `FAIL-PRODUCT`, `BLOCKED` or `OBSERVATION`
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
- Command: `.venv/bin/python tools/validation/ledger_report.py --self-check`
  Expected: exit `0`, reproducing the fixture figures exactly as it did for `P4-OPS-01`.
- Manual check: tool provenance, established from outside the tool, because a program cannot
  attest its own bytes — record
  `git log -1 --format=%H -- tools/validation/ledger_report.py` and confirm it equals the
  commit named in `P4-OPS-01`'s accepted handoff.
  Expected: identical; the ledger was produced by accepted code, not a local variant.
- Command: `.venv/bin/python tools/validation/ledger_report.py --period
  artifacts/validation/PC-02/sessions --baseline artifacts/validation/PC-02/preflight
  --out artifacts/validation/PC-02/ledger`
  Expected: exit `0`; writes the validation-period ledger, reads the preflight baseline
  without modifying it, and reports study activity separately from the pre-existing
  activity the baseline records.
- Command: `.venv/bin/python tools/validation/ledger_report.py --validate-sessions
  artifacts/validation/PC-02/sessions`
  Expected: exit `0`; the report never aggregates an incomplete dataset. The navigation
  incident metric covers the **P04 wave only** and uses the shared status-aware rule: zero
  only when every P04 task returned `recorded` or `none_observed`; `practice_not_exercised`
  or a missing status makes it `absent` with the non-reporting tasks named.
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

Effort P50 2.5 person-days, P80 5.0 person-days. Unchanged: the basis already priced one
serial integration pass over a validated dataset, and running accepted tooling to emit the
ledger belongs to that pass rather than being new build work. Basis: aggregation over a validated
dataset plus one owner-response cycle. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- changed files and containment proof
- commands/results
- criteria outcomes and unresolved owner decisions
- measured P02/P03/P04 throughput for the `P5-META-01` recalibration
