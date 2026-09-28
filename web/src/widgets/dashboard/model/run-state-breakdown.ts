/**
 * Run counts by state, computed over `getDashboardSummary`'s `run_activity.by_state`.
 *
 * `RunStateCount`'s own doc comment says every member of `RunState` is present, "for the
 * same reason `VerdictCount` states" — so this module holds the same rule
 * `verdict-breakdown.ts` does, for the same reason: eight states, once each, is the
 * server's promise, not something this module is free to approximate.
 *
 * **Two shapes of the same fault, both closed off here.** A response that carries only
 * some of the eight states used to render the ones it carried and quietly drop the rest —
 * not a false number, but a hidden true one, and indistinguishable on screen from "the
 * other states are genuinely at zero". And a response carrying a state this module does
 * not recognise used to vanish with no signal at all
 * (`docs/program/reviews/W46-JUDGE-X.md` §`X2-a`, the `escalated`/`ZZ` mutation). Neither
 * is a member reaching a different number — both are a response that is not the whole
 * closed vocabulary, so both return `{ ok: false }` here, once, rather than being told
 * apart by two different repairs.
 */

import type { RunState, RunStateCount } from '@/shared/api';
import { RUN_STATE_VALUES } from '@/shared/api';

export type RunStateBreakdownResult =
  | {
      readonly ok: true;
      readonly byState: Readonly<Record<RunState, number>>;
      readonly totalRuns: number;
    }
  /** The response did not carry exactly the closed vocabulary: a member missing, repeated, or unrecognised. */
  | { readonly ok: false };

export function summarizeRunStateBreakdown(rows: readonly RunStateCount[]): RunStateBreakdownResult {
  const byState = new Map<RunState, number>();
  for (const row of rows) {
    if (!RUN_STATE_VALUES.includes(row.state) || byState.has(row.state)) {
      return { ok: false };
    }
    byState.set(row.state, row.count);
  }
  if (byState.size !== RUN_STATE_VALUES.length) return { ok: false };

  const totalRuns = [...byState.values()].reduce((sum, count) => sum + count, 0);
  return { ok: true, byState: Object.fromEntries(byState) as Record<RunState, number>, totalRuns };
}
