/**
 * What a run reading means, as pure functions.
 *
 * Three rules are enforced here rather than in a component, so a test can hold them
 * without a browser:
 *
 * 1. **The success terminal of a run is `published`.** `succeeded` is a `StageResult`
 *    status on a different aggregate; it is legal on a stage row and illegal on a run.
 *    Nothing in this module produces the string for a run, and `RunStateBadge` would not
 *    compile if it did.
 * 2. **A recorded run never looks like a live one.** `provider_mode` is read from the
 *    reading and rendered; a reading that does not carry a recognised mode renders
 *    `unknown`, never `live`. Defaulting an unstated provenance to `live` would let a
 *    replayed run pass as evidence of a real model call.
 * 3. **A run that stopped stops animating.** `OD-10` reconciles a run abandoned in
 *    `running` to `failed` with an explicit interrupted reason. A view that keeps a
 *    spinner turning over that reading is telling the user work is happening when the
 *    contract says it has stopped.
 */

import type { CostBasis, RunState, RunStatus, StageId, StageStatus } from '@/shared/api';
import { PROVIDER_MODE_VALUES, isExportableRunState, isTerminalRunState } from '@/shared/api';

// ------------------------------------------------------------------------------------
// Provider mode
// ------------------------------------------------------------------------------------

/** Rendered when the reading carries no recognised provider mode. Never `live`. */
export const PROVIDER_MODE_UNKNOWN = 'unknown';

/** What the UI can display: a contract mode, or the explicit absence of one. */
export type ProviderModeLabel = (typeof PROVIDER_MODE_VALUES)[number] | typeof PROVIDER_MODE_UNKNOWN;

const PROVIDER_MODES: ReadonlySet<string> = new Set<string>(PROVIDER_MODE_VALUES);

/** Narrow an arbitrary value to a contract provider mode, or to `unknown`. */
export function providerModeLabel(value: unknown): ProviderModeLabel {
  return typeof value === 'string' && PROVIDER_MODES.has(value)
    ? (value as ProviderModeLabel)
    : PROVIDER_MODE_UNKNOWN;
}

/**
 * The provider mode of a run reading.
 *
 * The parameter is typed loosely on purpose. The contract makes `provider_mode` required,
 * but a client that trusts a required field to be present has decided that a malformed
 * response should render as `live`.
 */
export function runProviderMode(status: { readonly provider_mode?: unknown }): ProviderModeLabel {
  return providerModeLabel(status.provider_mode);
}

/**
 * The value `RunStateBadge` accepts. `unknown` is not one of its two qualifiers, so it is
 * passed as `undefined` and the screen states the absence separately and explicitly.
 */
export function badgeProviderMode(label: ProviderModeLabel): 'live' | 'recorded' | undefined {
  return label === PROVIDER_MODE_UNKNOWN ? undefined : label;
}

/** One sentence saying what this provenance is and is not evidence of. */
export function providerModeCaption(label: ProviderModeLabel): string {
  switch (label) {
    case 'live':
      return 'Live provider calls were made for this run.';
    case 'recorded':
      return 'Replayed from recordings. This run is not evidence of a live provider call.';
    case PROVIDER_MODE_UNKNOWN:
      return 'This reading carries no provider mode. It is not treated as live.';
  }
}

// ------------------------------------------------------------------------------------
// Lifecycle
// ------------------------------------------------------------------------------------

/**
 * `OD-10`: a run left `running` by a crash is reconciled to `failed` and carries an
 * explicit interrupted reason. There is no `interrupted` state.
 */
export function interruptedReason(status: Pick<RunStatus, 'interrupted_reason'>): string | null {
  const reason = status.interrupted_reason;
  return reason === undefined || reason === null || reason === '' ? null : reason;
}

/**
 * Whether the view should still show motion.
 *
 * True only while the run is non-terminal and carries no interrupted reason. A terminal
 * run and a reconciled one both stop: continuing to animate would report progress that
 * the reading says is not happening.
 */
export function isRunAnimating(
  status: Pick<RunStatus, 'state' | 'interrupted_reason'>,
): boolean {
  if (isTerminalRunState(status.state)) return false;
  return interruptedReason(status) === null;
}

/**
 * Whether this run has a published result, and therefore findings to review and bytes to
 * export. The same `OD-11` `publishes_result` flag the export panel uses — `published`
 * and `partial`, never `failed` and never a non-terminal run.
 */
export function runHasPublishedResult(state: RunState): boolean {
  return isExportableRunState(state);
}

/** What the terminal of a run actually is, as an explicit closed set of outcomes. */
export type RunOutcome =
  | { readonly kind: 'in_flight'; readonly state: RunState }
  | { readonly kind: 'published'; readonly findingCount: number | null }
  | { readonly kind: 'partial'; readonly degradation: readonly StageId[] }
  | {
      readonly kind: 'failed';
      readonly terminalReason: string | null;
      readonly interrupted: string | null;
    }
  | { readonly kind: 'cancelled' };

/**
 * Classify a reading into its outcome.
 *
 * `partial` and `failed` are separate cases from `published` and neither borrows its
 * wording: a degraded run reports its recorded degradation set, and a failed one reports
 * the catalog code it terminated with.
 */
export function runOutcome(status: RunStatus): RunOutcome {
  switch (status.state) {
    case 'created':
    case 'queued':
    case 'running':
    case 'validating':
      return { kind: 'in_flight', state: status.state };
    case 'published':
      return { kind: 'published', findingCount: status.published_finding_count ?? null };
    case 'partial':
      return { kind: 'partial', degradation: status.degradation_set ?? [] };
    case 'failed':
      return {
        kind: 'failed',
        terminalReason: status.terminal_reason ?? null,
        interrupted: interruptedReason(status),
      };
    case 'cancelled':
      return { kind: 'cancelled' };
  }
}

// ------------------------------------------------------------------------------------
// Stages
// ------------------------------------------------------------------------------------

/**
 * The four stages PC-01 schedules, in execution order.
 *
 * The contract's `StageId` enum declares nine; PC-01 schedules the first four. The other
 * five are not failures and not omissions — they are out of scope for this checkpoint,
 * which is why an unscheduled stage renders as not-applicable rather than as missing.
 */
export const PC01_STAGE_IDS = [
  'source_preparation',
  'page_geometry_extraction',
  'document_context_build',
  'text_analysis',
] as const satisfies readonly StageId[];

export interface StageRow {
  readonly stageId: StageId;
  /** `null` when the run has not reported this stage yet, or never scheduled it. */
  readonly status: StageStatus | null;
  readonly errorCode: string | null;
  readonly startedAt: string | null;
  readonly finishedAt: string | null;
  /** True when the stage is one PC-01 schedules; false for a stage the run added. */
  readonly expected: boolean;
}

/**
 * One row per PC-01 stage, plus any stage the run reported that PC-01 does not schedule.
 *
 * Built from the expected list rather than from the response, so a stage the run has not
 * reached is a visible row with no status instead of a row that is simply absent. A
 * missing row reads as "nothing to say"; an empty status reads as "not yet", which is
 * what it is.
 */
export function stageRows(status: Pick<RunStatus, 'stages'>): readonly StageRow[] {
  const reported = new Map(status.stages.map((stage) => [stage.stage_id, stage]));
  const rows: StageRow[] = [];

  for (const stageId of PC01_STAGE_IDS) {
    const stage = reported.get(stageId);
    rows.push({
      stageId,
      status: stage?.status ?? null,
      errorCode: stage?.error_code ?? null,
      startedAt: stage?.started_at ?? null,
      finishedAt: stage?.finished_at ?? null,
      expected: true,
    });
  }

  const expected: ReadonlySet<string> = new Set<string>(PC01_STAGE_IDS);
  for (const stage of status.stages) {
    if (expected.has(stage.stage_id)) continue;
    rows.push({
      stageId: stage.stage_id,
      status: stage.status,
      errorCode: stage.error_code ?? null,
      startedAt: stage.started_at ?? null,
      finishedAt: stage.finished_at ?? null,
      expected: false,
    });
  }

  return rows;
}

// ------------------------------------------------------------------------------------
// Cost
// ------------------------------------------------------------------------------------

/**
 * How many digits of `cost_micros` are the fractional part of one currency unit.
 *
 * Migration `20260910_0002` stores money as `bigint` millionths and says floating point
 * money is not stored. The contract carries that unit to the wire unchanged, and this
 * module carries it to the screen unchanged.
 */
const MICRO_FRACTION_DIGITS = 6;

/**
 * Render integer millionths for a human **without ever becoming a float**.
 *
 * The obvious implementation is `(micros / 1_000_000).toFixed(2)`. It is wrong twice: it
 * routes an exact integer through binary floating point, and it rounds away every digit
 * below a hundredth — so a run that spent one millionth prints `0.00`, which reads as
 * free. This one never divides and never parses. It is decimal-point insertion on the
 * integer's own digit string, so the digits that come out are the digits that came in.
 *
 * No currency symbol. The contract says "millionths of the provider currency unit" and
 * never names the currency; printing `$` would invent a fact the response does not carry.
 */
export function formatCostMicros(micros: number): string {
  const negative = micros < 0;
  const digits = String(Math.abs(micros)).padStart(MICRO_FRACTION_DIGITS + 1, '0');
  const whole = digits.slice(0, -MICRO_FRACTION_DIGITS);
  const fraction = digits.slice(-MICRO_FRACTION_DIGITS);
  return `${negative ? '-' : ''}${whole}.${fraction}`;
}

/**
 * What a reading says about cost.
 *
 * `absent` and a reported zero are **different facts and are kept different**. The
 * repository returns `None` for a run that made no provider call at all, so all three
 * cost fields vanish together; a run whose calls were genuinely free reports
 * `cost_micros: 0` with `model_call_count >= 1`. Collapsing the first into "0" is the
 * `D-3` class of invention: an answer produced for a question nothing was asked.
 */
export type RunCostReading =
  | { readonly kind: 'absent' }
  | { readonly kind: 'unreadable'; readonly why: string }
  | {
      readonly kind: 'reported';
      readonly micros: number;
      readonly basis: CostBasis | null;
      readonly callCount: number;
    };

/**
 * Classify the cost half of a reading.
 *
 * **A cost is never returned without its call count.** `D-15` is open: the run total sums
 * across retry attempts, so a figure with no count beside it cannot be told apart from a
 * first-try one. A response carrying `cost_micros` with no `model_call_count` violates
 * the contract's "present exactly when `cost_micros` is", and this returns `unreadable`
 * rather than print a sum whose span the reader cannot see — which would be `D-15`
 * re-created on the screen.
 *
 * The parameter is typed loosely for the same reason `runProviderMode` is: a client that
 * trusts the wire to be well-formed has decided what a malformed response renders as.
 */
export function runCost(status: {
  readonly cost_micros?: unknown;
  readonly cost_basis?: unknown;
  readonly model_call_count?: unknown;
}): RunCostReading {
  const micros = status.cost_micros;
  const callCount = status.model_call_count;

  if (micros === undefined || micros === null) return { kind: 'absent' };

  if (callCount === undefined || callCount === null) {
    return { kind: 'unreadable', why: 'it carries a cost with no model call count' };
  }
  if (typeof micros !== 'number' || !Number.isInteger(micros) || micros < 0) {
    return { kind: 'unreadable', why: 'its cost is not a non-negative integer' };
  }
  if (typeof callCount !== 'number' || !Number.isInteger(callCount) || callCount < 1) {
    return { kind: 'unreadable', why: 'its model call count is not a positive integer' };
  }

  const basis = status.cost_basis;
  return {
    kind: 'reported',
    micros,
    basis: basis === 'measured' || basis === 'estimated' ? basis : null,
    callCount,
  };
}

/**
 * One sentence saying how well the figure is known.
 *
 * `estimated` is **the ordinary case today and is not a warning**: a `recorded` run
 * replays calls that report no cost of their own, so the conservative aggregate rule
 * downgrades the whole run the moment one contributing call is unmeasured. The first
 * live run is the first that can print `measured`. Nothing here is phrased as a fault.
 */
export function costBasisCaption(basis: CostBasis | null): string {
  switch (basis) {
    case 'measured':
      return 'Every call this figure sums reported its own cost, so the figure is measured.';
    case 'estimated':
      return 'At least one call this figure sums did not report a cost of its own, so the figure is estimated. A recorded run replays calls that carry no cost, which is the ordinary case for this prototype and not a fault.';
    case null:
      return 'This reading carries no cost basis, so how well the figure is known is unstated.';
  }
}

/**
 * How many diagnostic observations this run recorded, or `null` when it did not say.
 *
 * **Not the finding count, and never folded into it.** `findings/queries.py` keeps the
 * two apart deliberately: a published finding is admitted evidence a reviewer acts on, a
 * diagnostic observation is something the run noticed and did not admit. Adding them
 * together would report evidence that was never admitted, and reporting only their sum
 * would make an unadmitted observation indistinguishable from a finding.
 */
export function diagnosticObservationCount(status: {
  readonly diagnostic_observation_count?: unknown;
}): number | null {
  const value = status.diagnostic_observation_count;
  return typeof value === 'number' && Number.isInteger(value) && value >= 0 ? value : null;
}
