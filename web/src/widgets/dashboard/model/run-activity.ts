/**
 * Run activity and spend, computed over a set of `RunStatus` readings the widget's walk
 * has collected.
 *
 * Pure and framework-free. `entities/audit-run`'s `runCost()` already draws the one line
 * that matters for money on this screen — *"absent and a reported zero are different
 * facts and are kept different"*, `RunStatus.cost_micros`'s own contract description says
 * a run that made no provider call carries no cost field at all. This module reuses that
 * classifier per run rather than re-deciding it, and extends the SAME rule `R-14` put on
 * one run's `cost_basis` to a set of them: the aggregate is `measured` only if every run
 * that contributed a reported cost was itself `measured`, and `estimated` the moment one
 * is not.
 */

import type { CostBasis, RunState, RunStatus } from '@/shared/api';
import { runCost } from '@/entities/audit-run';

const ZERO_BY_STATE: Record<RunState, number> = {
  created: 0,
  queued: 0,
  running: 0,
  validating: 0,
  published: 0,
  partial: 0,
  failed: 0,
  cancelled: 0,
};

export interface RunActivitySummary {
  readonly runCount: number;
  readonly byState: Readonly<Record<RunState, number>>;
  /** Sum of `cost_micros` over runs whose reading was `reported`. Never over `absent` ones. */
  readonly reportedCostMicros: number;
  readonly modelCallCount: number;
  /** How many runs contributed to `reportedCostMicros`. */
  readonly runsWithReportedCost: number;
  /** Made no provider call at all — a different fact from spending zero. */
  readonly runsWithAbsentCost: number;
  /** Carried a cost field the contract's own invariant says should not be possible. */
  readonly runsWithUnreadableCost: number;
  /** `null` when no run in scope reported a cost at all — there is nothing to grade. */
  readonly costBasis: CostBasis | null;
}

export function summarizeRunActivity(runs: readonly RunStatus[]): RunActivitySummary {
  const byState = { ...ZERO_BY_STATE };
  let reportedCostMicros = 0;
  let modelCallCount = 0;
  let runsWithReportedCost = 0;
  let runsWithAbsentCost = 0;
  let runsWithUnreadableCost = 0;
  let sawEstimated = false;
  let sawMeasured = false;

  for (const run of runs) {
    byState[run.state] += 1;

    const reading = runCost(run);
    switch (reading.kind) {
      case 'reported':
        reportedCostMicros += reading.micros;
        modelCallCount += reading.callCount;
        runsWithReportedCost += 1;
        if (reading.basis === 'estimated') sawEstimated = true;
        else if (reading.basis === 'measured') sawMeasured = true;
        break;
      case 'absent':
        runsWithAbsentCost += 1;
        break;
      case 'unreadable':
        runsWithUnreadableCost += 1;
        break;
    }
  }

  const costBasis: CostBasis | null =
    runsWithReportedCost === 0 ? null : sawEstimated ? 'estimated' : sawMeasured ? 'measured' : null;

  return {
    runCount: runs.length,
    byState,
    reportedCostMicros,
    modelCallCount,
    runsWithReportedCost,
    runsWithAbsentCost,
    runsWithUnreadableCost,
    costBasis,
  };
}
