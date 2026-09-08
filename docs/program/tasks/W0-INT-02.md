# Task W0-INT-02 — reconcile the live state and issue a truthful CP-00 evidence bundle

## Outcome

A CP-00 candidate whose live records describe the tree they ship in, whose evidence
bundle names only artifacts that exist, whose manifest separates the immutable reviewed
input from the final checkpoint state with per-file hashes, and whose two ratification
gates agree — leaving `W0-INT-03` a minimal, explicitly bounded delta and nothing else.

## Depends on

- `W0-QA-04`, accepted and integrated — its integration commit is this task's base

## Frozen inputs

- domain contract: `contracts/domain/v1/**` at `1.0.0-draft.1`, candidate revision 5 — read only
- API contract: none exists at CP-00
- analysis/comparison/event contract: `contracts/analysis/v1/**`, `contracts/events/v1/**` at `1.0.0-draft.1` — read only
- migration head: `none`
- base commit: the `W0-QA-04` integration commit, recorded by the integrator at dispatch
- immutable reviewed candidate: `92e13fa496a723ed6e4c3adbf138c4f4e1d7c368`
- immutable historical bundle: every `manual-report-round-*.md` and
  `automated-report-round-*.md` already committed — quoted, never rewritten
- local tag `v0.0.0-architecture` — read only, never moved

## Allowed paths

- `artifacts/checkpoints/CP-00/**` except the historical round reports listed above
- `docs/program/CURRENT_STATE.md`
- `docs/program/CHECKPOINT_REGISTRY.md`
- `docs/program/waves/W0.3_ratification_integration.md`
- `docs/program/tasks/W0-INT-01.md`, `docs/program/tasks/W0-INT-03.md` — status and
  handoff text only
- `docs/architecture/CP00_ARCHITECTURE_REVIEW.json` — the `review_status` field only, and
  only to make the two gates agree
- `docs/INDEX.md`, `docs/stages/S00_architecture_and_behavior_freeze.md`

## Forbidden hotspots

- `contracts/**`, `fixtures/**`, `scripts/**`
- `tests/**` — `W0-QA-04`'s, and frozen by its acceptance
- every `docs/architecture/**` file other than the single field named above
- the historical round reports: immutable. A superseded statement in them is corrected by
  an **erratum that quotes it**, never by editing the report
- root dependency and lock files, migration head, composition root, global styles
- the local tag: not moved, not deleted, not re-pointed. No new tag is created by this task

## Non-goals

- No ratification. `ratified` stays as it is; this task makes ratification *possible* and
  bounded, and `W0-INT-03` performs it.
- No tag, no push, no fast-forward of `main`.
- No new test or checker: `W0-QA-04` owns the contour and it is frozen.
- No rewriting of history to make a past claim true.

## Deliverables

1. **Erratum** — `artifacts/checkpoints/CP-00/erratum.md`. For each false or unsupported
   claim in the shipped bundle: the exact quote, its location, what is true, and how it
   was measured. At minimum it must cover the claims recorded as `CP00-B3` and §3.2 of the
   execution plan: the non-existent `tests/checkpoint/test_cp00_mechanism.py` and
   `tests/contract/test_cp00_contracts.py`, the "103 tests" figure against a 324-test
   contour, the duplicated manual report, the manual tester without a stable identifier,
   the three manual findings absent from the risk note, and the `PD-05` range whose result
   text stops at `PD-04`.
2. **Complete per-file manifest** — every file the checkpoint certifies, with its own
   SHA-256, and for each aggregate digest an explicit statement of which files roll into
   it and what it is for. The immutable reviewed input manifest and the final checkpoint
   manifest are separate objects; no aggregate may carry members it does not list.
3. **Live state reconciliation** — `CURRENT_STATE.md`, the checkpoint registry, the W0.3
   wave plan, the `W0-INT-01` banner, `docs/INDEX.md` and the S00 checklist agree with one
   another and with the manifest. The corrupted splice at `CURRENT_STATE.md:268` is
   repaired.
4. **Ratification-ready semantics** — one recorded disposition on the canonical value of
   `review_status`, applied on both sides so that `W0-INT-01`'s assertion at line 180 and
   the architecture review agree. The disposition names which side moved and why.
5. **The `W0-INT-03` delta** — the exact minimal set of paths and field values the primary
   reviewer will change to ratify, written into `docs/program/tasks/W0-INT-03.md`. Nothing
   outside it may be required to reach the ratified state.

## Required tests

- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/contract`.
  Expected: exit `0`.
- Command: `.venv/bootstrap/bin/python -m unittest discover -s tests/checkpoint`.
  Expected: exit `0`.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`.
  Expected: exit `0`, standalone `PASS`.
- Command: `.venv/bootstrap/bin/python -c "import json; from pathlib import Path; r=json.loads(Path('docs/architecture/CP00_ARCHITECTURE_REVIEW.json').read_text()); assert r['review_status']=='ratified'"`.
  Expected: exit `0` — the two gates agree. If the recorded disposition moves the other
  side instead, this command is replaced in `W0-INT-01` and both files say so.
- Command: `git status --porcelain -uall -- contracts fixtures scripts tests docs/architecture`.
  Expected: a path set containing **only** the single architecture-review field's file, if
  the disposition moved that side; otherwise empty. Assert containment, accept empty.
- Command: `git rev-list -n1 v0.0.0-architecture`.
  Expected: `39a3a6430bd97c38cb20bafc793fc9d077d0df8e`, unchanged.

Measure in a clone or the main checkout, never in a linked worktree, and never while
anything else clones this repository.

## Integration contract

The integrator can rely on: every live record agrees with the manifest and with every
other live record; every artifact the bundle names exists at the path it names; every
aggregate hash lists its members; both ratification gates assert the same value; and the
`W0-INT-03` delta is sufficient and minimal — applying exactly it reaches the ratified
state, and applying less does not.

## Failure/idempotency/security cases

- Re-running the reconciliation on an already-reconciled tree changes nothing.
- A claim that cannot be measured is recorded as unmeasured, not asserted.
- No historical report is edited; a superseded statement is corrected only by erratum.
- The task writes no ref and creates no tag.

## Rollback / feature flag

Not applicable: documentation and evidence records. Rollback is reverting the integration
commit; the immutable reviewed families and the tag are untouched either way.

## Handoff

- changed files: the exact list, proved a subset of allowed paths
- commands/results: every required test verbatim with measured exit codes
- known limits: every claim that remains unmeasured or unrepairable inside the freeze,
  with its owner
- integration notes: the recorded `review_status` disposition, and the exact
  `W0-INT-03` delta with a statement of why it is minimal
