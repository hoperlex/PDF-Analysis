# Task AR-V3-BETA-SCREEN-GATE-REPAIR-01 — compile and cover the v3 beta read screen

task_id: AR-V3-BETA-SCREEN-GATE-REPAIR-01

## Outcome

The development frontend compiles against the `1.4.0` RunStatus union and the rendered-language guard reaches the new group-review pending, invalid-ID, refused-read and inconsistent-answer branches.

## Depends on

- `AR-V3-BETA-RUN-STAGE-SEAL-01`
- `AR-V3-BETA-GROUP-REVIEW-SCREEN-01`
- `BETA-PB-PROFILE-TRUTH-01`

## Frozen inputs

- base commit: `573dbdce4ca728e7ff930ccd7f9eeecd5595c61c`
- shared contract `1.4.0`, API 91/103/298, migration head `0032_ar_v3_run_group`; unchanged
- measured TypeScript errors: `RunStatus.degradation_set`/`StageState.stage_id` now include `ArV3BetaStageId`, while the legacy UI model assumes only `StageId`; `RequestOptions.signal` is exact-optional, but the new widget passes `AbortSignal | undefined`.
- measured guard failure: four strings in `ar-v3-beta-review.tsx` are absent from the rendered matrix (101 passed, 1 failed in the focused run).

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

### P-01 — compiler and guard

- captured_at: 2026-10-23
- command: `npm --prefix web run typecheck` and `npm --prefix web test -- --run tests/unit/analysis-settings/analysis-settings.test.ts tests/unit/sections/classification-panel.test.ts tests/unit/sections/classification-correction.test.ts tests/guards/rendered-language.guard.test.ts`
- captured_output: typecheck exits 2 on v3 stage union and optional signal; rendered suite 101 passed, 1 failed and names the four group-review branch labels.
- interpretation: these are consumer/guard gaps after the v3 API and screen seals, not contract or provider failures.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/src/entities/audit-run/model/run-presentation.ts`
- `web/src/entities/audit-run/model/run-comparison.ts`
- `web/src/entities/audit-run/ui/stage-table.tsx`
- `web/src/shared/ui/stage-label.ts`
- `web/src/shared/ui/index.ts`
- `web/src/widgets/run-progress/ui/run-progress.tsx`
- `web/src/widgets/stage-comparison/ui/stage-comparison.tsx`
- `web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/tests/unit/run/stage-rows.test.ts`
- `web/tests/unit/run/run-comparison.test.ts`
- `web/tests/unit/analysis-settings/ar-v3-beta-review.test.ts`
- `web/node_modules`
- `docs/program/tasks/AR-V3-BETA-SCREEN-GATE-REPAIR-01.md`
- `docs/program/AR-V3-BETA-SCREEN-GATE-REPAIR-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- `contracts/**`, migration head, root dependency/locks, composition root, global styles, generated API, provider/pack data
- `origin/main`, tags, deployment host

## Non-goals

- No new v3 execution or expert approval.
- No change to the nine legacy stage IDs or their dependency map.
- No publication of a legal or numeric verdict.

## Deliverables

- Type-safe v3 stage presentation and exact-optional request signal.
- Four rendered group-review branch seeds in the language guard.
- Focused tests and result note.

## Required tests

- `npm --prefix web run typecheck`
- `npm --prefix web test -- --run tests/unit/run/stage-rows.test.ts tests/unit/run/run-comparison.test.ts tests/unit/analysis-settings/ar-v3-beta-review.test.ts tests/guards/rendered-language.guard.test.ts tests/guards/stage-vocabulary.guard.test.ts`
- `npm --prefix web run api:verify`
- `git diff --check`; `scripts/task_handoff.py`
- Temporary ignored `web/node_modules` symlink to a byte-matching existing installation is permitted for tests; remove it afterward. Full `make gate` remains at the final candidate (`R-135`).

## Integration contract

The legacy nine-stage map remains exact, while a v3 citation-review stage gets a Russian label and is recognized as a legal `RunStatus` member. Unknown stages still fail closed. The group-review read passes only a defined AbortSignal or omits the option. The rendered guard reaches all four new branches without waiving its branch ratchet.

## Failure/idempotency/security cases

- Unknown stage and malformed group response still show refusal; no silent fallback.
- Pending, invalid ID, API refusal and inconsistent six-scope answer each render a distinct Russian state.
- Read-only changes; no durable writes.

## Rollback / feature flag

Revert the frontend slice; no migration or flag.

## Handoff

- changed files: result note
- checks/results: result note
- known limits: full gate and live beta stand deferred
- integration notes: publish only the checked exact tree to `origin/dev`
