# AR-V3-BETA-SCREEN-GATE-REPAIR-01 — compile and cover the v3 beta read screen

Task: `docs/program/tasks/AR-V3-BETA-SCREEN-GATE-REPAIR-01.md`; base `573dbdce4ca728e7ff930ccd7f9eeecd5595c61c`.

## Result

The frontend typechecks against shared contract `1.4.0`. A `RunStatus` may carry the separate `ar_v3_citation_review` stage in its status and degradation set. The generic stage table labels that reported stage in Russian and does not fabricate legacy PC-01 rows beside it. The stage comparison reads the reported row's own dependency witness. The group-review query now omits an undefined abort signal. The rendered-language matrix reaches pending, invalid ID, refused read and inconsistent answer; reaching the invalid-ID branch exposed an English machine prefix in screen prose, which was removed.

## Changed files

- `web/src/entities/audit-run/model/run-presentation.ts`, `run-comparison.ts`: v3 stage union and truthful reported-row handling.
- `web/src/entities/audit-run/ui/stage-table.tsx`, `web/src/shared/ui/stage-label.ts`, `index.ts`, `web/src/widgets/run-progress/ui/run-progress.tsx`, `web/src/widgets/stage-comparison/ui/stage-comparison.tsx`: Russian v3 stage label, closed vocabulary and comparison rendering.
- `web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx`: exact optional signal and Russian invalid-ID instruction.
- `web/tests/guards/rendered-language.guard.test.ts`: four real v3 widget states, no coverage waiver.
- `web/tests/unit/run/stage-rows.test.ts`, `run-comparison.test.ts`, `web/tests/unit/analysis-settings/ar-v3-beta-review.test.ts`: reported v3 stage and invalid-ID evidence.
- `docs/program/CURRENT_STATE.md`, the task and this result note.

## Checks

- `npm --prefix web run typecheck`: **pass**.
- Focused five suites (`stage-rows`, `run-comparison`, `ar-v3-beta-review`, rendered-language guard, stage-vocabulary guard): **64 passed**.
- Adjacent `run-progress`, `stage-comparison`, closed-vocabulary suites: **108 passed**.
- `npm --prefix web run lint -- --quiet`: **pass**.
- `npm --prefix web run api:verify`: **pass**, 103 operations, OpenAPI SHA `ccc9956d19de3a4989ba4bab077ca957be30bc104a24eca3f74c4d1aa85660c1`.
- `git diff --check`: **pass**; handoff records the exact committed diff.
- Temporary ignored frontend dependencies came from a byte-matching gate worktree and were removed after testing. No install or lockfile change.

## Contracts, risks and integration

No API/domain/analysis contract, migration, generated client, pack or provider code changed. The nine legacy stage IDs and dependency map remain unchanged. The `ar_v3_citation_review` stage is accepted only as the contract's separate v3 member; unknown values still fail closed. The generic Run page cannot identify an in-flight v3 Run before its v3 stage appears and may show legacy placeholder rows then; the six-Run group review does not use those placeholders. A later profile-aware RunStatus read/presentation contract should close this before beta acceptance.

Only the task's allowed paths changed. Forbidden hotspots were untouched. Integrate the checked exact tree into `origin/dev`; `origin/main` stays unchanged. Full `make gate` and live PostgreSQL/Blob/provider acceptance remain deferred under `R-135` and the approved-pack/stand gates.
