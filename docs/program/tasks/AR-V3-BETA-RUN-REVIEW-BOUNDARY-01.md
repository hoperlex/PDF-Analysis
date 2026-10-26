# Task AR-V3-BETA-RUN-REVIEW-BOUNDARY-01 — keep v3 beta review separate from canonical findings

task_id: AR-V3-BETA-RUN-REVIEW-BOUNDARY-01

## Outcome

A terminal AR v3 beta Run never offers the canonical «Разобрать находки» link or a canonical finding-count claim. It directs the reviewer to the six-Run preliminary group review; legacy Runs retain their existing review path.

## Depends on

- `AR-V3-BETA-GROUP-REVIEW-SCREEN-01`
- `AR-V3-BETA-RUN-PROFILE-READ-01`

## Frozen inputs

- base commit: `289f1eb0182029dd53d7eae3407ee85ca55f1ec0`
- shared API `1.4.0`, API 91/103/298, migration head `0032_ar_v3_run_group`; unchanged
- analysis-stage contract: profile `ap_01M5M28ZCDD8VPSP1BTAEW92YE`, `canonical_finding_publication: false`; current group review lives under `/analysis-settings?group_id=...`.

## Enumerator ownership

- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence

- premise: the canonical review link and the finding count are offered by Run state alone, without looking at the Run's profile

### P-01 — state-only canonical review link

- captured_at: 2026-10-26
- command: `git grep -n -A 3 -E 'runHasPublishedResult\(|Разобрать находки|Опубликованных находок' 289f1eb0182029dd53d7eae3407ee85ca55f1ec0 -- web/src/entities/audit-run/model/run-presentation.ts web/src/widgets/run-progress/ui/run-progress.tsx`
- captured_output:
  ```text
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/entities/audit-run/model/run-presentation.ts:165:export function runHasPublishedResult(state: RunState): boolean {
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/entities/audit-run/model/run-presentation.ts-166-  return isExportableRunState(state);
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/entities/audit-run/model/run-presentation.ts-167-}
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/entities/audit-run/model/run-presentation.ts-168-
  --
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/widgets/run-progress/ui/run-progress.tsx:127:            Опубликованных находок:{' '}
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/widgets/run-progress/ui/run-progress.tsx-128-            {outcome.findingCount === null ? <em>не сообщено</em> : outcome.findingCount}
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/widgets/run-progress/ui/run-progress.tsx-129-          </p>
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/widgets/run-progress/ui/run-progress.tsx-130-        </div>
  --
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/widgets/run-progress/ui/run-progress.tsx:375:      {runHasPublishedResult(status.state) ? (
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/widgets/run-progress/ui/run-progress.tsx-376-        <p>
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/widgets/run-progress/ui/run-progress.tsx:377:          <Link href={routes.review(projectUid, status.run_id)}>Разобрать находки</Link>{' '}
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/widgets/run-progress/ui/run-progress.tsx-378-          — режим провайдера этого прогона:{' '}
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/widgets/run-progress/ui/run-progress.tsx-379-          <strong data-provider-mode={mode}>{modeText}</strong>.
  289f1eb0182029dd53d7eae3407ee85ca55f1ec0:web/src/widgets/run-progress/ui/run-progress.tsx-380-        </p>
  ```
- interpretation: Re-captured on 2026-10-26 from base commit 289f1eb0182029dd53d7eae3407ee85ca55f1ec0 with git grep against that tree (not at dispatch time). At the base, runHasPublishedResult(state: RunState) takes only the state and returns isExportableRunState(state) (run-presentation.ts:165-167). run-progress.tsx:375 gates the link «Разобрать находки» (377) on runHasPublishedResult(status.state) alone, and :127-128 prints «Опубликованных находок» with outcome.findingCount; no profile id is read in any of these lines. Not shown: which states isExportableRunState accepts (published and partial per the doc comment at run-presentation.ts:160-164, not captured). Dispatch-time record (2026-10-23, quoted from the original section, not re-run): command `rg -n 'runHasPublishedResult\(|Разобрать находки|Опубликованных находок' web/src/entities/audit-run/model/run-presentation.ts web/src/widgets/run-progress/ui/run-progress.tsx`; captured_output was a prose summary: RunProgress offers the canonical review link for every `published`/`partial` state; the published outcome prints a finding count without checking the profile. Original interpretation: a review-only v3 Run can be presented as if it had canonical findings.

## Historical evidence

- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority

- development_target: origin/dev
- origin_main_authority: none

## Allowed paths

- `web/src/entities/audit-run/model/run-presentation.ts`
- `web/src/widgets/run-progress/ui/run-progress.tsx`
- `web/tests/unit/run/provider-mode.test.ts`
- `web/tests/unit/screens/run-progress.test.ts`
- `web/tests/guards/rendered-language.guard.test.ts`
- `web/node_modules`
- `docs/program/tasks/AR-V3-BETA-RUN-REVIEW-BOUNDARY-01.md`
- `docs/program/AR-V3-BETA-RUN-REVIEW-BOUNDARY-01.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots

- `contracts/**`, migrations, root dependencies/locks, composition root, global styles, generated API, provider/pack code
- canonical finding/decision evidence, `origin/main`, tags and deployment host

## Non-goals

- No new v3 group lookup by Run ID; RunStatus does not carry group identity.
- No change to canonical finding publication, expert decisions or run terminal policy.

## Deliverables

- Profile-aware canonical review-link gate and review-only v3 terminal text.
- Rendered positive/negative tests for v3 and legacy Runs.
- Result note and handoff.

## Required tests

- `npm --prefix web run typecheck`
- `npm --prefix web test -- --run tests/unit/run/provider-mode.test.ts tests/unit/screens/run-progress.test.ts tests/guards/rendered-language.guard.test.ts`
- `npm --prefix web run lint -- --quiet`
- `git diff --check`; `scripts/task_handoff.py`
- Temporary ignored `web/node_modules` symlink to the byte-matching gate installation is permitted for tests and removed after checks. Full `make gate` remains final-candidate work under `R-135`.

## Integration contract

Only the exact v3 profile pin suppresses the canonical review link and finding-count wording. A successful v3 Run is labelled review-only with explicit expert review required. Legacy AR and other profiles still use the canonical published/partial review link. No group ID is guessed from Run ID.

## Failure/idempotency/security cases

- Missing/unknown profile retains prior behavior; no prefix-based v3 match.
- Failed or pending v3 Runs do not imply a saved review.
- Read-only projection; no external effect.

## Rollback / feature flag

Revert the UI slice; no flag or migration.

## Handoff

- changed files: result note
- checks/results: result note
- known limits: approved pack and stand still absent
- integration notes: publish exact checked tree to `origin/dev` only
