# Task P2-INT-02 — P02 handoff record and navigation regeneration

> **Status: specified; not dispatchable.** Planned as the final P02 task, after an
> accepted `P2-QA-01`.

## Outcome

One concise P02 handoff record names the exact accepted commits, the migration head and the
known limits, and the regenerated navigation index resolves every P02 seam to a file that
exists, so P03 starts from a described tree rather than an inferred one.

## Depends on

- none complete at plan time

Planned predecessors and dispatch conditions — this task is not dispatchable until it is
accepted and integrated:

  - `P2-QA-01` — the independent P02 verification suite

## Frozen inputs

- every accepted P02 module and test commit
- `docs/program/P02_LOCK.json` and the P02 migration head, read only
- the navigation schema and tooling from `P1-NAV-01`, read only
- base commit: the accepted `P2-QA-01` integration commit

## Allowed paths

- `docs/program/P02_HANDOFF.md`
- `docs/navigation/INDEX.md` — regeneration only, as the integration owner of this batch
- `docs/navigation/incidents/p2-int-02.jsonl` — created only if this task actually records an
  incident; never a shared append target
- `docs/program/tasks/P2-INT-02.md` status/handoff
- status banners of `docs/program/tasks/P2-*.md`

## Forbidden hotspots

- every `src/auditmanager/**` path, `db/migrations/**`, `tests/**`, root locks and the
  `Makefile`
- `docs/navigation/entries/**`, each owned by the task that created it
- `contracts/**`, `fixtures/**`, CP-00 evidence, Git tags and remote refs

## Non-goals

- No provider repair, no product implementation, no tag and no publication.
- No PC-01 claim: the working prototype is claimed only by `P3-INT-01`.
- No approval of P03.

## Deliverables

- the P02 handoff record: accepted commits per module, the migration head, the pinned
  dependencies with licences, the environment names, the commands that were run and their
  results, and the known limits carried into P03
- the explicit conformance-scope statement: PC-01 publishes `StageResult` objects against
  the frozen schema and publishes no `JobPackage` and no `ResultPackage`, so it claims no
  conformance to those two schemas
- the regenerated `docs/navigation/INDEX.md` built from the fragments the P02 tasks own
- the navigation incident summary for the P02 wave, computed with the same status-aware
  rule every aggregator uses: **zero is a legitimate result** when every P02 task returned
  `recorded` or `none_observed` and the recorded set is complete — an empty incident
  directory plus a full set of reporting statuses means the wave genuinely hit no friction.
  If any P02 task returned `practice_not_exercised`, or gave no status at all, the
  measurement is **absent** rather than zero, and the summary names the tasks that did not
  report. An empty directory on its own is never evidence either way

## Required tests

- Command: `make foundation`
  Expected: exit `0` on the convergence commit.
- Command: `.venv/bootstrap/bin/python tools/navigation/validate_navigation.py`
  Expected: exit `0`; every P02 fragment validates and no `implemented` entry names a path
  that does not exist.
- Command: `.venv/bootstrap/bin/python tools/navigation/generate_index.py --check`
  Expected: exit `0`; the committed index matches a fresh generation.
- Command: `.venv/bootstrap/bin/python scripts/validate_bootstrap.py`
  Expected: exit `0`, standalone `PASS`.
- Command: `git diff --check`
  Expected: exit `0`.

## Integration contract

P03 may begin from this record: the API contract is frozen, the composition root starts the
application, and every P02 seam resolves through the navigation index. No P03 task needs to
read a P02 module's internals to find its seam.

## Failure/idempotency/security cases

- A claim that does not resolve to an existing file or commit blocks the record.
- Regenerating the index twice changes no tracked file.
- The record contains no credential, provider payload or customer document.

## Rollback / feature flag

Documentation only. Revert the record commit; the P02 modules stand under their own
acceptances.

## Estimate

Effort P50 0.5 person-day, P80 1.0 person-day. Basis: a handoff record and one regeneration. Calibration pending.

## Handoff

- navigation incident status, one of `recorded`, `none_observed` or
  `practice_not_exercised`; `recorded` requires the incident file above, and the other
  two assert that no incident occurred or that the practice was not followed
- the accepted commit per module and the migration head
- commands and results
- known limits and the conformance-scope statement handed to P03
