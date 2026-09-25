/**
 * Findings by verdict, computed over one loaded page of `listDecisions`.
 *
 * `listDecisions` returns one row per **event**, not per finding — `widgets/knowledge-base`
 * says so and a finding the reviewer returned to carries several rows, all sharing the
 * same `current_verdict` and `category` (they are properties of the finding, projected
 * onto every event row). Tallying rows directly would count that finding once per event it
 * has, which is not "findings by verdict" — it is "decision events by the verdict that
 * happens to stand now". This module dedupes by `finding_uid` first.
 *
 * **What this can never show.** `listDecisions` is the ledger of *recorded* decisions: a
 * finding nobody has ever judged carries no event and never appears here, at any page size.
 * So a `pending` count from this module is "commented on or reverted, still undecided" —
 * never "never looked at". The widget's caption says so; this module does not invent the
 * distinction by fabricating a fourth verdict.
 */

import type { DecisionRecord, FindingCategory, Verdict } from '@/shared/api';

export interface VerdictTally {
  /** Distinct findings this page's events belong to, after dedup. */
  readonly findingCount: number;
  readonly byVerdict: Readonly<Record<Verdict, number>>;
  readonly byCategory: Readonly<Record<FindingCategory, number>>;
}

const ZERO_BY_VERDICT: Record<Verdict, number> = {
  pending: 0,
  accepted: 0,
  rejected: 0,
  needs_manual_review: 0,
};

const ZERO_BY_CATEGORY: Record<FindingCategory, number> = {
  internal_contradiction: 0,
  explicit_placeholder: 0,
};

export function tallyVerdicts(records: readonly DecisionRecord[]): VerdictTally {
  // One entry per finding. `current_verdict` and `category` are identical across every
  // row that shares a `finding_uid`, so the last write for a key carries the same value
  // any other row of that finding would have.
  const byFinding = new Map<string, DecisionRecord>();
  for (const record of records) {
    byFinding.set(record.finding_uid, record);
  }

  const byVerdict = { ...ZERO_BY_VERDICT };
  const byCategory = { ...ZERO_BY_CATEGORY };
  for (const record of byFinding.values()) {
    byVerdict[record.current_verdict] += 1;
    byCategory[record.category] += 1;
  }

  return { findingCount: byFinding.size, byVerdict, byCategory };
}
