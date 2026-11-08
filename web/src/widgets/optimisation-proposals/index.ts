/** Public API of the `optimisation-proposals` widget (`W60-OPT-PROPOSALS-01`). */

export type { ProposalLayout } from './model/layout';
export {
  DEFAULT_PROPOSAL_LAYOUT,
  PROPOSAL_LAYOUTS,
  PROPOSAL_LAYOUT_LABELS,
  PROPOSAL_LAYOUT_PARAM,
  TABLE_PAGE_LIMIT,
  isProposalLayout,
  pageLimitOf,
  readProposalLayout,
  writeProposalLayout,
} from './model/layout';
export type { ExportProposalsCsvApi, ExportProposalsCsvArgs } from './model/use-export-proposals-csv';
export { useExportProposalsCsv } from './model/use-export-proposals-csv';
export type { ExportProposalsXlsxApi, ExportProposalsXlsxArgs } from './model/use-export-proposals-xlsx';
export { useExportProposalsXlsx } from './model/use-export-proposals-xlsx';
export type {
  ExportProposalsViewProps,
  OptimisationProposalsProps,
  PassListProps,
  ProposalSetChooserProps,
} from './ui/optimisation-proposals';
export {
  OptimisationByDocument,
  ExportProposalsView,
  OptimisationProposals,
  PassList,
  ProposalSetChooser,
  classifiedDocumentSets,
} from './ui/optimisation-proposals';
export type { PassSummaryProps } from './ui/pass-summary';
export { PassSummary } from './ui/pass-summary';
export type { ProposalTableProps } from './ui/proposal-table';
export { ProposalTable } from './ui/proposal-table';
export type {
  ProposalCardProps,
  ProposalDecisionLineProps,
  ProposalHistoryViewProps,
} from './ui/proposal-card';
export { ProposalCard, ProposalDecisionLine, ProposalHistoryView, namedPage } from './ui/proposal-card';
export type { ProposalSheetBlocksProps } from './ui/proposal-sheet-blocks';
export { ProposalSheetBlocks, ProposalSheetBlocksBody } from './ui/proposal-sheet-blocks';
export type {
  DecisionFilterProps,
  LayoutSwitchProps,
  ProposalHistoryPanelViewProps,
  ProposalHistoryProps,
  ProposalListProps,
  ProposalListViewProps,
  SheetDocument,
} from './ui/proposal-list';
export {
  DecisionFilter,
  LayoutSwitch,
  ProposalHistory,
  ProposalHistoryPanelView,
  ProposalList,
  ProposalListView,
} from './ui/proposal-list';
