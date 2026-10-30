# BETA-REAUDIT-COST-WEB-1030 — fresh cost consent for repeated Runs

## Outcome
The queue's terminal-Run re-audit confirmation reads a fresh source-bound cost estimate and requires new finite-cap approval. It never reuses the original paid consent. Unknown-outcome retries retain the exact new key/body; failed or stale estimates cannot start another paid Run. Cancel/priority/pause behavior stays unchanged.

## Depends on
- BETA-COST-WEB-1030
- BETA-COST-JOURNEY-1030
- CMP-INT-HOTFIX-RECONCILE-1030

## Frozen inputs
- Current lane43db4802; root/API owner supplies the additive re-audit provider in parallel.
- Exact generated provider6ea9459f was consumed through root mergeb925e83c.
- Root's final seam2026-10-30: existing POST `/runs/cost-estimate` / estimateRunCost gains `reaudit_of_run_id`; `version_uid` is read once through generated getRunStatus for the selected source Run. Backend restores source executor/current route semantics, not the client.
- POST `/runs/{run_id}/reaudit` gains optional ReauditRunRequest.cost_consent; new served repeats require fresh approval. No preset or raised-limit override; old accepted command replay remains backend-owned.
- Metered cap minimum max(1,estimated), unmetered0 permitted. Root grants the three existing start/UI minimum fixes and their focused test as an actual integration correction.
- No browser, live call, full build/gate or expanded audit.

## Enumerator ownership
- enumerated_set_changed: no (preflight uses a scoped query, not a new mutation command)
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: existing terminal-only queue command plus focused actual-dialog tests.

## Allowed paths
- `web/src/features/reaudit-run/**`
- `web/src/_pages/queue/**`
- `web/src/features/start-run/model/use-run-cost-approval.ts` and `web/src/features/start-ar-v3-group/model/use-ar-v3-cost-approval.ts` (metered minimum only)
- `web/src/shared/ui/cost-approval/cost-approval.tsx` (metered minimum only)
- Related `web/tests/unit/execution/**`, `web/tests/unit/cost-approval/**`, relevant queue assertions and directly affected guard inventories if needed
- This task and `docs/program/BETA-REAUDIT-COST-WEB-1030.md`

## Forbidden hotspots
Contracts/generated/shared API, bootstrap/composition, migrations, dependencies/locks, global styles, unrelated source/journey and remote refs/deploy.

## Non-goals
No guessed version, executor, preset, profile or reuse of original consent; no change to terminal eligibility or unrelated queue commands; no new journey scope.

## Deliverables/checks
Connected fresh preflight/approval dialog and consent-bearing repeat command; focused unit/live-dialog tests, typecheck/scoped lint and report. Heavy acceptance is deferred.

## Integration contract
Consume exact generated provider. Source GET and estimate are bound to the selected Run/version; another selection, cancellation, failed read or stale conflict cannot inherit approval. Cap changes require fresh agreement and command identity; unchanged unknown-outcome retry keeps its key/body. Backend remains authoritative for source routing and money enforcement.

## Rollback
Coordinate with backend consent policy. Preserve accepted commands/old Runs; reverting UI alone cannot restore an unapproved served repeat.

## Handoff
- status: completed (UI and focused checks)
- report: `docs/program/BETA-REAUDIT-COST-WEB-1030.md`
- publication: local only; root sole integrator
