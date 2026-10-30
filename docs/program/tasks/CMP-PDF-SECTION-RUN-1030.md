# CMP-PDF-SECTION-RUN-1030 — ordinary section analysis for comparison PDFs

## Outcome
A classified PDF imported from a comparison ZIP can receive a normal section cost estimate, start a Run and execute against its native PDF text and pages.

## Depends on
- CMP-ONLY-RUN-GATE-1030 (complete; its UI-only refusal is superseded here)

## Frozen inputs
- API 1.14.0; domain error-code set unchanged; migration head `0043_stage_ai_generations`.
- Base commit `08431d8a`; `comparison_pdf` versions store `comparison.source_pdf` and no portal text count.

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- `RunCostPreflight._source` previously refused a missing portal text count; run admission and execution previously required `source.document`. The reported `comparison_only_version` error is from this ordinary run path.

## Historical evidence
- correction_mode: addendum
- source_record: `docs/program/tasks/CMP-ONLY-RUN-GATE-1030.md`
- addendum_path: this task

## Publication authority
- development_target: origin/dev
- origin_main_authority: none

## Allowed paths
- `src/auditmanager/analysis/public.py`
- `src/auditmanager/analysis/stages/source_preparation.py`
- `src/auditmanager/api/schemas/models.py`
- `src/auditmanager/documents/README.md`
- `src/auditmanager/documents/models.py`
- `src/auditmanager/runs/commands.py`
- `src/auditmanager/runs/executor.py`
- `src/auditmanager/runs/preflight.py`
- `web/src/_pages/version-detail/ui/version-detail-page.tsx`
- `web/src/entities/document-version/index.ts`
- `web/src/entities/document-version/model/upload-kind.ts`
- `web/src/entities/document-version/ui/comparison-only-mark.tsx`
- `web/src/entities/document-version/ui/version-panel.tsx`
- `web/src/entities/document-version/ui/version-row.tsx`
- `web/src/features/start-run/ui/start-run-control.tsx`
- `web/src/shared/api/catalog-message.ts`
- `web/src/shared/api/generated/types.gen.ts`
- `web/src/widgets/run-list/ui/run-list.tsx`
- `contracts/api/v1/openapi.json`
- `contracts/domain/v1/error-codes.json`
- `tests/integration/ingest/comparison_pdf/test_http.py`
- `tests/integration/ingest/comparison_pdf/test_run_refusal.py`
- `tests/unit/runs/test_cost_preflight.py`
- `tests/unit/runs/test_executor_choice.py`
- `web/tests/unit/version-mark/comparison-only-version.test.ts`
- `web/tests/unit/cost-approval/start-cost-flow.test.ts`
- `docs/program/tasks/CMP-PDF-SECTION-RUN-1030.md`
- `docs/program/CURRENT_STATE.md`

## Forbidden hotspots
- Migrations, root dependencies and lockfiles, composition root, global styles and `origin/main`.

## Non-goals
- Portal-only AR six-check group, OCR for image-only PDFs, live model acceptance and full gate.

## Deliverables
- Source-role adapter, bounded native-text cost count, execution binding, ordinary UI control, corrected contract descriptions and focused checks.

## Required tests
- Focused Python unit and web render tests, typecheck, web production build, Python compile and diff check.

## Integration contract
- `comparison.source_pdf` remains the stored manifest role. For ordinary Runs it supplies `source.document`; the frozen input digest binds both roles to the same blob. Cost preflight verifies and counts the actual PDF. Existing portal versions keep their stored count and source role. This task owns the description-only API/domain contract correction and dev integration slot; no schema shape, error code or migration changes.

## Failure/idempotency/security cases
- Missing/changed PDF bytes and invalid full PDF interpretation refuse before a new cost consent. Start still checks classification and cost consent before claiming a new idempotency key. The AR six-check group still refuses absent portal inputs.

## Rollback / feature flag
- Revert this dev commit to restore the prior refusal. No new flag or data migration.

## Handoff
- Dev-only hotfix. No main publication authority. Check results and SHA belong in the final handoff.
