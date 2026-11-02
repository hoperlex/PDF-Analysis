# Task REVIEW-FIX-TESTS-1102 — tests and pins agree with the served behaviour again

## Outcome
Every composed-app suite that starts a Run passes a real priced consent; one test proves the served
API refuses a Run without consent; the frontend lock, the expected-facts head, the surface counts,
the R-66 menu guard and the comparison-PDF refusal tests describe the tree as it is after this wave.

## Depends on
- REVIEW-FIX-BOUNDS-1102
- REVIEW-FIX-SEAMS-1102
- REVIEW-FIX-ANALYSIS-1102
- REVIEW-FIX-CMP-RUNTIME-1102
- REVIEW-FIX-CMP-SPEC-1102

## Frozen inputs
- domain contract: as left by REVIEW-FIX-BOUNDS-1102 (prose only)
- API contract: 1.14.0
- analysis/comparison/event contract: unchanged
- migration head: as left by REVIEW-FIX-CMP-SPEC-1102 (`0045_comparison_page_bounds`)
- base commit: the integration tip after the five tasks above
- findings: S6-02, S9-03, S9-04, S8-04, S7-design-03, S9-07, S9-09 in `.local/reports/code-review-2026-11-02/*.findings.md`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- premise: the frontend lock pins a contract that no longer exists

### P-01 — locked versus actual OpenAPI digest
- captured_at: 2026-11-02
- command: `grep -n '"sha256"' web/FRONTEND_LOCK.json && sha256sum contracts/api/v1/openapi.json`
- captured_output:
  ```text
  19:    "sha256": "05397fad027834c0f037d0890e4a059207b7881445b810cbc0bac2137b7233dd",
  11db634e3a35f9e94c1a5b1d18aa42f675ce0a32327b82f1d2c12d2bb002b466  contracts/api/v1/openapi.json
  ```
- interpretation: `web/tests/guards/frontend-lock.guard.test.ts` cannot pass on the base.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `tests/**`
- `web/tests/**`
- `web/FRONTEND_LOCK.json`
- `web/src/shared/api/authorization.ts`

## Forbidden hotspots
- `src/**` except `web/src/shared/api/authorization.ts`, contracts, migrations, `infra/**`, root dependency/lock files, global styles

## Non-goals
- Weakening any assertion; re-capturing a characterization corpus without first asserting the new behaviour.

## Deliverables
- S6-02: a helper in `tests/support` that calls `POST /runs/cost-estimate` and then starts the Run with `cost_consent` from the estimate; every suite that starts a Run through the composed app uses it; one new test proves the served API answers 422 without consent and writes nothing.
- S9-03: `web/FRONTEND_LOCK.json` re-measured from the tree (OpenAPI digest, snapshot digest, content commit, generated-file digests).
- S9-04: `tests/support/expected_facts.json` migration head = the real newest migration.
- S8-04: `authorization.ts` operation count and the addressed/served pins re-measured with their own counting rule.
- S7-design-03: the R-66 guard reads labels through the new icon markup and lists `/stage-comparison`.
- S9-07: one test that a group start on a comparison-only source still writes nothing where refusal remains.
- S9-09: the loosened `calls >= 5` returns to the exact count the code produces.
- Any pin this wave made stale (contract prose digests, recovery inventories), re-measured, never loosened.

## Verification
- Optional per owner instruction. Proof checks if run: the frontend lock guard and `.venv/bin/pytest -q tests/contract/program tests/support`.

## Integration contract
- The lane does not run git. The integrator commits exactly the allowed paths it changed.

## Rollback / feature flag
- Tests and pins only.
