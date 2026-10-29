/**
 * Public API of the `version-series` widget (`CMP-VC-UI-01`): the two tabs of «Сравнение версий» that read the
 * comparison of one project — the table of document sets and their steps, and the sheet matrix of one set with its
 * transitions, its draft of manual edits and its order dialog.
 *
 * The page that composes them (`_pages/version-compare`) also mounts the upload dialogs and the sheet viewer, which
 * are sibling widgets and are handed in.
 */

export type { ProjectsAndStagesProps, ProjectsAndStagesViewProps } from './ui/projects-and-stages';
export { ProjectsAndStages, ProjectsAndStagesView, clockOf } from './ui/projects-and-stages';
export type { RenderViewer, SheetsTabProps, SheetsTabViewProps, ViewerSlotProps } from './ui/sheets-tab';
export { ModuleOffState, PairViewerSlot, SheetsTab, SheetsTabView } from './ui/sheets-tab';
export type { FailureStateProps } from './ui/module-state';
export { CommandRefusal, FailureState, MODULE_UNAVAILABLE_TITLE } from './ui/module-state';
export type { TransitionSummaryProps } from './ui/transition-summary';
export {
  CHOOSE_TWO_NOTE,
  NOT_COMPARED_NOTE,
  NO_SERIES_NOTE,
  TransitionSummary,
} from './ui/transition-summary';
export type { SheetMatrixProps } from './ui/sheet-matrix';
export { NO_PAIR_FOR_CHANGES, SheetMatrix } from './ui/sheet-matrix';
export type { MatrixCellViewProps } from './ui/matrix-cell';
export { MatrixCellView, Thumb } from './ui/matrix-cell';
export type { DraftPanelProps, EditHistoryProps } from './ui/draft-panel';
export { DraftPanel, EditHistory, ORPHANED_NOTE } from './ui/draft-panel';
export type { MatrixStateProps } from './ui/matrix-state';
export { MatrixState } from './ui/matrix-state';
export type { OrderRow, VersionOrderDialogProps, VersionOrderDialogViewProps } from './ui/version-order-dialog';
export { VersionOrderDialog, VersionOrderDialogView } from './ui/version-order-dialog';
