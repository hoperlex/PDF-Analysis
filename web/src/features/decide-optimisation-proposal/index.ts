/** Public API of the `decide-optimisation-proposal` feature (`W60-OPT-PROPOSALS-01`). */

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
  ProposalDecisionForm,
  ProposalDecisionFormView,
  normalisedComment,
} from './ui/proposal-decision-form';
