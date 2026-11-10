/** Public API of the `start-run` feature. */

export type { StartRunCommand, StartRunIntent } from './model/start-run-intent';
export { startRunBody, startRunIntent } from './model/start-run-intent';
export { useStartRun } from './model/use-start-run';

// `AR-V3-OPT-IN`: the radio that chooses the analysis of one start; the rules around it are the run list's.
export type { AnalysisChoiceProps, AnalysisChoiceValue } from './ui/analysis-choice';
export { ANALYSIS_CHOICE_LABEL, ANALYSIS_CHOICE_OPTIONS, AnalysisChoice } from './ui/analysis-choice';

// `READINESS-WEB-01`: the line under «Запустить» and the reason the button is inactive, read from `getRunStartReadiness`.
export {
  ACCESS_WORDS, CLIENT_DOCUMENTS_MARK, CONNECT_SERVER, CONTACT_ADMIN, LEGACY_ROUTE_NOTE, MODELS_BY_STAGE_LABEL, NOT_READY,
  READINESS_NOT_READ, READINESS_READING, blockedModels, layoutNotAvailable, readinessLine,
} from './model/readiness';
export type { ReadinessLine } from './model/readiness';
export type { RunStartReadinessReading } from './model/use-run-start-readiness';
export { runStartReadinessKey, useRunStartReadiness } from './model/use-run-start-readiness';
export type { ReadinessLinePlanProps } from './ui/readiness-line';
export { ReadinessLinePlan, readinessNoteOf } from './ui/readiness-line';

export type { StartRunControlProps } from './ui/start-run-control';
export { DEFAULT_READINESS_NOTE, StartRunControl, UNCAPPED_START_LABEL } from './ui/start-run-control';

// `RUN-START-ONE-01a`: the one dialog of a start that can charge money (the control mounts it; the view is public for the
// contrast census and the language guard, which draw it open). `RUN-START-ONE-01b`: the connected dialog is public too, so the
// queue's repeated Run asks the same question in the same words (`subject` names the Run).
export type { StartRunCostDialogProps, StartRunCostDialogViewProps } from './ui/start-run-cost-dialog';
export { StartRunCostDialog, StartRunCostDialogView } from './ui/start-run-cost-dialog';

export type { StartRunFailureViewProps } from './ui/start-run-failure';
export { StartRunFailureView } from './ui/start-run-failure';

// `R-151c`: starting several documents with one agreement.
export type { BatchEntry, BatchEstimate, BatchOutcome, BatchTotals } from './model/batch-start';
export { batchConsent, batchIsFree, batchTotals, estimateFits, minimumCeiling } from './model/batch-start';
export type { BatchStartApi } from './model/use-batch-start';
export { useBatchStart } from './model/use-batch-start';
export type { BatchStartPanelProps, BatchStartPanelViewProps } from './ui/batch-start-panel';
export { BatchStartPanel, BatchStartPanelView } from './ui/batch-start-panel';
