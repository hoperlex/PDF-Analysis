/**
 * Starting several documents at once (`R-151c`), as the original's «Запустить аудит» over a selection.
 *
 * The owner ruled one dialog with every estimate and one consent for the batch, while the server still records a
 * consent per run. So each version is estimated on its own (`estimateRunCost`, the same request a single start
 * makes), the panel shows each estimate and the total, and the one agreement covers exactly those estimates: each
 * run is then started with its own consent (its estimate's digest and its recommended ceiling) under its own
 * idempotency key. A batch start chooses no executor, preset or group: it follows the route, as a single start
 * does when nothing is chosen.
 *
 * Pure: the shapes and the arithmetic. The hook (`use-batch-start.ts`) sends.
 */

import type { RunCostEstimate, RunStatus, VersionUid } from '@/shared/api';
import { usableCostEstimate } from '@/shared/ui';

import type { RunCostConsent } from './start-run-intent';

export interface BatchEntry {
  readonly versionUid: VersionUid;
  /** What the panel calls the document. */
  readonly title: string;
}

export type BatchEstimate =
  | { readonly kind: 'pending' }
  | { readonly kind: 'ready'; readonly estimate: RunCostEstimate }
  | { readonly kind: 'failed'; readonly text: string };

export type BatchOutcome =
  | { readonly kind: 'sending' }
  | { readonly kind: 'started'; readonly run: RunStatus }
  | { readonly kind: 'refused'; readonly text: string };

/** The least a metered run may be capped at: what it is estimated to cost, and never nothing. */
export function minimumCeiling(estimate: RunCostEstimate): number {
  return Math.max(estimate.billing === 'metered' ? 1 : 0, estimate.estimated_cost_micros);
}

/** The consent one run of the batch is started with: its estimate, capped at its recommended ceiling. */
export function batchConsent(estimate: RunCostEstimate): RunCostConsent {
  return {
    estimate_digest: estimate.estimate_digest,
    ceiling_micros: Math.max(minimumCeiling(estimate), estimate.recommended_ceiling_micros),
    confirmed: true,
  };
}

/** Whether an estimate answered for this version can be agreed to. */
export function estimateFits(estimate: RunCostEstimate, versionUid: VersionUid): boolean {
  return usableCostEstimate(estimate) && estimate.scope === 'run' && estimate.version_uid === versionUid
    && estimate.relaxed_limits === false;
}

/**
 * Whether every estimate that is ready charges nothing (`billing: unmetered`), and there is at least one.
 * Such a batch needs no separate agreement: its one button is the confirmation, and the list shows 0
 * (`RUN-START-ONE-01a`, the single start's rule applied to the batch).
 */
export function batchIsFree(estimates: readonly BatchEstimate[]): boolean {
  const ready = estimates.filter((item) => item.kind === 'ready');
  return ready.length > 0 && ready.every((item) => item.estimate.billing === 'unmetered');
}

export interface BatchTotals {
  readonly ready: number;
  readonly pending: number;
  readonly failed: number;
  /** The estimated cost of the ready runs, in micro-dollars. */
  readonly costMicros: number;
  /** What the one agreement allows them to spend at most: the sum of their ceilings. */
  readonly ceilingMicros: number;
}

export function batchTotals(estimates: readonly BatchEstimate[]): BatchTotals {
  let ready = 0;
  let pending = 0;
  let failed = 0;
  let costMicros = 0;
  let ceilingMicros = 0;
  for (const item of estimates) {
    if (item.kind === 'pending') pending += 1;
    else if (item.kind === 'failed') failed += 1;
    else {
      ready += 1;
      costMicros += item.estimate.estimated_cost_micros;
      ceilingMicros += batchConsent(item.estimate).ceiling_micros;
    }
  }
  return { ready, pending, failed, costMicros, ceilingMicros };
}
