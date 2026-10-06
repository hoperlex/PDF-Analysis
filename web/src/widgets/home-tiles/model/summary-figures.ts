/**
 * The four figures the home page's summary tile shows, read off `getDashboardSummary`'s one
 * answer (`R-44`): how many projects, how many documents, how many findings still wait for a
 * decision, and how many runs.
 *
 * **Absent is not empty.** The contract promises every `Verdict` and every `RunState` as a
 * row, zero included. A figure summed over a breakdown with a row missing, repeated or not
 * recognised would be a partial count shown as a whole one, so such an answer gives no
 * figures at all and the tile says why — the same rule the dashboard's panels apply.
 */

import type { DashboardSummary } from '@/shared/api';
import { RUN_STATE_VALUES, VERDICT_VALUES } from '@/shared/api';

export interface SummaryFigures {
  readonly projects: number;
  readonly documents: number;
  readonly pendingFindings: number;
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
  const verdicts = summary.findings_by_verdict;
  const states = summary.run_activity.by_state;
  if (!namesEachOnce(verdicts.map((row) => row.verdict), VERDICT_VALUES)) return null;
  if (!namesEachOnce(states.map((row) => row.state), RUN_STATE_VALUES)) return null;

  return {
    projects: summary.documents_by_project.length,
    documents: summary.documents_by_project.reduce((sum, row) => sum + row.document_count, 0),
    // Present exactly once: `namesEachOnce` above has just said so.
    pendingFindings: verdicts
      .filter((row) => row.verdict === 'pending')
      .reduce((sum, row) => sum + row.count, 0),
    runs: states.reduce((sum, row) => sum + row.count, 0),
  };
}
