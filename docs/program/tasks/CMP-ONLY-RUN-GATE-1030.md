# CMP-ONLY-RUN-GATE-1030 — route comparison PDFs to comparison runs

## Outcome
The version page does not offer ordinary analysis before the version kind is known, and a comparison-only PDF points to version/stage comparison instead of an unusable ordinary cost estimate.

## Depends on
- CMP-STAGE-MAP-PREREQ-1030 (complete)

## Frozen inputs
- domain/comparison contract: ADR-0025 `comparison_pdf`/`comparison_only_version`, unchanged
- API contract: 1.14.0, unchanged
- migration head: `0043_stage_ai_generations`, unchanged
- base commit: `49fd95ea`

## Enumerator ownership
- enumerated_set_changed: no
- enumerator_path: not_applicable
- enumerator_owner: not_applicable
- totality_query: not_applicable

## Captured premise evidence
- The reported title `Стоимость не оценена` appears only in ordinary `StartRunControl`, not stage comparison. The server intentionally refuses ordinary section analysis for `comparison_pdf`; stage comparison uses a separate estimate and accepts the saved stage-map revision. The version page mounted `RunList` while `upload_kind` was still unknown and its "compare versions" link went to the two-runs route.

## Historical evidence
- correction_mode: none
- source_record: not_applicable
- addendum_path: not_applicable

## Publication authority
- development_target: origin/dev (owner's hotfix/dev instruction)
- origin_main_authority: none

## Allowed paths
- `web/src/_pages/version-detail/ui/version-detail-page.tsx`
- `web/src/features/start-run/ui/start-run-control.tsx`
- `web/tests/unit/version-mark/comparison-only-version.test.ts`
- `web/tests/unit/cost-approval/start-cost-flow.test.ts`
- `docs/program/tasks/CMP-ONLY-RUN-GATE-1030.md`

## Forbidden hotspots
- `contracts/**`, migrations, root dependencies/lockfiles, composition root, global styles, generated client, `origin/main`.

## Non-goals
- No section-analysis admission of comparison-only PDF, backend/contract change, live model call, full gate or main deployment.

## Deliverables
- Deferred ordinary run controls until version kind is read; correct module links; actionable fallback for a server `comparison_only_version` cost refusal.

## Required tests
- Focused version-mark and cost-flow tests, web typecheck, production web build, staged diff check.

## Integration contract
- `comparison_pdf` stays eligible for version/stage comparison and ineligible for ordinary section analysis. Existing portal-bundle versions keep the ordinary cost-consent flow.

## Failure/idempotency/security cases
- Unknown version kind while loading cannot start an ordinary run. A late comparison-only refusal blocks repeat cost requests; its correlation ID remains visible.

## Rollback / feature flag
- Revert the UI change; no new flag or stored-data migration.

## Handoff
- Final check results and published SHA are reported by the integrator. Main remains untouched.
