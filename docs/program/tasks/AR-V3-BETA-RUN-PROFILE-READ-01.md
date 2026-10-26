# Task AR-V3-BETA-RUN-PROFILE-READ-01 — show an in-flight v3 Run without legacy stage placeholders

task_id: AR-V3-BETA-RUN-PROFILE-READ-01

## Outcome

The generic Run page identifies a pinned AR v3 beta profile before its CITE stage is reported and shows an honest empty stage reading, never the four PC-01 placeholders. The rendered CITE stage still appears when reported.

## Depends on

- `AR-V3-BETA-CITE-STAGE-CONTRACT-01`
- `AR-V3-BETA-SCREEN-GATE-REPAIR-01`

## Frozen inputs

- base commit: `6650f1eeb8fbf2c18ac33a6e3973646215e6e6c4`
- shared contract `1.4.0`; API 91/103/298, migration head `0032_ar_v3_run_group`; unchanged
- `contracts/analysis/ar_v3_beta/v1/stage.json` declares profile `ap_01M5M28ZCDD8VPSP1BTAEW92YE` and one profile-specific stage; `RunStatus.analysis_profile_id` is served when set.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the Run page keys its PC-01 placeholder rows on a reported v3 CITE stage, not on the Run's pinned profile

### P-01 — current placeholder rule

- captured_at: 2026-10-26
- command: `git grep -n -E 'reportsV3|PC01_STAGE_IDS.forEach|analysis_profile_id' 6650f1eeb8fbf2c18ac33a6e3973646215e6e6c4 -- web/src/entities/audit-run/model/run-presentation.ts contracts/analysis/ar_v3_beta/v1/stage.json`
- captured_output:
  ```text
  6650f1eeb8fbf2c18ac33a6e3973646215e6e6c4:contracts/analysis/ar_v3_beta/v1/stage.json:5:  "analysis_profile_id": "ap_01M5M28ZCDD8VPSP1BTAEW92YE",
  6650f1eeb8fbf2c18ac33a6e3973646215e6e6c4:web/src/entities/audit-run/model/run-presentation.ts:296:  const reportsV3 = status.stages.some((stage) => stage.stage_id === 'ar_v3_citation_review');
  6650f1eeb8fbf2c18ac33a6e3973646215e6e6c4:web/src/entities/audit-run/model/run-presentation.ts:297:  if (!reportsV3) PC01_STAGE_IDS.forEach((stageId, index) => {
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 6650f1eeb8fbf2c18ac33a6e3973646215e6e6c4 with git grep against that tree (not at dispatch time). At the base, run-presentation.ts:296 computes reportsV3 from the status stages containing 'ar_v3_citation_review' and :297 runs PC01_STAGE_IDS.forEach (the PC-01 placeholder rows) only when reportsV3 is false. The file has no analysis_profile_id reference (the only analysis_profile_id hit is contracts/analysis/ar_v3_beta/v1/stage.json:5, which declares ap_01M5M28ZCDD8VPSP1BTAEW92YE), so a queued v3 Run with no stage row falls into the placeholder branch. Not shown: that exactly four rows are produced (the task states the first four PC-01 stages). Dispatch-time record (2026-10-23, quoted from the original section, not re-run): command `rg -n 'reportsV3|PC01_STAGE_IDS.forEach|analysis_profile_id' web/src/entities/audit-run/model/run-presentation.ts contracts/analysis/ar_v3_beta/v1/stage.json`; captured_output was a prose summary: `stageRows` suppresses PC-01 rows only after a reported v3 CITE stage; the frozen contract declares an earlier stable v3 profile ID. Original interpretation: a queued v3 Run with no stage row receives four false legacy placeholders.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/src/entities/audit-run/model/run-presentation.ts`
- `web/src/entities/audit-run/index.ts`
- `web/src/entities/audit-run/ui/stage-table.tsx`
- `web/tests/unit/run/stage-rows.test.ts`
- `web/tests/unit/screens/run-progress.test.ts`
- `web/node_modules`
- `docs/program/tasks/AR-V3-BETA-RUN-PROFILE-READ-01.md`
- `docs/program/AR-V3-BETA-RUN-PROFILE-READ-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- `contracts/**`, migrations, root dependencies/locks, generated API, composition root, global styles, provider and pack data
- `origin/main`, tag and deployment host

## Non-goals

- No change to the nine legacy stage IDs, `RunStatus` wire schema or v3 executor.
- No new expert or normative decision.

## Deliverables

- Profile-aware stage row projection and explicit empty reading.
- A pin test against the existing analysis-stage contract and a rendered in-flight Run case.
- Result note and handoff.

## Required tests

- `npm --prefix web run typecheck`
- `npm --prefix web test -- --run tests/unit/run/stage-rows.test.ts tests/unit/screens/run-progress.test.ts tests/guards/stage-vocabulary.guard.test.ts`
- `npm --prefix web run lint -- --quiet`
- `git diff --check`; `scripts/task_handoff.py`
- The ignored `web/node_modules` may temporarily link to the byte-matching gate installation and must be removed after checks. Full `make gate` remains final-candidate work under `R-135`.

## Integration contract

Only the exact frozen v3 profile ID selects the v3 stage presentation. A legacy or unknown profile retains existing PC-01 scheduling behavior. A reported v3 stage with a contradictory profile refuses the vocabulary read. Empty v3 stage lists say no stage has been reported; they do not claim the first four legacy stages are pending.

## Failure/idempotency/security cases

- An unrecognized profile never gains v3 behavior through substring/prefix matching.
- A mismatched v3 stage/profile pair fails closed.
- Read-only projection; no side effect.

## Rollback / feature flag

Revert the UI slice; no flag or migration.

## Handoff

- changed files: result note
- checks/results: result note
- known limits: v3 pack/stand acceptance remains open
- integration notes: publish only exact checked tree to `origin/dev`
