/**
 * Public API of the `audit-run` entity.
 *
 * The review slice depends on two things here, per the UI seam's integration contract:
 * the run-state and provider-mode selectors, and the guarantee that this is the only
 * slice that polls the run endpoint.
 */

export type { ProviderModeLabel, RunCostReading, RunOutcome, StageRow } from './model/run-presentation';
export {
  PC01_STAGE_IDS,
  PROVIDER_MODE_UNKNOWN,
  badgeProviderMode,
  costBasisCaption,
  diagnosticObservationCount,
  elapsedMs,
  formatCostMicros,
  formatElapsed,
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

export type { RunFailure, RunFailureKind } from './model/run-failure';
export { classifyRunFailure } from './model/run-failure';

export { RUN_PAGE_LIMIT, useRunList } from './api/use-run-list';

export type { RunStatusPolling } from './api/use-run-status';
export { useRunStatus } from './api/use-run-status';

export type { RunRowProps } from './ui/run-row';
export { RunRow } from './ui/run-row';

export type { StageTableProps } from './ui/stage-table';
export { StageTable } from './ui/stage-table';
