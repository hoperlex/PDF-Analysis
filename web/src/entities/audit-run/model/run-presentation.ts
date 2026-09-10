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

import type { RunState, RunStatus, StageId, StageStatus } from '@/shared/api';
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
