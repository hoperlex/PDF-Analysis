# BETA-COST-WEB-1030 — explicit Run cost approval

Date2026-10-30. Completed UI code on assigned base0ed4f009 plus root's generated-provider mergeb2ef672e (provider7fcbeb37acf197f052b0ae0bf670307cfa68b143). No remote ref or deployed service changed.

## Result
Ordinary section starts and six-check AR v3 starts now read their actual cost estimate, display the model, page/text volume, windows, calls, input/output token estimates and metered/unmetered status, then require an explicit finite USD ceiling and checkbox agreement. The recorded caption identifies saved test answers and does not claim actual spend. An unmetered reading permits zero but still requires agreement.

The raised-limit switch remains default off and independent: it selects the 64,000-token request, while the approved cost cap is sent separately. Estimate/start use identical version, executor-or-preset and raised-limit fields. Start carries the exact digest/cap/confirmed consent; options and consent are part of its key. Changed options clear the estimate and agreement, a cap edit clears agreement, and late readings for another version or scope cannot approve work. Retry, checkbox re-agreement and a re-read of the unchanged payload retain its key. A server stale-estimate conflict clears approval and asks for a new estimate. Missing/failed legacy endpoints show a normal error and cannot start work.

AR estimates and approval live in the caller-held intent alongside its mutation/key, so temporary removal of the control cannot discard the accepted payload's identity. Its cache subscription now schedules notifications through TanStack notifyManager, avoiding cross-component updates during a sibling observer's render; immediate version-specific snapshots remain intact.

## Changed files
- `web/src/features/start-run/model/start-run-intent.ts`: additive consent body and intent signature.
- `web/src/features/start-run/model/use-run-cost-approval.ts`: source-bound estimate and approval state.
- `web/src/features/start-run/ui/start-run-control.tsx`: estimate/approve/start and actual stale/failure handling.
- `web/src/features/start-ar-v3-group/model/use-ar-v3-cost-approval.ts`: group-scoped estimate and approval state.
- `web/src/features/start-ar-v3-group/model/use-ar-v3-group-start-intent.ts`: persistent consent/key and scheduled cache subscription.
- `web/src/features/start-ar-v3-group/model/use-start-ar-v3-group.ts`: consent-bearing request.
- `web/src/features/start-ar-v3-group/ui/start-ar-v3-group-control.tsx`: estimate/approve/start views.
- `web/src/shared/ui/cost-approval/{cost-approval.tsx,index.ts}` and additive `shared/ui/index.ts` export: pure common amount form, exact USD/micro conversion and rendering validation; semantic duplication proof is in the task.
- `web/tests/unit/cost-approval/{cost-approval.test.ts,start-cost-flow.test.ts}`: actual controls, malformed/stale reads, finite cap, same-key retry, remount, recorded/unmetered and exact body coverage.
- `web/tests/unit/analysis-settings/{cost-estimate-fixtures.ts,live-render.ts}`: explicit estimate/checkbox fixture support; disabled controls/fieldsets remain unpressable.
- Existing focused `start-run/{start-run-intent,executor-select,executor-refusal}.test.ts` and `analysis-settings/{analysis-presets,ar-v3-group-start-command,ar-v3-group-start-failure,run-list-ar-v3-live}.test.ts`: add real approval before the existing start assertions; preserve preset/executor/remount/refusal claims.
- `web/tests/guards/dashboard-invalidation.guard.test.ts`: classify the two preflight POST-read hooks as no dashboard mutation, preserving exact-set discovery.
- Task and this report.

## Verification
- Focused ten-file/slice Vitest run: **154 passed** (4.44s).
- Dashboard invalidation and review indication guards: **57 passed**.
- After scheduling the cache subscription, the 20 lifecycle and 11 new cost tests were re-run: **31 passed**, without the earlier cross-component render warning.
- `tsc --noEmit`: passed. Scoped ESLint over all changed source/tests: passed. `git diff --check`: passed.
- No browser, model call, full build or heavy gate. Actual provider billing and end-to-end preflight execution remain tomorrow's integration obligations.

## Contracts, limits and integration
This commit consumes generated operations/types and changes no API/contracts/generated files, bootstrap, migration, dependency lock or global styles. All changed paths belong to the task's feature/shared-presentation/test allowlist; generated provider bytes arrived through the root-owned merge and are outside this commit's changes.

Root integrates this provider with the backend cost service. Stable controls: ordinary «Оценить стоимость»; AR «Оценить стоимость шести проверок»; «Лимит стоимости, USD»; checkbox «Подтверждаю оценку и лимит для выбранных параметров»; fieldset `[data-cost-approval]`. Existing journey starts need the separately authorised narrow compatibility followup. Monetary calculations and authoritative ceiling enforcement remain backend-owned; the form never computes prices or dispatches a model.

Rollback only with backend consent-policy coordination; keep already accepted immutable commands/Runs. No publication or main authority is included.
