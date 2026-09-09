# Task P5-ARC-01 — evidence-to-candidate architecture disposition

> **Status: specified; not dispatchable.** Planned for P05, after `PC-02` acceptance.

## Outcome

Every P05 candidate carries a disposition — `adopt`, `simplify`, `defer, evidence not
observed` or `reject` — each justified by a named PC-02 measurement or explicitly marked
as unbacked.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until it is
accepted and integrated:

  - `P4-INT-01` — `PC-02` accepted

## Frozen inputs

- the PC-02 report and its listed evidence inputs, read only
- the candidate list in `ROADMAP.md` P05 and `PROTOTYPE_PROFILE.md` §9
- the decision rule in `PROTOTYPE_EXECUTION_PLAN.md`, frozen before analysis begins
- owner decision `OD-21`, the stop rule, if PC-02 returned `FAIL-PRODUCT`
- accepted ADRs 0001–0019: read only; an accepted ADR is immutable history per Bible §14
- migration head: not touched

## Allowed paths

- `docs/program/P05_EVIDENCE_DISPOSITION.md`
- new `docs/architecture/adr/ADR-00NN-*.md` files with `Status: proposed` only
- `docs/navigation/incidents/p5-arc-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P5-ARC-01.md`
- `docs/navigation/entries/p5-arc-01.json`

## Forbidden hotspots

- every existing ADR file and `docs/architecture/ADR_INDEX.md`, owned by `P5-INT-01`
- `ARCHITECTURE_BIBLE.md`, `PROTOTYPE_FOUNDATION_FREEZE.md`, profile foundation invariants
- `contracts/**`, `src/**`, `web/**`, all PC-02 evidence
- `docs/program/ROADMAP.md`, owned by `P5-META-01`

## Non-goals

- No implementation, schema or contract change.
- No candidate adopted because it appears in the S00–S10 backlog.
- No new candidate invented that PC-02 evidence does not name.

## Deliverables

- a disposition table of candidate by disposition by the named measurement that decided
  it, with the evidence path
- for every `adopt`, a proposed ADR stating what changes and what measurement would
  falsify it
- for every `defer`, the specific measurement that would later flip it
- an explicit list of candidates that P04 evidence cannot decide at all — multi-tenant
  AuthZ, retention, backup and SLO among them, because P04 used no production data

## Required tests

- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.
- Command: `git diff --name-only <pc02_commit>..HEAD -- docs/architecture/adr`
  Expected: only new `ADR-00NN-*.md` files; no existing ADR modified.
- Manual check: every `adopt` row cites an evidence path present in the PC-02 input list,
  and no row cites the backlog as its justification. Expected: pass.
- Manual check: every proposed ADR names its falsifying measurement. Expected: pass.

## Integration contract

`P5-META-01` schedules only `adopt` and `simplify` rows. `P5-INT-01` records only the
dispositions the owner ratifies. This task recommends and never decides.

## Failure/idempotency/security cases

- An unbacked candidate defaults to `defer, evidence not observed`, never to `adopt` and
  never to a permanent `reject` that would have to be re-litigated.
- A disappointing PC-02 product result does not license changing the accepted foundation.
- No PC-02 evidence file is modified; disagreement is recorded as new text.

## Rollback / feature flag

Documentation only; proposed ADRs are inert until accepted. Revert the integration commit.

## Estimate

Effort P50 2.5 person-days, P80 5.0 person-days. Basis: seven or more candidates, each needing an evidence trace
and a proposed ADR where adopted. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- disposition table, and the **exact repository paths** of every ADR file this task
  created, each with `Status: proposed`, listed one per line as
  `docs/architecture/adr/ADR-00NN-<slug>.md`. That list is the authority for what
  `P5-INT-01` may later transition: an ADR absent from this list stays untouchable, so the
  handoff cannot silently widen `P5-INT-01`'s reach over the ADR corpus
- confirmation that no pre-existing ADR file and no `ADR_INDEX.md` row was modified, and
  that the path list above is exactly `git diff --name-only <base>..HEAD -- docs/architecture/adr`
  — the list is checked against what was actually created rather than being self-declared,
  because `P5-INT-01` derives its write authority from it
- the index rows the new ADRs still need, which `P5-INT-01` creates: this task delivers ADR
  files and never an `ADR_INDEX.md` row
- candidates undecidable from P04 evidence
- unresolved owner decisions
