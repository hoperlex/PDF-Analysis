/** Public API of the `start-run` feature. */

export type { StartRunCommand, StartRunIntent } from './model/start-run-intent';
export { startRunBody, startRunIntent } from './model/start-run-intent';
export { useStartRun } from './model/use-start-run';

// `AR-V3-OPT-IN`: the radio that chooses the analysis of one start; the rules around it are the run list's.
export type { AnalysisChoiceProps, AnalysisChoiceValue } from './ui/analysis-choice';
export { ANALYSIS_CHOICE_LABEL, ANALYSIS_CHOICE_OPTIONS, AnalysisChoice } from './ui/analysis-choice';

export type { StartRunControlProps } from './ui/start-run-control';
export { DEFAULT_READINESS_NOTE, StartRunControl, UNCAPPED_START_LABEL } from './ui/start-run-control';

// `RUN-START-ONE-01a`: the one dialog of a start that can charge money, and the rules of the one-button start.
export type { StartRunCostDialogProps, StartRunCostDialogViewProps } from './ui/start-run-cost-dialog';
export { StartRunCostDialog, StartRunCostDialogView, UNCAPPED_MEANING } from './ui/start-run-cost-dialog';
export {
  automaticConsent, chargesMoney, dialogConsent, estimateChanged, initialCeiling,
} from './model/one-click-start';

export type { StartRunFailureViewProps } from './ui/start-run-failure';
export { StartRunFailureView } from './ui/start-run-failure';

// `R-151c`: starting several documents with one agreement.
export type { BatchEntry, BatchEstimate, BatchOutcome, BatchTotals } from './model/batch-start';
export { batchConsent, batchIsFree, batchTotals, estimateFits, minimumCeiling } from './model/batch-start';
export type { BatchStartApi } from './model/use-batch-start';
export { useBatchStart } from './model/use-batch-start';
export type { BatchStartPanelProps, BatchStartPanelViewProps } from './ui/batch-start-panel';
export { BatchStartPanel, BatchStartPanelView } from './ui/batch-start-panel';
