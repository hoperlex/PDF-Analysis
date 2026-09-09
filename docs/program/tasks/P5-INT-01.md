# Task P5-INT-01 — PC-03 acceptance and backlog disposition

> **Status: specified; not dispatchable.** Planned as the final P05 task.

## Outcome

An owner-ratified PC-03 record naming the next investment, the accepted ADR set and the
disposition of every deferred candidate, with the programme's live state documents
reconciled to it.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated:

  - `P5-ARC-01` — evidence disposition accepted
  - `P5-META-01` — beta roadmap accepted

## Frozen inputs

- the disposition table, proposed ADRs and beta roadmap at their accepted commits
- `CHECKPOINT_REGISTRY.md` conventions and the CP-00 tag rule: an existing tag is never
  moved, re-pointed or deleted
- migration head: not touched

## Allowed paths

- `artifacts/validation/PC-03/checkpoint-report.md`
- `artifacts/validation/PC-03/known-risks.md`
- `docs/architecture/ADR_INDEX.md` — status transitions for the P05 ADRs only
- `docs/program/CHECKPOINT_REGISTRY.md` — creates and maintains the PC-03 row; no such row exists yet
- `docs/program/CURRENT_STATE.md` — creates and maintains the PC-03 status line
- `docs/INDEX.md` — creates and maintains the PC-03 entry
- `docs/navigation/INDEX.md` — regeneration only
- `docs/navigation/entries/p5-int-01.json`
- `docs/navigation/incidents/p5-int-01.jsonl`
- `docs/program/tasks/P5-INT-01.md`

## Forbidden hotspots

- ADR bodies, the disposition table, the beta roadmap and all PC-02 evidence
- `artifacts/checkpoints/CP-00/**`, `v0.0.0-architecture` and every existing tag
- `PROTOTYPE_FOUNDATION_FREEZE.md`, profile foundation invariants, `contracts/**`,
  `src/**`, `web/**`

## Non-goals

- No self-authored acceptance: the integrator does not accept work it coordinated and
  does not decide the next investment.
- No implementation dispatch inside this task.

## Deliverables

- the PC-03 checkpoint report in the `CHECKPOINT_REPORT_TEMPLATE.md` shape
- the owner's verbatim acceptance record naming the chosen next investment
- ADR status transitions from `proposed` to `accepted` for exactly the ADRs the owner
  ratified
- registry, `CURRENT_STATE.md` and `docs/INDEX.md` reconciliation, including the deferred
  candidates and each one's flip condition
- the regenerated navigation index

## Required tests

- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.
- Command: `git tag --list` before and after
  Expected: identical unless the owner explicitly authorized a new tag; no existing tag
  moved.
- Command: `.venv/bootstrap/bin/python tools/navigation/generate_index.py --check`
  Expected: exit `0`; the committed index matches a fresh generation.
- Manual check: every ADR moved to `accepted` appears in the owner's verbatim record and
  no other ADR changed status. Expected: exact set match.
- Manual check: every deferred candidate carries a flip condition. Expected: pass.

## Integration contract

Beta implementation is dispatchable only from an accepted PC-03 record. Absent it, the
programme's authorized scope remains PC-01 plus PC-02 evidence.

## Failure/idempotency/security cases

- A candidate absent from the owner's record is never accepted by inference from the
  report's recommendation.
- An accepted ADR is superseded by a new ADR, never edited.
- Rerunning the navigation regeneration changes no tracked file beyond the index.

## Rollback / feature flag

Documentation only. Revert the integration commit; PC-02 evidence and the beta roadmap
stand under their own commits.

## Estimate

Effort P50 1.5 person-days, P80 3.0 person-days. Basis: reconciliation plus one owner-response cycle.
Calibration pending.

## Handoff

- changed files and containment proof
- the owner record, the accepted ADR set and the deferred list
- next dispatchable work and its gate
