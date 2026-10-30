# CMP-ZIP-TRANSPORT-1030 — repair comparison ZIP request transport

## Outcome
The version ZIP import and both comparison/stage file-part uploads leave the browser with their declared binary media types.

## Depends on
- HOTFIX-PRESENTATION-INT-1030 (complete)

## Frozen inputs
- domain/comparison contract: ADR-0025, unchanged
- API contract: 1.14.0, unchanged; `importComparisonZip` declares `application/zip`
- migration head: `0043_stage_ai_generations`, unchanged
- base commit: `4d4201f5`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- `web/src/shared/api/transport.ts` accepted JSON and multipart request bodies only; the generated ZIP import and comparison-part methods declare binary bodies. A client-side `ClientUsageError` produced the reported generic UI message before fetch.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev (owner chose dev only)
- origin_main_authority: none

## Allowed paths
- `web/src/shared/api/transport.ts`
- `web/tests/unit/api/transport-rules.test.ts`
- `docs/program/tasks/CMP-ZIP-TRANSPORT-1030.md`

## Forbidden hotspots
- `contracts/**`, migrations, root dependencies/lockfiles, composition root, global styles, generated client, `origin/main`.

## Non-goals
- No API/server behavior change, live model call, full gate or main deployment.

## Deliverables
- Narrow binary request handling for ZIP and octet-stream; generated-client regressions using synthetic VS1 and SP1 archives.

## Required tests
- Focused `transport-rules.test.ts`, web typecheck, production web build, staged diff check.

## Integration contract
- `importComparisonZip` sends its Blob unchanged with `Content-Type: application/zip`; comparison and stage part methods send their Blob with `application/octet-stream`. Existing JSON/multipart behavior remains.

## Failure/idempotency/security cases
- Non-Blob binary requests fail before fetch. Existing idempotency key and response/error handling are retained.

## Rollback / feature flag
- Revert this narrow client change; no new flag or stored-data migration.

## Handoff
- Final check results and published SHA are reported by the integrator. Main remains untouched.
