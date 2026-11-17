/** Public API of the `decide-optimisation-proposal` feature (`W60-OPT-PROPOSALS-01`, `UIP-S09-03`). */

export type { DecideOptimisationProposalCommand } from './model/use-decide-optimisation-proposal';
export {
  decisionSignature,
  useDecideOptimisationProposal,
} from './model/use-decide-optimisation-proposal';

export type {
  ProposalDecisionFormProps,
  ProposalDecisionFormViewProps,
} from './ui/proposal-decision-form';
export {
  MORE_DECISIONS_LABEL,
  ProposalDecisionForm,
  ProposalDecisionFormView,
  RECORDED_TEXT,
  REVISE_NEEDS_REASON_TEXT,
  decisionInForce,
  normalisedComment,
} from './ui/proposal-decision-form';
