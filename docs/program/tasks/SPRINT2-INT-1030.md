# SPRINT2-INT-1030

task_id: SPRINT2-INT-1030

## Outcome

Integrate maximum useful section-analysis and original comparison features and publish origin/dev within the second hour.

## Frozen inputs

- Base: `5e4ef75a` (origin/dev refreshed at this window start).
- API: 1.14.0; 233 paths /259 operations /620 schemas; migration0043.
- Original read-only source: `/tmp/pdf-proverka-original`, commit3c99481719218b9cfa7560886529916646c61939.
- Completed dependency: SPRINT-SECTION-INT-1030, published78d5799e.
- Owner explicitly continues another one-hour implementation window: 14:50–15:50 Europe/Moscow, no checks; lane handback15:32, integration/publication before15:50.

## Depends on

- SPRINT-SECTION-INT-1030

## Forbidden hotspots

- Other lane owned files; contracts/**; migrations; root dependencies/locks; global styles; production services; origin/main; tests/** and fixtures/** (synthetic inputs owned by another session).
- No tests, imports/compile, lint/typecheck/build, runtime/browser/DB/model execution or checks. Static source reading and Git metadata for root integration only.

## Non-goals

No production deployment or beta/original quality claim; no automatic expert decision or rewrite of raw comparison evidence; no synthetic inputs; no new OCR service/API/migration.

## Required tests

- command: none, expressly deferred by owner for this hour.
- expected: UNVERIFIED source candidate; no PASS claim.

## Integration contract

Root is sole Git writer and publisher to origin/dev, exact clean FF/read-back. API1.14.0/migration0043 remain frozen. Old accepted v1/v2/v3 authorities keep old request/count behavior; new paid behavior requires separately frozen fresh policy metadata and sufficient explicit cost consent. Unknown paid outcomes never trigger a resend. Coordinate helper signatures before editing another lane seam.

## Rollback / feature flag

Fresh-policy behavior boundary; preserve historical receipts. Disable fresh enhanced policy or forward revert; no retroactive paid expansion. Existing switches retained.

## Handoff

Return changed files, actual work, no-check status, unchanged contracts, limitations and integration notes. Freeze by15:32Europe/Moscow; no Git writes or tags.

## Allowed paths

- `docs/program/**`
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/analysis/extended/estimate.py`
- `src/auditmanager/runs/preflight.py`
- `src/auditmanager/runs/cost_policy.py`
- `src/auditmanager/runs/extended_review.py`
- `src/auditmanager/bootstrap/adapters.py`

## Deliverables

Code, cost/public integration, current-state/beta addendum and exact dev receipt. Root owns all integration policy and named preflight composition slot.

Stage UI exact grant: the Stage lane exclusively owns web/src/widgets/stage-v3-experimental/** and web/src/widgets/stage-changes/** for reports and parameter/source navigation. Ordinary extended-review UI remains Experience ownership.

## Frozen batching seam

Fresh ordinary v3 consent defaults to `coverage_version=batched-v1`, `phase_call_limits={block_analysis:2,comprehensive_analysis:4,norm_verification:8,finding_review:8,finding_correction:8}` per window, maximum30 additional calls. Root public helpers: extended_coverage_policy(), validate_extended_coverage_policy(policy), plan_extended_coverage(**kwargs) delegate to analysis.extended.coverage. Fresh budget reserves actual phase caps and output maxima; empty phases spend zero. `AUDITMANAGER_EXTENDED_COVERAGE=legacy` keeps fresh six-call v3 allowance. Old accepted authorities never acquire batch spending. Changed implementation SHA safely refuses old queued v3 before dispatch and requires fresh consent; do not fake legacy hashes.

## Additional archive integration

New concrete feature `features/export-evidence-package` is exclusively owned by Coverage lane. Stage/Experience own only their respective download controls, collecting actual source version IDs from their existing data, reports and cancellation/progress state. Consume its public buildEvidencePackage(request) returning Blob/fileName; no private imports or duplicate fetch/ZIP implementations. Root owns Git and the named feature ownership slot. No backend/model calls or extra consent. Existing full independent downloads remain available. Handback≤12:30UTC.

Root exclusive post-freeze seam: read_extended_review projects actual version_uid from the verified artifact envelope/Run into result for source viewers and source ZIP. A conflicting existing result identity is refused. No model request/source SHA/worker behavior changes; old stored snapshots need no backfill. Coverage owner frozen on this file.
