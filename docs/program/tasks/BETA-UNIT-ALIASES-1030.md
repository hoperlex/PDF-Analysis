# BETA-UNIT-ALIASES-1030

## Outcome
Specification and price-list running metres (`п.м` and known spelling aliases) match metres (`м`) at exact factor1, including deterministic cheaper-analog proposals. Source units remain visible and immutable.

## Depends on
- CMP-INT-HOTFIX-RECONCILE-1030

## Frozen inputs
Owner direct poll2026-10-30: «Да, сопоставлять с коэффициентом1». Base8a437cbe; current API1.13/0043; existing Decimal monetary rules and same-currency/one-position requirements.

## Allowed paths
- src/auditmanager/optimisation/matching.py
- src/auditmanager/optimisation/proposals/generator.py
- src/auditmanager/optimisation/specification.py (source-unit explanation only)
- tests/unit/optimisation/**
- tests/integration/optimisation/proposals/test_passes.py
- tests/integration/optimisation/proposals/conftest.py (retain true dimension-mismatch fixture)
- docs/program/tasks/BETA-UNIT-ALIASES-1030.md
- docs/program/BETA-UNIT-ALIASES-1030.md

## Forbidden hotspots
Contracts/generated/composition (owned by BETA-COST-PREFLIGHT-1030 seal), migration, dependencies, global styles and main.

## Non-goals
No other unit conversions, guessed prices, currency conversion, model proposal generation or source-unit rewrite.

## Deliverables
Pricing unit alias, versioned matcher/generator, exact amount/total/ambiguity/proposal regressions and report.

## Verification
Focused existing matcher/proposal tests; compile/whitespace; no heavy gate.

## Integration contract
Cost-preflight serial contract owner broadens the two transport price-match literals to v1|v2. New calculations use price-match-v2/cheaper-analog-v2; old saved passes remain readable and unchanged.

## Rollback
Forward code change or disable new starts; preserve previous immutable passes and original quantities/units. Ambiguous equivalent price positions remain ambiguous rather than choosing a price.
