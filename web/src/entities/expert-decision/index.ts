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

export { KNOWLEDGE_BASE_SCREEN } from './model/knowledge-base-screen';

export type { DecisionJournalQuery, DecisionVerdictTotals } from './api/use-decision-journal';
export {
  JOURNAL_PAGE_LIMIT, useDecisionJournal, useDecisionStatusTotals, useDecisionVerdictTotals, useKnowledgeBaseJournal,
  useProposalDecisionJournal,
} from './api/use-decision-journal';

/** The Russian label for a verdict, so no consumer renders the contract value as prose. */
export { VERDICT_LABELS } from './ui/verdict-badge';

/** The Russian heading for a finding's category, as the knowledge base shows it. */
export { CATEGORY_LABELS } from './model/category-labels';

/** «N записей», the journal's `total` with its noun in agreement. */
export { recordCountLabel } from './model/record-count';

export type { IntentRecord } from './model/intent';
export { intentSignature, resolveIntentKey } from './model/intent';

export type { VerdictBadgeProps } from './ui/verdict-badge';
export { VerdictBadge } from './ui/verdict-badge';

/** `UI-A-73`: «↩ Перенесено из V2», the mark of a decision carried over from an earlier version. */
export { carriedFromMark } from './model/carried-from';
export type { CarriedMarkProps } from './ui/carried-mark';
export { CarriedMark } from './ui/carried-mark';

/**
 * `UIP-S06-01`: the decision field (✓, ✕, «Причина», the line of the last press, a slot for a screen's further actions) and
 * the one-glyph verdict mark (✓ green, ✕ red, a dash). Pure markup: the screen that uses them sends the decision.
 */
export type { DecisionIntent, DecisionNote, DecisionReasonControlProps } from './ui/decision-reason-control';
export { DecisionReasonControl } from './ui/decision-reason-control';
export type { VerdictMarkProps } from './ui/verdict-mark';
export { VerdictMark } from './ui/verdict-mark';
