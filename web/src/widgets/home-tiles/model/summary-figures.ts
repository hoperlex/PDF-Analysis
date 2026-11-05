/**
 * The four figures the home page's summary tile shows, read off `getDashboardSummary`'s one
 * answer (`R-44`): how many projects, how many documents, how many findings still wait for a
 * decision, and how many runs.
 *
 * **The findings figure is the server's, not a sum of the verdict panel** (`UI-PARITY-P0B`,
 * `R-150q`). `awaiting_decision_findings` counts the undecided findings in the result runs of
 * the current versions. The verdict breakdown counts every finding of every run, «за всё
 * время», so summing its `pending` row here would show history under the label of today's work.
 *
 * **Absent is not empty.** The contract promises every `RunState` as a row, zero included. A
 * figure summed over a breakdown with a row missing, repeated or not recognised would be a
 * partial count shown as a whole one, and a findings figure that is not a whole number is not
 * a zero: such an answer gives no figures at all and the tile says why — the same rule the
 * dashboard's panels apply.
 */

import type { DashboardSummary } from '@/shared/api';
import { RUN_STATE_VALUES } from '@/shared/api';

export interface SummaryFigures {
  readonly projects: number;
  readonly documents: number;
  /** Undecided findings in the result runs of the current versions (`awaiting_decision_findings`). */
  readonly awaitingDecisionFindings: number;
  readonly runs: number;
}

/** True when `rows` names every member of `values` exactly once and nothing else. */
function namesEachOnce(rows: readonly unknown[], values: readonly string[]): boolean {
  if (rows.length !== values.length) return false;
  const seen = new Set<unknown>(rows);
  return seen.size === values.length && values.every((value) => seen.has(value));
}

/** The figures, or `null` when a breakdown the figures are summed over is incomplete. */
export function summaryFigures(summary: DashboardSummary): SummaryFigures | null {
  const states = summary.run_activity.by_state;
  if (!namesEachOnce(states.map((row) => row.state), RUN_STATE_VALUES)) return null;
  const awaiting = summary.awaiting_decision_findings;
  if (!Number.isInteger(awaiting) || awaiting < 0) return null;

  return {
    projects: summary.documents_by_project.length,
    documents: summary.documents_by_project.reduce((sum, row) => sum + row.document_count, 0),
    awaitingDecisionFindings: awaiting,
    runs: states.reduce((sum, row) => sum + row.count, 0),
  };
}
