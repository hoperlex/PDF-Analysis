/** Public API of the `start-run` feature. */

export type { StartRunCommand, StartRunIntent } from './model/start-run-intent';
export { chosenExecutor, startRunBody, startRunIntent } from './model/start-run-intent';
export { useStartRun } from './model/use-start-run';

export type { StartChoice, StartMode, StartSelectors } from './model/start-mode';
export {
  AUTOMATIC_CHOICE, START_CHOICE_MISSING, START_MODES, START_MODE_HINTS, START_MODE_LABELS, chooseMode,
  selectorCount, startChoiceComplete, startSelectors,
} from './model/start-mode';

// `AR-V3-OPT-IN`: the radio that chooses the analysis of one start; the rules around it are the run list's.
export type { AnalysisChoiceProps, AnalysisChoiceValue } from './ui/analysis-choice';
export { ANALYSIS_CHOICE_LABEL, ANALYSIS_CHOICE_OPTIONS, AnalysisChoice } from './ui/analysis-choice';

export type { StartRunControlProps } from './ui/start-run-control';
export { StartRunControl } from './ui/start-run-control';

export type { PresetListReading, PresetSelectViewProps } from './ui/preset-select';
export { PresetSelectView, chosenPreset } from './ui/preset-select';

export type { GroupListReading, GroupSelectViewProps } from './ui/group-select';
export { GROUP_OPTION_NONE, GroupSelect, GroupSelectView, chosenGroup, groupOptionLabel } from './ui/group-select';

export type { ExecutorListReading, ExecutorSelectViewProps } from './ui/executor-select';
export { DEFAULT_EXECUTOR_LABEL, ExecutorSelectView } from './ui/executor-select';

export type { StartRunFailureViewProps } from './ui/start-run-failure';
export { StartRunFailureView } from './ui/start-run-failure';

// `R-151c`: starting several documents with one agreement.
export type { BatchEntry, BatchEstimate, BatchOutcome, BatchTotals } from './model/batch-start';
export { batchConsent, batchTotals, estimateFits, minimumCeiling } from './model/batch-start';
export type { BatchStartApi } from './model/use-batch-start';
export { useBatchStart } from './model/use-batch-start';
export type { BatchStartPanelProps, BatchStartPanelViewProps } from './ui/batch-start-panel';
export { BatchStartPanel, BatchStartPanelView } from './ui/batch-start-panel';
