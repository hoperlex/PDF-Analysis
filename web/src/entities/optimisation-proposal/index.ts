/** Public API of the `optimisation-proposal` entity (`W60-OPT-PROPOSALS-01`): passes and proposals. */

export {
  PROPOSAL_PAGE_LIMIT,
  optimisationPassesQueryOptions,
  optimisationProposalsQueryOptions,
  proposalDecisionsQueryOptions,
  useOptimisationPasses,
  useOptimisationProposals,
  useProposalDecisions,
} from './api/use-optimisation-proposals';
export {
  ANALOG_BASIS_LABELS,
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
} from './model/presentation';
export {
  COMMENT_REQUIRED_TEXT,
  COMMENT_TOO_LONG_TEXT,
  PASS_REFUSAL_TEXT,
  decideFailureMessage,
  startPassFailureMessage,
} from './model/failure';
