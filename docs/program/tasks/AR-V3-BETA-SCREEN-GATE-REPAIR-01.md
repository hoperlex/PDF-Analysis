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

- premise: the generated RunStatus types admit ArV3BetaStageId while the run UI model is typed to StageId only, and RequestOptions.signal is an exact optional while the new widget passes AbortSignal | undefined

### P-01 — compiler and guard

- captured_at: 2026-10-26
- command: `git grep -n -E 'ArV3BetaStageId' 573dbdce4ca728e7ff930ccd7f9eeecd5595c61c -- web/src/shared/api/generated/types.gen.ts; git grep -n -E 'readonly signal\?|exactOptionalPropertyTypes|\{ signal \}' 573dbdce4ca728e7ff930ccd7f9eeecd5595c61c -- web/src/shared/api/transport.ts web/tsconfig.json web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx; git grep -n -E 'StageId' 573dbdce4ca728e7ff930ccd7f9eeecd5595c61c -- web/src/entities/audit-run/model/run-presentation.ts`
- captured_output:
  ```text
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/shared/api/generated/types.gen.ts:40:  'ArV3BetaStageId',
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/shared/api/generated/types.gen.ts:469:/** ArV3BetaStageId - the closed value set above. */
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/shared/api/generated/types.gen.ts:470:export type ArV3BetaStageId = (typeof AR_V3_BETA_STAGE_ID_VALUES)[number];
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/shared/api/generated/types.gen.ts:2593:  degradation_set?: Array<(StageId | ArV3BetaStageId)>;
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/shared/api/generated/types.gen.ts:3114:  stage_id: StageId | ArV3BetaStageId;
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/shared/api/transport.ts:61:  readonly signal?: AbortSignal;
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:19:    queryFn: async ({ signal }: { signal?: AbortSignal }): Promise<ArV3BetaGroupReview> =>
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/widgets/ar-v3-beta-review/ui/ar-v3-beta-review.tsx:20:      (await getArV3BetaGroupReview({ path: { group_id: groupId } }, { signal })).data,
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/tsconfig.json:18:    "exactOptionalPropertyTypes": true,
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/entities/audit-run/model/run-presentation.ts:21:import type { CostBasis, ProviderMode, RunState, RunStatus, StageId, StageStatus } from '@/shared/api';
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/entities/audit-run/model/run-presentation.ts:165:  | { readonly kind: 'partial'; readonly degradation: readonly StageId[] }
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/entities/audit-run/model/run-presentation.ts:209: * The contract's `StageId` enum declares nine; PC-01 schedules the first four. The other
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/entities/audit-run/model/run-presentation.ts:218:] as const satisfies readonly StageId[];
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/entities/audit-run/model/run-presentation.ts:246:export const STAGE_DEPENDS_ON: Readonly<Record<StageId, readonly StageId[]>> = {
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/entities/audit-run/model/run-presentation.ts:259:  readonly stageId: StageId;
  573dbdce4ca728e7ff930ccd7f9eeecd5595c61c:web/src/entities/audit-run/model/run-presentation.ts:278:  readonly dependsOn: readonly StageId[];
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 573dbdce4ca728e7ff930ccd7f9eeecd5595c61c with git grep against that tree (not at dispatch time). SCOPE: only the static causes are re-captured. The typecheck exit status 2 and the rendered-language result 101 passed / 1 failed (and the four unrendered strings) were NOT re-run in this lane (no web toolchain here) and remain only the dispatch-time measurements in Frozen inputs. At the base, generated types.gen.ts defines ArV3BetaStageId (470) and widens degradation_set to Array<(StageId | ArV3BetaStageId)> (2593) and stage_id to StageId | ArV3BetaStageId (3114); entities/audit-run/model/run-presentation.ts imports and types with StageId alone (21, 165, 218, 246, 259, 278); transport.ts:61 declares signal?: AbortSignal under exactOptionalPropertyTypes: true (web/tsconfig.json:18), and ar-v3-beta-review.tsx:19-20 destructures signal as optional and passes { signal } to getArV3BetaGroupReview. These are the type-level conditions the measured typecheck failure is attributed to; the output does not itself prove the compiler errors. Dispatch-time record (2026-10-23, quoted from the original section, not re-run): command `npm --prefix web run typecheck` and `npm --prefix web test -- --run tests/unit/analysis-settings/analysis-settings.test.ts tests/unit/sections/classification-panel.test.ts tests/unit/sections/classification-correction.test.ts tests/guards/rendered-language.guard.test.ts`; captured_output was a prose summary: typecheck exits 2 on v3 stage union and optional signal; rendered suite 101 passed, 1 failed and names the four group-review branch labels. Original interpretation: these are consumer/guard gaps after the v3 API and screen seals, not contract or provider failures.

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
