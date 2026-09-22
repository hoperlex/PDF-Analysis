/**
 * Public API of the `expert-decision` entity.
 *
 * The append-only ledger and its projection, the one-key-per-intent rule, and the verdict
 * badge. Nothing here writes: `features/record-verdict` and `features/append-comment` own
 * the mutation.
 */

export type { VerdictProjection } from './model/ledger';
export {
  appendEvent,
  compareEvents,
  isVerdictBearing,
  orderEvents,
  projectVerdict,
  reconcile,
} from './model/ledger';

export { decisionCacheKeys } from './model/cache';

export type { DecisionJournalQuery } from './api/use-decision-journal';
export { JOURNAL_PAGE_LIMIT, useDecisionJournal } from './api/use-decision-journal';

/** The Russian label for a verdict, so no consumer renders the contract value as prose. */
export { VERDICT_LABELS } from './ui/verdict-badge';

export type { IntentRecord } from './model/intent';
export { intentSignature, resolveIntentKey } from './model/intent';

export type { VerdictBadgeProps } from './ui/verdict-badge';
export { VerdictBadge } from './ui/verdict-badge';
