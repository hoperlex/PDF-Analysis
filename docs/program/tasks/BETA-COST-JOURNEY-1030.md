# BETA-COST-JOURNEY-1030 — Run preflight compatibility

## Outcome
Existing maintained journey starts obtain an actual estimate through the UI, approve the exact recommended finite cap through the checkbox, and verify the later start carries the same frozen options/digest/cap. Missing or failed reads are failures, never bypasses. The closed action supports ordinary and AR v3 group cost scopes.

## Depends on
- BETA-COST-WEB-1030
- CMP-JOURNEY-C4-01

## Frozen inputs
- UI provider6fe0bd501349a66407e2d74b6828fac92f3898ea; generated preflight provider7fcbeb37.
- Owner/root grant: narrow journey compatibility only; no browser/heavy window today.
- Existing pending AR v1 steps remain pending; no new AR activation/acceptance is inferred.

## Enumerator ownership
- enumerated_set_changed: yes
- enumerator_path: tests/e2e/test_pc01_journey_conformance.py (closed action set)
- enumerator_owner: BETA-COST-JOURNEY-1030
- totality_query: every declared startRun/startArV3BetaGroup requires a matching bounded approval action before its start click; both scopes map to current frozen operations.

## Allowed paths
- `tests/e2e/pc01/journey/manifest.json`
- `tests/e2e/pc01/journey/write.mjs`
- `tests/e2e/pc01/journey/README.md`
- `tests/e2e/test_pc01_journey_conformance.py` (new closed action/compatibility assertions)
- This task and `docs/program/BETA-COST-JOURNEY-1030.md`

## Forbidden hotspots
Product source, contracts/generated, migrations, bootstrap/composition, dependencies/global styles, unrelated journey modules and remote refs.

## Non-goals
No browser, worker, model, build or gate execution. No activation/renaming/removal of historical pending steps, no change to comparison C4 consent, no silent estimate fallback.

## Deliverables and checks
Explicit manifest approval actions and operation declarations, bounded driver with exchange-bound consent checks, short Node syntax/Python conformance and report.

## Integration contract
The driver verifies successful source-bound estimate scope/version, recorded mode unless explicit allow-spend, the prefilled exact recommended cap, actual checkbox state, matching start options/digest/ceiling and real command key. Retries retain existing request/key behavior. Auth/scope/API failure remains a red step.

## Rollback
Revert only alongside the corresponding start UI/consent policy; preserve original and pending steps. No product behavior changes.

## Handoff
- status: completed (source compatibility; browser execution UNVERIFIED)
- checks/limits: `docs/program/BETA-COST-JOURNEY-1030.md`
- publication: local commit only; root sole integrator
