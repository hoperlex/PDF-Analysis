/**
 * Public API of the `audit-run` entity.
 *
 * The review slice depends on two things here, per the UI seam's integration contract:
 * the run-state and provider-mode selectors, and the guarantee that this is the only
 * slice that polls the run endpoint.
 */

export type { ProviderModeLabel, RunCostReading, RunOutcome, StageRow } from './model/run-presentation';
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
export { looksLikeArV3GroupId } from './model/ar-v3-group-id';

export { looksLikeRunId } from './model/address';

export type { RunFailure, RunFailureKind } from './model/run-failure';
export { classifyRunFailure } from './model/run-failure';

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
export { useRunStatus } from './api/use-run-status';

export type { RunRowProps } from './ui/run-row';
export { RunRow } from './ui/run-row';

export type { StageTableProps } from './ui/stage-table';
export { StageTable } from './ui/stage-table';
