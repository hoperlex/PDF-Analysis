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
- `src/auditmanager/bootstrap/adapters.py`

## Deliverables

Code, cost/public integration, current-state/beta addendum and exact dev receipt. Root owns all integration policy and named preflight composition slot.
