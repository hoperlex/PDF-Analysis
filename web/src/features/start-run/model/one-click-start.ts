/**
 * The rules of the one-button start (`RUN-START-ONE-01a`, plan v3 §8): what an estimate means for the
 * agreement, and which answers of the server send the person back to a fresh estimate.
 *
 * Pure: shapes and arithmetic. `./use-run-cost-approval.ts` holds the sequence (estimate, agree, send).
 *
 * **The click is the agreement when nothing can be charged.** An estimate with `billing: unmetered`
 * is the connection that the application does not bill; its estimated cost is 0 by construction, and
 * the server accepts `ceiling_micros: 0` for it. Pressing «Запустить» then sends the consent of that
 * very estimate (`confirmed: true`) with no second step. Anything else (`metered`) shows its figure and
 * asks once.
 *
 * **«Без денежного потолка» (`relaxed_limits`) never skips the question when it can charge.** The
 * ceiling of such a start is `0` by the contract (`uncapped_stats`), and a metered one is exactly the
 * start that spends without an application cap, so it always shows the dialog.
 */

import type { RunCostEstimate, RunCostEstimateRequest, VersionUid } from '@/shared/api';
import { ApiError } from '@/shared/api';
import { ceilingMicros, microsAsUsd, usableCostEstimate } from '@/shared/ui';

import type { RunCostConsent } from './start-run-intent';

/** `409 conflict` of a start whose digest is no longer the one the server computes. */
export const ESTIMATE_STALE_REASON = 'run_cost_estimate_stale';
/** `422 analysis_input_invalid`: the model, rate or revision the estimate was bound to has changed. */
export const BINDING_CHANGED_REASON = 'cost_estimate_binding_changed';

/** Whether this estimate can charge anything at all. Only `unmetered` cannot. */
export function chargesMoney(estimate: RunCostEstimate): boolean {
  return estimate.billing !== 'unmetered';
}

/** The body of the estimate request: the version and the one optional flag; never a selector. */
export function estimateRequest(versionUid: VersionUid, relaxed: boolean): RunCostEstimateRequest {
  return { version_uid: versionUid, ...(relaxed ? { relaxed_limits: true } : {}) };
}

/** Whether an answer is the estimate of this version for this kind of start, and can be agreed to. */
export function estimateAnswers(estimate: RunCostEstimate, versionUid: VersionUid, relaxed: boolean): boolean {
  return usableCostEstimate(estimate) && estimate.scope === 'run' && estimate.version_uid === versionUid
    && estimate.relaxed_limits === relaxed;
}

/** The least a ceiling may be: what the run is estimated to cost, and never nothing when it is billed. */
export function ceilingFloor(estimate: RunCostEstimate): number {
  return Math.max(chargesMoney(estimate) ? 1 : 0, estimate.estimated_cost_micros);
}

/**
 * The consent a click gives by itself for an estimate that charges nothing: the estimate's own digest and
 * ceiling (0 for an unmetered one), and 0 for a start without an application cap.
 */
export function automaticConsent(estimate: RunCostEstimate, relaxed: boolean): RunCostConsent {
  return {
    estimate_digest: estimate.estimate_digest,
    ceiling_micros: relaxed ? 0 : estimate.recommended_ceiling_micros,
    confirmed: true,
  };
}

/** What the dialog's ceiling field holds when it opens: the recommended ceiling, or `0` without a cap. */
export function initialCeiling(estimate: RunCostEstimate, relaxed: boolean): string {
  return relaxed ? '0' : microsAsUsd(estimate.recommended_ceiling_micros);
}

/** The consent the dialog's «Запустить» gives, or `null` while its ceiling cannot be one. */
export function dialogConsent(estimate: RunCostEstimate, relaxed: boolean, ceiling: string): RunCostConsent | null {
  const micros = relaxed ? 0 : ceilingMicros(ceiling, ceilingFloor(estimate));
  return micros === null ? null : { estimate_digest: estimate.estimate_digest, ceiling_micros: micros, confirmed: true };
}

/**
 * The server saying that what the person agreed to is not what it would run: the digest is stale, or the
 * accepted model, rate or revision has changed. The answer to both is a fresh estimate, shown again.
 */
export function estimateChanged(error: unknown): boolean {
  if (!(error instanceof ApiError)) return false;
  return (error.errorCode === 'conflict' && error.details.conflict_reason === ESTIMATE_STALE_REASON)
    || (error.errorCode === 'analysis_input_invalid' && error.details.reason === BINDING_CHANGED_REASON);
}

/** A comparison PDF has no portal companion and this server does not analyse it as a section. */
export function comparisonOnlyRefusal(error: unknown): boolean {
  return error instanceof ApiError && error.errorCode === 'analysis_input_invalid'
    && error.details.reason === 'comparison_only_version';
}
