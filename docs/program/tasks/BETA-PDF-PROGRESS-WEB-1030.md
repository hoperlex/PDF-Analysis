# BETA-PDF-PROGRESS-WEB-1030

## Outcome
The Run screen shows real durable page-validation progress and an explicit PDF precheck failure before analysis. It reuses the existing Run polling cadence.

## Depends on
- CMP-INT-HOTFIX-RECONCILE-1030

## Frozen inputs
Owner poll2026-10-30: background PDF validation before analysis, progress and explicit error. Producer seam assigned to BETA-PDF-PRECHECK-1030: stage.pdf_precheck/AuditRun, source_preparation, phase started/checking/completed/failed, completed_pages/total_pages integers. Current ExecutionJournalEntry already carries scalar payload.

## Allowed paths
- web/src/widgets/run-progress/**
- web/src/entities/audit-run/api/use-run-status.ts
- web/src/entities/execution/model/presentation.ts (controlled event label only)
- web/tests/unit/run/pdf-precheck-progress.test.ts
- docs/program/tasks/BETA-PDF-PROGRESS-WEB-1030.md
- docs/program/BETA-PDF-PROGRESS-WEB-1030.md

## Forbidden hotspots
Contracts/generated, backend/worker producer, root dependencies/global styles, cost UI and remote main.

## Non-goals
No inferred percentages, extra polling loop, source text display or changed result/analysis behavior.

## Deliverables
Validated latest-event projection and page progress UI; existing onReading invalidates the current journal read. Missing/invalid evidence remains explicit.

## Verification
Focused parser/render and existing Run/poll tests, typecheck, compile/whitespace; no browser/heavy window.

## Integration contract
PDF producer emits events in its authority-fenced transaction. UI reads the exact run’s newest stage event through listExecutionJournal. Cancellation hides activity, completed source stage stops refresh.

## Rollback
Remove view/invalidation through a forward commit; durable events and results remain intact.
