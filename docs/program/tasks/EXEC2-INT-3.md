# Task EXEC2-INT-3 — integrate and publish stage 3 to origin/dev with the upgrade and rollback steps

## Outcome
`integration/exec2` holds GROUP-RUN-01, GROUP-CMP-01, WEB-GROUPS-01 and CUTOVER-01. The read-only reviews of lock order, money and write-once binding are recorded. `CURRENT_STATE` and the upgrade and rollback steps for the release integrator exist. The exact tip is on `origin/dev`. Promotion to `origin/main` is the release integrator's, after `D-292`.

## Depends on
- EXEC2-INT-2
- EXEC2-GROUP-RUN-01
- EXEC2-GROUP-CMP-01
- EXEC2-WEB-GROUPS-01
- EXEC2-CUTOVER-01

## Frozen inputs
- domain contract: unchanged
- API contract: 1.16.0, frozen by `EXEC2-SEAL-2`
- analysis/comparison/event contract: unchanged
- migration head: `0048`, created by `EXEC2-SEAL-2`; this task adds no migration
- base commit: `integration/exec2`
- architecture: `docs/architecture/adr/ADR-0026-executor-capacity-enrollment-groups.md` decisions 10–20; plan `docs/program/dispatch/EXEC2-PLAN.md`; rulings `R-149a`…`R-149f`

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
- `docs/program/EXEC2-INT-3.md`

## Forbidden hotspots
- any code change beyond conflict resolution

## Non-goals
- no `origin/main`
- no cut-over on the stand (owner act)

## Deliverables
- Merges and per-lane path checks.
- Reviews:
-   - lock order across `jobs/repository.py` and `comparison/spend/*`;
-   - every `connection_revision_id` reader in premise lists of GROUP-RUN-01 and GROUP-CMP-01 handles `pending`;
-   - `environment` refusal;
-   - ceilings against the bound member.
- Upgrade and rollback steps in `EXEC2-INT-3.md` for the release integrator, who writes the Russian `release-notes/<version>.json` at the version bump; no VERSION change on dev. `CURRENT_STATE`, push with exact read-back.
- B3 §11 item 21 noted as a pending run in `D-292`.

## Required tests
- command: `git diff --check origin/dev...integration/exec2`
- expected: `git diff --check`; the per-lane path check

## Integration contract
- the release integrator promotes to `origin/main` only after the `D-292` test run

## Failure/idempotency/security cases
- as `EXEC2-INT-1`

## Rollback / feature flag
Mode `legacy` is the default after deploy. Revert the integration merge only with no `pending` work.

## Handoff
- changed files: the lane lists them; it does not run git, and the integrator commits exactly the allowed paths it changed
- commands/results: generation commands run and their result; no test, build, typecheck, lint, database, browser or model run (`R-149d`)
- known limits: every acceptance test named above is unexecuted
- integration notes: what the next consumer of this task may rely on
