/**
 * Findings by verdict, computed over `getDashboardSummary`'s `findings_by_verdict`.
 *
 * `VerdictCount`'s own doc comment says every member of `Verdict` is present, at zero when
 * nothing reached it. This module does not simply trust the array's length and order: it
 * merges onto the closed `VERDICT_VALUES` vocabulary the same defensive way
 * `section-breakdown.ts` merges onto `PROJECT_SECTIONS` — a row a future response happens
 * to omit reads as its true zero, in the contract's own declared order, rather than
 * silently dropping that verdict's row from the screen.
 */

import type { Verdict, VerdictCount } from '@/shared/api';
import { VERDICT_VALUES } from '@/shared/api';

const ZERO_BY_VERDICT: Readonly<Record<Verdict, number>> = Object.fromEntries(
  VERDICT_VALUES.map((verdict) => [verdict, 0]),
) as Record<Verdict, number>;

export function summarizeVerdictBreakdown(
  rows: readonly VerdictCount[],
): Readonly<Record<Verdict, number>> {
  const byVerdict: Record<Verdict, number> = { ...ZERO_BY_VERDICT };
  for (const row of rows) {
    if (row.verdict in byVerdict) byVerdict[row.verdict] = row.count;
  }
  return byVerdict;
}
