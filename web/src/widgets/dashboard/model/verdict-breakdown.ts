/**
 * Findings by verdict, computed over `getDashboardSummary`'s `findings_by_verdict`.
 *
 * `VerdictCount`'s own doc comment says every member of `Verdict` is present, at zero when
 * nothing reached it — "a verdict nobody has recorded is `count: 0`, not an absent row".
 *
 * **This module no longer fills a gap it did not compute.** It used to seed all four
 * verdicts at zero and overwrite from the wire, calling the result a defensive merge — but
 * a member the response omits is the server not saying, not the server saying zero, and
 * defaulting it is exactly the invented number `R-23`'s addendum names and the silent
 * fallback `AGENTS.md` §4 forbids (`docs/program/reviews/W46-JUDGE-Y.md` §5, `Y5-a`;
 * `docs/program/reviews/W46-JUDGE-X.md` §`X2-a`). It also used to drop, with no signal, a
 * row whose verdict the closed set does not recognise.
 *
 * So this function checks the closed vocabulary instead of filling it: all four members,
 * once each — anything short of exactly that (a missing member, a repeated one, or one
 * this module does not recognise) is reported as `{ ok: false }`, and it is the caller's
 * job to show that as a fault rather than as a number.
 */

import type { Verdict, VerdictCount } from '@/shared/api';
import { VERDICT_VALUES } from '@/shared/api';

export type VerdictBreakdownResult =
  | { readonly ok: true; readonly byVerdict: Readonly<Record<Verdict, number>> }
  /** The response did not carry exactly the closed vocabulary: a member missing, repeated, or unrecognised. */
  | { readonly ok: false };

export function summarizeVerdictBreakdown(rows: readonly VerdictCount[]): VerdictBreakdownResult {
  const byVerdict = new Map<Verdict, number>();
  for (const row of rows) {
    if (!VERDICT_VALUES.includes(row.verdict) || byVerdict.has(row.verdict)) {
      return { ok: false };
    }
    byVerdict.set(row.verdict, row.count);
  }
  if (byVerdict.size !== VERDICT_VALUES.length) return { ok: false };

  return { ok: true, byVerdict: Object.fromEntries(byVerdict) as Record<Verdict, number> };
}
