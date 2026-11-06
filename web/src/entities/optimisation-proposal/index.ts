/** Public API of the `optimisation-proposal` entity (`W60-OPT-PROPOSALS-01`): passes and proposals. */

export type { AcceptedProposalsFilter } from './api/use-optimisation-proposals';
export {
  ACCEPTED_PAGE_LIMIT,
  PROPOSAL_PAGE_LIMIT,
  acceptedProposalsQueryOptions,
  optimisationPassesQueryOptions,
  optimisationProposalsQueryOptions,
  proposalDecisionsQueryOptions,
  useAcceptedOptimisationProposals,
  useOptimisationPasses,
  useOptimisationProposals,
  useProposalDecisions,
} from './api/use-optimisation-proposals';
export {
  ANALOG_BASIS_LABELS,
  DECISION_EVENT_LABELS,
  DECISION_STATES,
  DECISION_STATE_LABELS,
  MATCH_BASIS_LABELS,
  VENDOR_LIST_SCOPE_LABELS,
  VERDICT_LABELS,
  describeCounts,
  describeProvenance,
  describeQuantity,
  describeSaving,
  formatAmount,
  formatDecimal,
  proposalsCsvFileName,
  proposalsXlsxFileName,
} from './model/presentation';
export {
  COMMENT_REQUIRED_TEXT,
  COMMENT_TOO_LONG_TEXT,
  NOTHING_TO_REVOKE_TEXT,
  PASS_REFUSAL_TEXT,
  decideFailureMessage,
  startPassFailureMessage,
} from './model/failure';
