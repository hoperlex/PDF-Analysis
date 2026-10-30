# BETA-COST-WEB-1030 — estimate and finite approval before analysis start

## Outcome
Both ordinary section Runs and six-check AR v3 groups read an actual source-bound cost estimate before start. The expert sees metered/unmetered and recorded mode, chooses a sufficient finite USD cap, explicitly approves it, and sends the same options plus digest-bound consent. Changed options or a failed estimate cannot start work under an older approval.

## Depends on
- CMP-INT-HOTFIX-RECONCILE-1030
- HOTFIX-SECTION-LIMITS-WEB-20261030
- BETA-UNIT-ALIASES-1030

## Frozen inputs
- Assigned base `0ed4f009`, current integrated API1.13/migration0043.
- Owner2026-10-30: estimate before start plus explicit sufficient cap; raised 64k-token option remains separate from cost approval.
- Serial backend/API provider BETA-COST-PREFLIGHT-1030 owns generated `estimateRunCost`, `estimateArV3GroupCost`, `RunCostEstimate`, optional start `cost_consent`; this consumer owns no shared API changes. Provider is coordinated in parallel, not an unfinished task dependency.
- Generated provider consumed via root-owned merge `b2ef672e` of exact SHA `7fcbeb37acf197f052b0ae0bf670307cfa68b143`.
- Existing immutable command/key/preset/executor semantics and caller-owned AR v3 mutation observer survive.
- Full gates/heavy windows/live calls deferred; focused UI tests only.

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: web/tests/guards/dashboard-invalidation.guard.test.ts
- enumerator_owner: BETA-COST-WEB-1030 (two additive preflight POST-read hooks only)
- totality_query: existing guard discovers every feature useMutation hook and matches the closed inventory; both preflights map false because they create no dashboard count/spend.

## Allowed paths
- `web/src/features/start-run/**`
- `web/src/features/start-ar-v3-group/**`
- `web/src/shared/ui/cost-approval/**` and additive export in `web/src/shared/ui/index.ts`
- Relevant tests under `web/tests/unit/start-run/**`, `web/tests/unit/analysis-settings/**`, `web/tests/unit/cost-approval/**`, and existing directly affected guard assertions if their behavior changed
- `web/tests/guards/dashboard-invalidation.guard.test.ts` (additive two-hook classification only)
- `docs/program/tasks/BETA-COST-WEB-1030.md`
- `docs/program/BETA-COST-WEB-1030.md`
- Ignored dependency symlink `web/node_modules`

## Shared UI duplicate proof
Both starts require the identical USD micro-unit amount display, sufficient finite-cap input, explicit checkbox, unmetered explanation, and recorded-mode caption. A new pure `CostApproval` view renders those values/events only: no API calls, Run/AR identities, pricing, routing or start policy. Feature hooks retain estimate requests and command scope. Sharing this one presentation avoids two monetary parsing/approval forms with divergent semantics.

## Forbidden hotspots
Shared API/contracts/generated files, bootstrap/composition, migrations, root dependencies/locks, global styles and remote refs/deploy.

## Non-goals
No provider mode selector, live model call, pricing calculation in React, bypass for missing/old estimate endpoint, alteration of the raised-limit output policy, or gate/browser window.

## Deliverables
Two connected preflight/approval controls, consent-bearing keyed requests, focused stale/failure/cap tests and report.

## Verification
Focused Vitest suites; typecheck after generated provider integration; scoped eslint and whitespace. No build/full battery.

## Integration contract
Use generated endpoint methods without local transport copies. Estimate body and start body use the same version/executor-or-preset/raised-limit options. Approval includes digest and finite micro-USD cap in command signature; retry retains key. New estimate/options/cap clears agreement. The parent-held AR v3 intent retains accepted command identity across control remounts.

## Failure/idempotency/security cases
Failed/malformed/stale read exposes an error and no confirmation. Below-estimate, nonfinite, negative and overly precise caps refuse submission. Unknown/legacy endpoint errors are visible; no silent start. Pending starts lock parameter and consent edits.

## Rollback
Revert UI changes only in coordination with backend consent policy. Existing accepted Runs/keys remain immutable. No feature flag added.

## Handoff
- status: completed (UI code and focused checks)
- changed files/checks/limitations: `docs/program/BETA-COST-WEB-1030.md`
- publication: local commit only; root sole integrator
