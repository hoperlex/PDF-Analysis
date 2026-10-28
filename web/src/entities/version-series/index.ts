/**
 * Public API of the `version-series` entity (`CMP-VC-UI-01`): the reads and commands of the version comparison
 * (the overview, the effective matrix and its edits, the series of adjacent transitions, the order of the versions,
 * the thumbnails, the queue summary), and everything that says them in Russian — the steps and their states, the
 * verdict of a transition, the cells of the matrix, the draft of manual edits and the refusals of the module.
 *
 * Nothing here draws. The tables, the matrix and the dialogs are in `widgets/version-series` and
 * `widgets/comparison-upload`; the viewer of one pair is `widgets/comparison-viewer`.
 */

export { COMPARISON_KEYS } from './api/keys';
export { useKeyedCommand } from './api/use-keyed-command';
export { OVERVIEW_BUSY_POLL_MS, OVERVIEW_IDLE_POLL_MS, overviewQueryOptions, useComparisonOverview } from './api/use-overview';
export type { ApplyEditsCommand, PrepareCommand, UndoEditCommand } from './api/use-matrix';
export {
  EDIT_HISTORY_LIMIT,
  MATRIX_BUILD_POLL_MS,
  applySignature,
  useApplyMatrixEdits,
  useComparisonEdits,
  useComparisonMatrix,
  usePrepareMatrix,
  useUndoMatrixEdit,
} from './api/use-matrix';
export type { SeriesAct, SeriesActCommand, StartSeriesCommand } from './api/use-series';
export {
  PAIR_PAGE_CAP,
  PAIR_PAGE_LIMIT,
  SERIES_POLL_MS,
  useLatestSeries,
  useSeriesAct,
  useSheetPair,
  useSheetPairs,
  useStartSeries,
} from './api/use-series';
export type { AppendOrderCommand } from './api/use-order';
export { useAppendOrder, useLatestOrder } from './api/use-order';
export { useComparisonQueueSummary, usePageProfile } from './api/use-extras';
export { classifyThumbnailFailure, useThumbnail } from './api/use-thumbnail';

export { MODULE_OFF_DETAIL, MODULE_OFF_TITLE, versionsModuleOn } from './model/module';
export type { ShownStep, StepTone, StepView } from './model/steps';
export {
  LATER_STEPS,
  LATER_STEPS_NOTE,
  SHOWN_STEPS,
  STEP_HINTS,
  STEP_LABELS,
  STEP_NUMBERS,
  TONE_BADGES,
  TONE_ICONS,
  isRunningState,
  stepRank,
  stepView,
} from './model/steps';
export type { OverviewFilter, OverviewGroup, OverviewView, Sort, SortDirection, SortKey } from './model/overview-view';
export {
  INITIAL_VIEW,
  NEXT_STEP_LABELS,
  OVERVIEW_FILTERS,
  SORT_PRESETS,
  anythingRunning,
  codeOf,
  countsOf,
  groupOf,
  inScope,
  markOf,
  marksOf,
  nextSort,
  parseSort,
  sortValue,
  visibleSets,
} from './model/overview-view';
export type { VerdictPart } from './model/verdict';
export { NO_VERDICT_YET, aiDependenceNote, verdictParts, verdictSentence } from './model/verdict';
export {
  SERIES_STALE_LABELS,
  SERIES_STATE_LABELS,
  STALE_SERIES_NOTE,
  TRANSITION_STATE_LABELS,
  canCancelSeries,
  continueOf,
  latestSeries,
  progressPercent,
  staleReasonsLine,
  transitionOf,
} from './model/series-words';
export type { SeriesContinue } from './model/series-words';
export {
  CELL_REASON_WORDS,
  CELL_STATE_LABELS,
  CONFIDENCE_MARKS,
  EDIT_KIND_LABELS,
  EDIT_SOURCE_LABELS,
  EDIT_STATUS_LABELS,
  FLAG_MARKS,
  MATRIX_STALE_LABELS,
  MATRIX_STATE_LABELS,
  PAIR_STATE_LABELS,
  SHEET_STATUS_BADGES,
  SPLIT_PART_MARK,
  SPLIT_WHOLE_MARK,
  UNDESCRIBED_REASON,
  cellReasonWords,
} from './model/matrix-words';
export type { ClickAnswer, ClickContext } from './model/click-notes';
export {
  CHAIN_NOTE,
  CHOOSE_TWO_DIFFERENT,
  ONE_VERSION_NOTE,
  PAIR_NOT_READY,
  answerClick,
} from './model/click-notes';
export type { StepAction, StepActionId } from './model/step-actions';
export {
  RESTART_CONFIRM_ACTION,
  RESTART_CONFIRM_TEXT,
  RESTART_CONFIRM_TITLE,
  stepActions,
} from './model/step-actions';
export type { Sides } from './model/matrix-view';
export {
  adjacentSides,
  columnName,
  columnNames,
  cellOf,
  changedRows,
  defaultSides,
  isSoleSheet,
  matchedCells,
  openablePairs,
  pageKey,
  pairOfRow,
  referencePage,
  rowHeading,
  samePage,
  splitDirection,
  validSides,
} from './model/matrix-view';
export {
  ORDER_DIALOG_TEXT,
  ORDER_SAVE_HINT,
  baseRevisionOf,
  moveVersion,
  sameOrder,
} from './model/order';
export type { Draft, DraftEdit, Rebased } from './model/draft';
export {
  DRAFT_LIMIT,
  EMPTY_DRAFT,
  addEdit,
  describeEdit,
  isStale,
  rebase,
  removeAt,
  removeLast,
  requestOf,
  revisionKey,
  toInput,
  touchedPages,
} from './model/draft';
export {
  FILE_STATE_LABELS,
  ORDER_SOURCE_LABELS,
  PROPOSAL_WARNING_LABELS,
  SET_STATUS_LABELS,
  UPLOAD_STATE_LABELS,
  canConfirmSet,
  canExcludeSet,
  canRetrySet,
  uploadIsActive,
} from './model/upload-words';
export type { GestureResult } from './model/matrix-edits';
export {
  ALREADY_THERE,
  DRAG_TYPE,
  NO_REFERENCE_SHEET,
  SOLE_SHEET,
  WRONG_COLUMN,
  dragPayload,
  dropOnCell,
  linkCandidate,
  markAbsent,
  parseDragged,
  unlinkSheet,
} from './model/matrix-edits';
export type { ComparisonFailure, ComparisonFailureKind } from './model/failure';
export {
  COMPARISON_CONFLICT_SENTENCES,
  COMPARISON_CONSTRAINT_SENTENCES,
  COMPARISON_DEPENDENCY_SENTENCES,
  COMPARISON_INTEGRITY_SENTENCE,
  UNDESCRIBED_FAILURE,
  UPLOAD_FAILURE_REASON_SENTENCES,
  comparisonFailure,
  comparisonReasonSentence,
  uploadFailureReasonSentence,
} from './model/failure';
export {
  OTHER_QUEUE_KIND,
  QUEUE_KIND_LABELS,
  QUEUE_MODULE_LABELS,
  QUEUE_STATE_LABELS,
  QUEUE_STATE_ORDER,
  modulesSentence,
  queueKindLabel,
} from './model/queue-words';
export type { ThumbnailSnapshot, ThumbnailState } from './model/thumbnail-store';
export { ThumbnailStore } from './model/thumbnail-store';
