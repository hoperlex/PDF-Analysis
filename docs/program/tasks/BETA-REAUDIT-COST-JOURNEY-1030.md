# BETA-REAUDIT-COST-JOURNEY-1030 — existing queue step compatibility

## Outcome
The existing queue re-audit step approves the freshly loaded finite cost cap through its real checkbox and verifies source Run/version, digest/cap and the later repeat request. No new journey scenario/scope or acceptance claim.

## Depends on
- BETA-REAUDIT-COST-WEB-1030
- BETA-COST-JOURNEY-1030

## Frozen inputs
UI639f9d09; generated6ea9459f; owner/root exact followup grant2026-10-30 for the existing queue step/driver fresh-source consent assertions. Current scopes remain run/ar_v3_group; no browser/model/heavy window.

## Allowed paths
- `tests/e2e/pc01/journey/manifest.json` (existing queue re-audit step)
- `tests/e2e/pc01/journey/write.mjs` (existing cost action with source Run binding)
- `tests/e2e/pc01/journey/README.md`
- `tests/e2e/test_pc01_journey_conformance.py` (closed optional source field and focused negative assertions)
- This task and `docs/program/BETA-REAUDIT-COST-JOURNEY-1030.md`

## Forbidden hotspots / non-goals
No product source/contracts/generated/migrations/locks/composition/styles, unrelated journeys, additional scopes/audit, browser/live model/gate or remote refs.

## Deliverables/checks
Exact existing-step approval and source-bound receipts; Node syntax and short manifest/pure conformance; report. Existing pending steps and unrelated checks remain intact.

## Integration contract
Auto-estimate is observed, not fabricated. The driver requires the selected source Run's actual successful read, matching estimate body/version, no executor/preset/raised override, unchecked-to-checked UI agreement and a matching keyed consent-only repeat body.

## Rollback
Coordinate with the repeat consent UI/backend policy. No product behavior change in this commit.

## Handoff
status: completed (source compatibility; browser execution UNVERIFIED). Report: `docs/program/BETA-REAUDIT-COST-JOURNEY-1030.md`. Local commit only, root sole integrator.
