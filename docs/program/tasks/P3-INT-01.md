# Task P3-INT-01 — PC-01 acceptance runbook, live run and checkpoint evidence

> **Status: specified; not dispatchable.** Planned as the final P03 task. Sole writer of
> PC-01 acceptance evidence.

## Outcome

An independent reviewer executes the PC-01 runbook from a clean local start, performs one
live `text_analysis` run that finds at least two seeded issues, completes the
accept/reject/comment loop, downloads the CSV, restarts everything without losing
canonical state, and records the result as the PC-01 checkpoint.

## Depends on

- none complete at plan time

Planned predecessors and dispatch condition — this task is not dispatchable until each
is accepted and integrated, and until a live provider credential is available on the
acceptance instance:

  - `P3-QA-01` — the automated journey suite
  - `P1-INT-01` — `PF-01` accepted

## Frozen inputs

- the accepted P02 and P03 commits, `FOUNDATION_LOCK.json` and `web/FRONTEND_LOCK.json`
- `PROTOTYPE_PROFILE.md` §8 evidence list at its clarified wording
- domain contract state and verdict vocabularies
- migration head: the accepted P02 head, read only
- base commit: the P03 convergence commit supplied at dispatch

## Allowed paths

- `docs/manual-tests/PC-01_prototype.md`
- `artifacts/checkpoints/PC-01/**`
- `docs/program/CHECKPOINT_REGISTRY.md` — creates and maintains the PC-01 row; no such row exists yet
- `docs/program/CURRENT_STATE.md` — creates and maintains the PC-01 status line
- `docs/INDEX.md` — creates and maintains the PC-01 entry
- `docs/navigation/INDEX.md` — regeneration only
- `docs/navigation/entries/p3-int-01.json`
- `docs/navigation/incidents/p3-int-01.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P3-INT-01.md`

## Forbidden hotspots

- every `web/src/**` and `src/**` path, all contracts, migrations, fixtures, and the root
  and web manifests
- `artifacts/checkpoints/CP-00/**`, `PROTOTYPE_FOUNDATION_FREEZE.md`, the profile
  foundation invariants and `docs/navigation/entries/**` owned by other tasks

## Non-goals

- No defect repair in any slice, no scope addition, no P04 execution.
- No production-deployment claim and no tag.

## Deliverables

- the numbered reviewer runbook recorded in `PROTOTYPE_EXECUTION_PLAN.md`, with exact
  commands and expected results
- an executed acceptance record: environment, commits, image digests, migration head,
  provider mode per run, and measured elapsed time per step with the method that measured it
- the produced CSV, the live-run and recorded-run artifacts, and a screenshot set showing
  the page-beside-quotation view, the decision ledger after a later comment and the
  provider-mode badge
- a defect register separating prototype-blocking from advisory findings under the profile
  gate classes
- the regenerated navigation index built from the fragments the other tasks own

## Required tests

- Command: the full PC-01 runbook
  Expected: every numbered step passes as written.
- Command: `make foundation` from a clean clone
  Expected: exit `0`.
- Command: `npm --prefix web ci && npm --prefix web run build`
  Expected: exit `0`.
- Command: `npm --prefix web run e2e:pc01`
  Expected: exit `0`.
- Command: `.venv/bootstrap/bin/python tools/navigation/generate_index.py --check`
  Expected: exit `0`; the committed index matches a fresh generation.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

PC-01 is claimed only by this record. No earlier task may assert a working prototype. The
record names the exact commits certified and which steps were manual rather than
automated.

## Failure/idempotency/security cases

- A live-provider failure during acceptance is recorded as an explicit outcome; it is
  never replaced by a recorded run presented as live.
- The runbook is re-runnable on a fresh instance and produces the same verdict for the
  same commits.
- No credential, real customer document or provider payload enters the checkpoint
  evidence; the fixture is the synthetic AR PDF only.

## Rollback / feature flag

Evidence only. Revert the acceptance commit to withdraw the PC-01 claim; product code and
server state are unaffected.

## Estimate

Effort P50 1.0 person-day, P80 2.0 person-days. Basis: executing the nineteen-step runbook and recording its evidence. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- certified commits, locks and digests
- runbook results with measured figures and the method that produced them
- the defect register with gate classification
- the single next-investment question handed to P04
