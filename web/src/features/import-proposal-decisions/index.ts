/** Public API of the `import-proposal-decisions` feature: decisions loaded back from a pass's own workbook (`UI-B-15`). */

export { useImportProposalDecisions } from './model/use-import-proposal-decisions';
export type { ImportProposalDecisionsViewProps } from './ui/import-proposal-decisions';
export {
  ImportProposalDecisions,
  ImportProposalDecisionsView,
  PROPOSAL_IMPORT_MAX_BYTES,
  PROPOSAL_IMPORT_REFUSAL_LABELS,
  importProposalFailure,
} from './ui/import-proposal-decisions';
