# Task EXEC2-INT-2 — integrate and publish stage 2 to origin/dev

## Outcome
`integration/exec2` holds ENROLL-SSH-01, WEB-WIZARD-01, SEAL-2 and GROUP-STORE-01. The SSH install runner has had a read-only review. `CURRENT_STATE` records the stage as an unverified development candidate, and the exact tip is on `origin/dev`.

## Depends on
- EXEC2-INT-1
- EXEC2-ENROLL-SSH-01
- EXEC2-WEB-WIZARD-01
- EXEC2-SEAL-2
- EXEC2-GROUP-STORE-01

## Frozen inputs
- domain contract: unchanged
- API contract: 1.16.0, frozen by `EXEC2-SEAL-2`
- analysis/comparison/event contract: unchanged
- migration head: `0048`, created by `EXEC2-SEAL-2`; this task adds no migration
- base commit: `integration/exec2`
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 6–18; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

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
- `docs/program/EXEC2-INT-2.md`

## Forbidden hotspots
- any code change beyond conflict resolution

## Non-goals
- no `origin/main`
- no test run (`R-149d`)

## Deliverables
- Merges, per-lane path check, read-only review of the install runner (secret handling, host-key compare, command construction).
- `CURRENT_STATE`, push with exact read-back.
- The optional owner act of clean-Ubuntu acceptance is offered.

## Required tests
- command: `git diff --check origin/dev...integration/exec2`
- expected: `git diff --check`; the per-lane path check

## Integration contract
- stage-3 lanes start from the published tip

## Failure/idempotency/security cases
- as `EXEC2-INT-1`

## Rollback / feature flag
Revert the integration merge; 0047 and 0048 downgrades are guarded.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
