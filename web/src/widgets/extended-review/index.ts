export { ExtendedReview, procedureReasonSentence } from './ui/extended-review';
export { ExtendedReviewSummary } from './ui/extended-review-summary';
export { ReviewCandidates, ReviewCandidateTable } from './ui/review-candidates';
export { CandidateNormAdvice } from './ui/candidate-norm-advice';
export { CRITIC_QUEUES, ObservationList, criticQueueCounts } from './ui/observation-list';
export { CRITIC_QUEUE_NOTES, queueAfterKey } from './ui/critic-queues';
export { extendedReviewKey, useExtendedReviewReading } from './ui/extended-review-reading';

// `F8-WEB`: the critic's advice for a finding that stands on portal blocks, in one line of its card.
export type { AdviceSubject, CandidateAdvice } from './model/candidate-advice';
export { ADVICE_EXPLANATION_LIMIT, adviceForFinding, adviceLine, candidateOfFinding } from './model/candidate-advice';
export { CriticAdviceLine, CriticAdviceView } from './ui/critic-advice-line';
