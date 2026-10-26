# AR-V3-BETA-RUN-PROFILE-READ-01 — in-flight v3 Run has no legacy placeholders

Task: `docs/program/tasks/AR-V3-BETA-RUN-PROFILE-READ-01.md`; base `6650f1eeb8fbf2c18ac33a6e3973646215e6e6c4`.

## Result

The generic Run page selects the v3 presentation by the exact saved `analysis_profile_id` before any stage result exists. It shows «Сведения об этапах пока не поступили» for an empty v3 stage list, while legacy and unknown profiles keep the PC-01 placeholder behavior. A reported v3 citation stage still renders in Russian. A citation stage under a missing or different profile fails the RunStatus vocabulary check. The frontend constant is tested against the existing analysis-stage contract JSON, so a changed profile seal reddens the test.

## Changed files

- `web/src/entities/audit-run/model/run-presentation.ts`, `index.ts`: profile pin, early v3 recognition and mismatch refusal.
- `web/src/entities/audit-run/ui/stage-table.tsx`: explicit empty stage reading.
- `web/tests/unit/run/stage-rows.test.ts`, `web/tests/unit/screens/run-progress.test.ts`: contract pin, queued v3, mismatch and rendered screen coverage.
- `docs/program/CURRENT_STATE.md`, the task and this result note.

## Checks

- `npm --prefix web run typecheck`: **pass**.
- Stage row, Run progress and stage-vocabulary suites: **99 passed**.
- Rendered-language guard and closed-vocabulary badge suite: **33 passed**.
- `npm --prefix web run lint -- --quiet`: **pass**.
- `tests/contract/api_v1/test_doc_prose_facts.py`: **44 passed**.
- `git diff --check` and task handoff: **pass** on the exact committed diff.
- Frontend packages were read via a temporary ignored symlink to the byte-matching gate installation; the symlink was removed after testing. No install or lockfile change.

## Contracts, risks and integration

No contract, migration, generated file, provider or pack changed. The UI copies only the exact immutable v3 profile ID from `contracts/analysis/ar_v3_beta/v1/stage.json`, with a test pin. A future profile ID revision must update this presentation and test together; it will fail visibly rather than silently reverting to the legacy schedule. Unknown profiles retain existing behavior, because their stage schedule cannot be inferred from this v3 seal.

Only the task's allowed paths changed; forbidden hotspots were untouched. Integrate the exact checked tree into `origin/dev`. Full `make gate`, approved six-map/six-set pack and live stand acceptance remain open under `R-135`; `origin/main` is not a target.
