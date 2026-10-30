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
export {
  AR_V3_BETA_PROFILE_ID,
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
export { arV3GroupReviewAddress, looksLikeArV3GroupId } from './model/ar-v3-group-id';

export type { ArV3PackFaultReason, ArV3PackReading, ArV3PackScopeId } from './model/ar-v3-pack-status';
export { AR_V3_PACK_SCOPE_IDS, readArV3PackStatus } from './model/ar-v3-pack-status';

export { looksLikeRunId } from './model/address';

export type { RunFailure, RunFailureKind } from './model/run-failure';
export { classifyRunFailure } from './model/run-failure';

export type { ExecutorRefusal, ExecutorRefusalKind } from './model/executor-refusal';
export { EXECUTOR_DEPENDENCY, EXECUTOR_FIELD, executorRefusal } from './model/executor-refusal';

export type { PresetRefusal, PresetRefusalKind } from './model/preset-refusal';
export { PRESET_FIELD, presetRefusal } from './model/preset-refusal';

export type { RunPresetLine } from './model/run-preset';
export { runPresetLine, runPresetSentence, runPresetValue } from './model/run-preset';

export type { RunExecutorLine } from './model/run-executor';
export {
  runExecutorLine, runExecutorSentence, runExecutorValue, runWaitingSentence,
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

export type { ArV3PackView } from './api/use-ar-v3-pack-status';
export { arV3PackStatusQueryOptions, useArV3PackStatus } from './api/use-ar-v3-pack-status';

export type { RunStatusPolling } from './api/use-run-status';
export { useRunStatus } from './api/use-run-status';

export type { RunRowProps } from './ui/run-row';
export { RunRow } from './ui/run-row';

export type { StageTableProps } from './ui/stage-table';
export { StageTable } from './ui/stage-table';
