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
export type { AiStepId, SelectableStep, ShownStep, StepTone, StepView } from './model/steps';
export {
  AI_STEP_IDS,
  SELECTABLE_STEPS,
  SHOWN_STEPS,
  STEP_HINTS,
  STEP_LABELS,
  STEP_NUMBERS,
  TONE_BADGES,
  TONE_ICONS,
  isRunningState,
  stepRank,
  stepView,
  toneOfState,
} from './model/steps';
export type { OverviewFilter, OverviewGroup, OverviewView, Sort, SortDirection, SortKey } from './model/overview-view';
export {
  INITIAL_VIEW,
  NEXT_STEP_LABELS,
  ONE_VERSION_SENTENCE,
  OVERVIEW_FILTERS,
  READY_SENTENCE,
  SORT_PRESETS,
  anythingRunning,
  codeOf,
  countsOf,
  groupOf,
  inScope,
  markOf,
  marksOf,
  nextSort,
  nextStepSentence,
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
  canRestart,
  continueOf,
  hasLeftovers,
  latestSeries,
  progressPercent,
  staleReasonsLine,
  transitionOf,
} from './model/series-words';
export type { SeriesContinue } from './model/series-words';
export {
  CHANNEL_WORDS,
  PAIR_REASON_WORDS,
  PART_ROLE_LABELS,
  PERMIT_HEADING,
  PERMIT_STATE_LABELS,
  pairReasonWords,
  partsLine,
} from './model/pair-words';
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

// ------------------------------------------------------------------------------ wave C2 (`CMP-VC-UI-02`): the AI layer

export { AI_POLL_MS, AI_QUEUE_POLL_MS } from './api/use-ai';
export type { EstimateScope } from './api/use-ai';
export {
  estimateScopeKey,
  useAiEstimate,
  useAiPairCheck,
  useAiPairHints,
  useAiQueue,
  useAiSheetChanges,
  useDescriptionHistory,
  useLaunchQueue,
  useReports,
  useReviewSheets,
  useSheetDescription,
  useSpecificationChanges,
  useSpecifications,
} from './api/use-ai';
export type { AiJobAct, AiJobActCommand, AiJobMethod, QueueCommand, ReportCommand, StartAiCommand } from './api/use-ai-commands';
export { JOB_ACTS, consentFor, useAiJobAct, useAiStart, useQueueCommand, useReportCommand } from './api/use-ai-commands';
export type { ConsentFlow, ConsentFlowOptions } from './api/use-consent-flow';
export { useConsentFlow } from './api/use-consent-flow';
export type { SelectionEstimate, SelectionItem } from './api/use-selection-estimates';
export { useSelectionEstimates } from './api/use-selection-estimates';
export type { DownloadTarget } from './api/use-download';
export { useDownload } from './api/use-download';

export {
  AI_CEILING_LABELS,
  AI_CERTAINTY_LABELS,
  AI_CONFIDENCE_LABELS,
  AI_EXCLUDE_REASON_LABELS,
  AI_JOB_PARTIAL_LABEL,
  AI_JOB_STATE_LABELS,
  AI_METHOD_LABELS,
  AI_PAUSE_ADVICE,
  AI_PAUSE_REASON_LABELS,
  AI_SHEET_STATE_LABELS,
  AI_SHEET_STATE_TONES,
  AI_SIDE_WORDS,
  AI_TEXT_NOTE,
  AI_TIER_LABELS,
  AI_TIER_TITLES,
  LAUNCH_ENTRY_STATE_LABELS,
  LAUNCH_QUEUE_STATE_LABELS,
  PAIR_DECISION_LABELS,
  PAIR_QUESTION_KIND_LABELS,
  RECORDED_LABEL,
  RECORDED_NOTE,
  REPORT_ARTIFACT_LABELS,
  REPORT_KIND_LABELS,
  REPORT_KIND_TITLES,
  REPORT_SOURCE_LABELS,
  REPORT_STAGE_LABELS,
  REPORT_STATE_LABELS,
  REVIEW_SHEET_KIND_LABELS,
  REVIEW_SHEET_KIND_TITLES,
  SPEC_CHANGE_KIND_LABELS,
  SPEC_FIELD_LABELS,
  SPEC_METHOD_LABELS,
  SPEC_METHOD_TITLES,
  SPEC_PHASE_LABELS,
  SPEC_REASON_UNDESCRIBED,
  SPEC_REASON_WORDS,
  SPEC_STATE_LABELS,
  UNCONFIRMED_LABEL,
  UNIT_MARKS,
  aiJobStateLabel,
  descriptionHasContent,
  isRecordedRoute,
  pauseNeedsConsent,
  specFieldLabel,
  specReasonWords,
} from './model/ai-words';
export type { ConsentKind, EstimateLine } from './model/estimate';
export {
  BILLING_LABELS,
  BLOCKED_SENTENCES,
  CEILINGS_LINE,
  CONFIRM_LABELS,
  CONSENT_LINES,
  NOTHING_TO_SEND_SENTENCE,
  NOT_METERED_LABEL,
  NOT_METERED_TITLE,
  NO_CEILINGS_LINE,
  RECONSENT_NOTE,
  RESTART_CONFIRM_LABELS,
  RETRY_FAILED_LABEL,
  agreementStands,
  ceilingsLine,
  consentKindOf,
  consentOf,
  costLine,
  estimateLines,
  formatUsd,
  isBlocked,
  isNotMetered,
  isNothingToSend,
  megabytes,
  reconsentRequired,
} from './model/estimate';
export type { AiStepAction, AiStepActionId, AiStepCell, AiStepFacts, ColumnState, QueueBadge, SelectContext, SheetTotals } from './model/ai-steps';
export {
  COLUMN_SELECT_TITLE,
  NOT_NEEDED_TITLE,
  ROW_SELECT_TITLE,
  aiStepActions,
  aiStepCell,
  aiStepState,
  canSelect,
  columnState,
  pairNote,
  queueBadge,
  reportNote,
  selectionKey,
  sheetTotals,
  sheetsNote,
} from './model/ai-steps';
export {
  AI_QUEUE_TITLE,
  LAUNCH_QUEUE_TITLE,
  LAUNCH_QUEUE_TONES,
  PREVIEW_LIMIT,
  QUEUE_ENQUEUE_LABEL,
  SELECTION_CLEAR_LABEL,
  SELECTION_RUN_LABEL,
  SELECTION_RUN_TITLE,
  aiQueueItemLine,
  aiQueueName,
  aiQueueShown,
  aiQueueText,
  canRemoveEntry,
  entryLabel,
  launchControls,
  launchCountsLine,
  launchQueueShown,
  previewLines,
  queueStepLabel,
  selectionTitle,
} from './model/launch-queue';
export type { HintMark } from './model/hints';
export { MOON, hintMark, hintText, hintTitle, hintsFor, newestHint } from './model/hints';
export {
  canCancelReport,
  canContinueReport,
  canDeleteReport,
  canPrepareClientReport,
  canRebuildReport,
  canStartReport,
  coverageLine,
  coveragePercent,
  hasArtifact,
  isLiveReport,
  pdfName,
  positionsLine,
  reportKindLine,
  reportProgressLine,
  sourceMdName,
  specMethodsLine,
  specSheetsLine,
  unitMark,
  usageLine,
} from './model/report-view';
export type { Evidence } from './model/description-view';
export { copyText, evidenceCounter, evidenceOf, focusIndexOf, leadLine, nowText, stepIndex, wasText } from './model/description-view';
export { AiLabel, AiText, RecordedMark } from './ui/ai-text';
export type { AiTextProps } from './ui/ai-text';
export { EstimatePanel } from './ui/estimate-panel';
export type { EstimatePanelProps } from './ui/estimate-panel';
