# CMP-STAGE-MAP-PREREQ-1030 — explain stage map prerequisite

## Outcome
A newly confirmed П→Р pair without a saved sheet map shows the required expert action, then becomes launchable immediately after the map is saved.

## Depends on
- CMP-ZIP-TRANSPORT-1030 (complete)

## Frozen inputs
- domain/comparison contract: ADR-0025, unchanged
- API contract: 1.14.0, unchanged
- migration head: `0043_stage_ai_generations`, unchanged
- base commit: `486ef4861c42d940130eec5435348fd185f292b4`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- `StageSheetMapService.current()` returns 404 when the pair is confirmed but has no saved revision. The map screen already treats this as an empty map; single and batch run controls showed it as a generic missing object. Both reported failures are consistent with this prerequisite; no production logs were inspected.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev (owner's hotfix/dev instruction)
- origin_main_authority: none

## Allowed paths
- `web/src/widgets/stage-run-controls/model/runs.ts`
- `web/src/widgets/stage-run-controls/ui/stage-run-controls.tsx`
- `web/src/widgets/stage-run-controls/ui/stage-batch-controls.tsx`
- `web/tests/unit/stage-run-controls/runs.test.ts`
- `fixtures/manual-comparison-1030/README.md`
- `fixtures/manual-comparison-1030/comparison-manual-pack.zip`
- `docs/program/tasks/CMP-STAGE-MAP-PREREQ-1030.md`

## Forbidden hotspots
- `contracts/**`, migrations, root dependencies/lockfiles, composition root, global styles, generated client, `origin/main`.

## Non-goals
- No automatic expert map decision, backend/contract change, live model call, full gate or main deployment.

## Deliverables
- Actionable prerequisite in single/batch controls; shared current-map cache key; concise fixture guide correction.

## Required tests
- Focused stage-run-control test, web typecheck and production build; fixture ZIP/README identity and CRC; staged diff check.

## Integration contract
- A confirmed pair without a map cannot launch. Saving the map on tab 2 updates the current-map cache used by the run controls; a new batch preparation reads the saved revision.

## Failure/idempotency/security cases
- Only the expected 404 on the current-map read becomes the prerequisite state; other errors retain their original handling. No map is generated or saved without expert action.

## Rollback / feature flag
- Revert this UI change and guide correction; no new flag or data migration.

## Handoff
- Final checks and published SHA are reported by the integrator. Main remains untouched.
