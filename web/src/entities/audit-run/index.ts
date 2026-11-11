/**
 * Public API of the `audit-run` entity.
 *
 * The review slice depends on two things here, per the UI seam's integration contract:
 * the run-state and provider-mode selectors, and the guarantee that this is the only
 * slice that polls the run endpoint.
 */

export type { ProviderModeLabel, RunCostReading, RunOutcome, StageRow } from './model/run-presentation';
export type { ExtendedReportFile, ExtendedReportFormat } from './lib/extended-report';
export { formatExtendedRunReport } from './lib/extended-report';
export { EXTENDED_ADVICE, EXTENDED_CORRECTION_ACTION, EXTENDED_REASONS, EXTENDED_NORM_STATUS, extendedReasonText } from './lib/extended-labels';
export {
  PC01_STAGE_IDS,
  PROVIDER_MODE_UNKNOWN,
  PROVIDER_MODE_UNRECOGNIZED,
  STAGE_DEPENDS_ON,
  badgeProviderMode,
  costBasisCaption,
  diagnosticObservationCount,
  elapsedMs,
  formatCostMicros,
  formatElapsed,
  hasKnownRunVocabulary,
  interruptedReason,
  isRunAnimating,
  providerModeCaption,
  providerModeLabel,
  runCost,
  runHasPublishedResult,
  runOutcome,
  runProviderMode,
  stageRows,
} from './model/run-presentation';

export type { RunChipDefinition, RunChipId } from './model/stage-dictionary';
export { RUN_CHIP, RUN_CHIPS, RUN_CHIP_IDS, chipById, chipOfStage, phaseFullLabel } from './model/stage-dictionary';
export { shortModelName } from './model/model-short-name';
export type { LiveProgress, ProcedureReading, ProcedureStatus } from './model/extended-readings';
export { PROCEDURE_STATUS_VALUES, extendedLiveProgress, liveProgressText, procedureReadings } from './model/extended-readings';
export type { ChipProgress, ChipState, RunChip, RunChipsInput } from './model/run-chips';
export { CHIP_STATE_LABELS, chipProgress, runChips } from './model/run-chips';

export type { RunFinishEstimate } from './model/run-estimate';
export { formatClockTime, runFinishEstimate } from './model/run-estimate';

export type { ComparedFact, ComparedStage, Comparison, FactId, StageSide } from './model/run-comparison';
export {
  comparableCostMicros,
  compareReadings,
  comparedCount,
  comparedFacts,
  comparedStages,
  defaultPair,
  differenceCount,
  runElapsedMs,
  terminalDetailDigest,
  terminalDetailKeys,
} from './model/run-comparison';

export type { TerminalReasonNote } from './model/terminal-reason';
export { ABSENT_SENTENCE, UNDESCRIBED_PREFIX, terminalReasonNote } from './model/terminal-reason';

export { looksLikeRunId } from './model/address';

export type { RunFailure, RunFailureKind } from './model/run-failure';
export { classifyRunFailure } from './model/run-failure';

export type { ExecutorRefusal, ExecutorRefusalKind } from './model/executor-refusal';
export { EXECUTOR_DEPENDENCY, EXECUTOR_FIELD, executorRefusal } from './model/executor-refusal';

export type { GroupRefusal, GroupRefusalKind } from './model/group-refusal';
export { GROUP_FIELD, groupRefusal } from './model/group-refusal';

export type { PresetRefusal, PresetRefusalKind } from './model/preset-refusal';
export { PRESET_FIELD, presetRefusal } from './model/preset-refusal';

export type { RunPresetLine } from './model/run-preset';
export { runPresetLine, runPresetSentence, runPresetValue } from './model/run-preset';

export { QUEUE_REASON_LABELS, knownQueueReason, runQueueReason, runQueueReasonLabel } from './model/run-queue-reason';
export type { RunWaitCellsLine, RunWaitModel } from './model/run-wait-cells';
export { WAIT_CAUSE_LABELS, WAIT_MODELS_SHOWN, knownWaitCause, runWaitCellsLine, runWaitCellsSentence } from './model/run-wait-cells';
export type { RunNextTask, RunNextTaskSource } from './model/run-next-task';
export { nextTaskPlace, nextTaskWhy, nextTaskWork, runNextTask } from './model/run-next-task';

export type { QueueItemWaitingReading } from './model/queue-item-waiting';
export { queueItemWaiting } from './model/queue-item-waiting';
export type { QueueItemWaitingProps } from './ui/queue-item-waiting';
export { QueueItemWaiting } from './ui/queue-item-waiting';

export type { RunExecutorLine } from './model/run-executor';
export {
  boundExecutorValue, plannedExecutorValue, runExecutorLine, runExecutorSentence, runExecutorValue, runWaitingSentence,
} from './model/run-executor';

export type { RoutingRefusal, RoutingRefusalKind } from './model/routing-refusal';
export {
  SECTION_PROFILE_UNAVAILABLE_REFUSAL,
  VERSION_UNCLASSIFIED_REFUSAL,
  routingRefusal,
} from './model/routing-refusal';

export type { InputBudgetFigures } from './model/input-budget';
export { DIGIT_GROUP_SEPARATOR, groupDigits, inputBudgetFigures, inputBudgetSentence } from './model/input-budget';

export { RUN_PAGE_LIMIT, runListQueryOptions, useRunList } from './api/use-run-list';

export { runStatusQueryOptions } from './api/run-status-query';

export type { RunStatusPolling } from './api/use-run-status';
export { recordRunReading, useRunStatus } from './api/use-run-status';

export type { RunStagesView } from './api/use-run-stages';
export { runStagesKey, runStagesQueryOptions, useRunStages } from './api/use-run-stages';
export type { ChipModelLine } from './model/run-stages';
export { chipModelLine, modelsCount, planModelIds, stageOfChip } from './model/run-stages';

export type { RunTableProps } from './ui/run-table';
export { RunTable, STARTED_BY_UNKNOWN } from './ui/run-table';

export type { StageActivity } from './model/stage-activity';
export { chipPagesText, stageActivity, stageActivityText } from './model/stage-activity';

export type { StageTableProps } from './ui/stage-table';
export { StageTable } from './ui/stage-table';
