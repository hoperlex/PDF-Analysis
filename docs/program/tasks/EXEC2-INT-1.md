# Task EXEC2-INT-1 — integrate and publish stage 1 to origin/dev

## Outcome
`integration/exec2` holds SEAL-1, CAP-01, PULL-01, ENROLL-01, AGENT-01 and WEB-CAP-01. The integrator has reviewed the claim and per-token lock diff read-only. `CURRENT_STATE` records the stage as an unverified development candidate, and the exact tip is on `origin/dev`.

## Depends on
- EXEC2-SEAL-1
- EXEC2-CAP-01
- EXEC2-PULL-01
- EXEC2-ENROLL-01
- EXEC2-AGENT-01
- EXEC2-WEB-CAP-01

## Frozen inputs
- domain contract: unchanged
- API contract: 1.15.0, frozen by `EXEC2-SEAL-1`
- analysis/comparison/event contract: unchanged
- migration head: `0046`, created by `EXEC2-SEAL-1`; this task adds no migration
- base commit: `integration/exec2`
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 1–9, 18–20; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: none

The integrator re-runs every premise command on the actual base before dispatch (`EXEC2-PLAN.md` section 6) and corrects line numbers; a premise that no longer holds stops the dispatch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `docs/program/CURRENT_STATE.md`
- `docs/program/EXEC2-INT-1.md`

## Forbidden hotspots
- any code change beyond conflict resolution; a defect goes back to its lane

## Non-goals
- no `origin/main`
- no test run (`R-149d`)

## Deliverables
- Merges in dependency order. `git diff --name-only` per lane checked against its allowed paths.
- A read-only review of `jobs/repository.py`, `comparison/spend/*` and `executors/runner*.py` for lock order, count-under-lock and per-token atomicity, recorded in `EXEC2-INT-1.md`.
- `CURRENT_STATE` entry. Push to `origin/dev` with a read-back of the exact SHA.

## Required tests
- command: `git diff --check origin/dev...integration/exec2`
- expected: `git diff --check`; the per-lane path check

## Integration contract
- stage-2 lanes start from the published tip

## Failure/idempotency/security cases
- a lane outside its allowed paths: its out-of-bounds hunks are dropped and returned to the lane

## Rollback / feature flag
Revert the integration merge on `origin/dev`. Migration 0046 downgrade guarded.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
