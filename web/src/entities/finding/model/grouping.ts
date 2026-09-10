/**
 * Grouping a finding page by category, in the contract's declared order.
 *
 * The order comes from the generated `FINDING_CATEGORY_VALUES`, never from a hand-written
 * list and never from whatever order the server happened to return: a reviewer working
 * through two categories should find them in the same places on every run.
 *
 * `P2-AI-01` declares exactly two categories for PC-01. Nothing here hardcodes that
 * number — a third category added to the contract shows up as a third group.
 */

import type { Finding, FindingCategory, FindingDetail } from '@/shared/api';
import { FINDING_CATEGORY_VALUES } from '@/shared/api';

export interface FindingGroup<T extends Finding | FindingDetail> {
  readonly category: FindingCategory;
  readonly findings: readonly T[];
}

/**
 * Group by category, preserving the server's ordering inside each group.
 *
 * A category with no findings is omitted rather than rendered as an empty heading: an
 * empty group tells the reviewer nothing and an empty list already has its own state.
 */
export function groupByCategory<T extends Finding | FindingDetail>(
  findings: readonly T[],
): readonly FindingGroup<T>[] {
  const groups: FindingGroup<T>[] = [];

  for (const category of FINDING_CATEGORY_VALUES) {
    const inCategory = findings.filter((finding) => finding.category === category);
    if (inCategory.length === 0) continue;
    groups.push({ category, findings: inCategory });
  }

  return groups;
}

/** Total across groups. Used by the list header so it does not re-count the raw page. */
export function countGrouped<T extends Finding | FindingDetail>(
  groups: readonly FindingGroup<T>[],
): number {
  return groups.reduce((total, group) => total + group.findings.length, 0);
}
