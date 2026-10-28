/**
 * Public API of the `version-comparison` entity (`COMPARE-PERSISTED-SUMMARY-01`): an expert's
 * approval of a sheet pairing and the evidence of the approved pairs.
 *
 * The comparison read itself stays in `document-version`; this entity holds what the stored
 * approvals add: who may approve, what the state of their evidence means, the two commands and
 * the refusals in Russian, and the controls on a sheet row.
 */

export type { PairingConflictReason, PairingFailure, PairingFailureKind } from './model/pairing';
export {
  EVIDENCE_STATE_TEXT,
  LINK_STATE_TEXT,
  PAIRING_CONFLICT_TEXT,
  PAIRING_NOT_PERMITTED_DETAIL,
  approvalOf,
  canApproveSheetPairing,
  isApprovablePair,
  pairingFailure,
} from './model/pairing';

export type {
  ApproveSheetPairingCommand,
  WithdrawSheetPairingCommand,
} from './api/use-sheet-pairing';
export {
  approveSignature,
  useApproveSheetPairing,
  useWithdrawSheetPairing,
  withdrawSignature,
} from './api/use-sheet-pairing';

export type { SummaryFailure, SummaryFailureKind } from './model/summary';
export {
  RECORDED_MODE_TEXT,
  SUMMARY_CONFLICT_TEXT,
  SUMMARY_NOT_CURRENT_TEXT,
  SUMMARY_NOT_PERMITTED_DETAIL,
  SUMMARY_NOT_SEALED_TEXT,
  SUMMARY_REJECTION_TEXT,
  SUMMARY_UNAVAILABLE_DETAIL,
  canOfferSummary,
  citationText,
  citedChange,
  summaryFailure,
} from './model/summary';

export type { GenerateComparisonSummaryCommand } from './api/use-comparison-summary';
export { summarySignature, useGenerateComparisonSummary } from './api/use-comparison-summary';

export type { SummaryView } from './ui/comparison-summary';
export { ComparisonSummarySection, ComparisonSummaryView } from './ui/comparison-summary';
export type { ComparisonSummaryViewProps } from './ui/comparison-summary';

export type {
  PairingView,
  SheetPairingControlsProps,
  SheetPairingControlsViewProps,
} from './ui/sheet-pairing-controls';
export { SheetPairingControls, SheetPairingControlsView } from './ui/sheet-pairing-controls';
