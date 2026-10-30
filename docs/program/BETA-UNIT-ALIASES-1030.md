# BETA-UNIT-ALIASES-1030

Implemented the direct owner decision2026-10-30: known running-metre spellings (`п.м`, `пог. м`, `м.п.`) share the pricing key `м` with exact factor1. Specification extraction retains original canonical source units; quantities, Decimal amounts and currencies are unchanged. Multiple equivalent price positions still produce ambiguity, never an automatic cheaper choice. Deterministic cheaper-analog proposals accept these aliases while keeping vendor/currency/price evidence requirements.

Changed files: optimisation matching/generator, source-unit explanation, existing matcher/proposal tests and the saved-pass algorithm expectation. New algorithms are `price-match-v2` and `cheaper-analog-v2`; old passes remain immutable. Cost-preflight seal owner broadens the two transport algorithm literals to accept historicalv1 and newv2 before dev publication.

Focused evidence: **86 matcher/proposal tests passed** (33s), including exact factor1 amounts/totals, both alias directions, area/length refusal, ambiguity and a real cheaper price-list proposal. Compile/whitespace PASS. No new contract/migration/dependency/style change by this lane; shared schema belongs to the cost-preflight owner. No heavy gate, live model or remote publication.
