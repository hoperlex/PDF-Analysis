/**
 * Run-state and stage-status vocabulary, split into the distinctions the UI needs.
 *
 * The value sets themselves are generated from the contract; nothing here re-declares
 * one. What this module adds is the terminal/non-terminal split, which the contract's
 * enum does not carry but `P02_SEAMS.md` sections 6 and 9.2 fix, plus the exportability
 * rule the export panel needs.
 *
 * The success terminal of an `AuditRun` is `published`. `succeeded` is a `StageResult`
 * status on a different aggregate and is never a run state — rendering it on a run badge
 * is the mistake this split exists to make impossible.
 */

import type { RunState, StageStatus } from './generated/types.gen';
import { RUN_STATE_VALUES } from './generated/types.gen';

/** States a run can still leave. Polling continues while the reading is one of these. */
export const NON_TERMINAL_RUN_STATES = ['created', 'queued', 'running', 'validating'] as const;

/** States a run never leaves. Polling stops on any of them. */
export const TERMINAL_RUN_STATES = ['published', 'partial', 'failed', 'cancelled'] as const;

export type NonTerminalRunState = (typeof NON_TERMINAL_RUN_STATES)[number];
export type TerminalRunState = (typeof TERMINAL_RUN_STATES)[number];

/**
 * Compile-time proof that the split is a partition of the contract enum. Adding a state
 * to the contract without classifying it here stops type-checking.
 */
const _partitionCoversContract: readonly RunState[] = [
  ...NON_TERMINAL_RUN_STATES,
  ...TERMINAL_RUN_STATES,
];
void _partitionCoversContract;
const _contractCoversPartition: readonly (NonTerminalRunState | TerminalRunState)[] = RUN_STATE_VALUES;
void _contractCoversPartition;

const TERMINAL: ReadonlySet<string> = new Set<string>(TERMINAL_RUN_STATES);

/** True when the run will not change state again. */
export function isTerminalRunState(state: RunState): state is TerminalRunState {
  return TERMINAL.has(state);
}

/**
 * Terminals whose `publishes_result` flag is true, per `OD-11` and `P02_SEAMS.md`
 * section 6. These, and only these, are exportable — a `partial` run is exported with its
 * degradation visible in the `run_state` column, not refused.
 */
export const EXPORTABLE_RUN_STATES = ['published', 'partial'] as const;

const EXPORTABLE: ReadonlySet<string> = new Set<string>(EXPORTABLE_RUN_STATES);

/**
 * True when `GET /runs/{run_id}/export.csv` will return bytes rather than
 * `state_transition_not_allowed`. A UI uses this to enable the export control; the
 * server remains the authority.
 */
export function isExportableRunState(state: RunState): boolean {
  return EXPORTABLE.has(state);
}

/**
 * A `succeeded` stage carries no error; every other status carries one. Stated as a
 * predicate so a stage row does not re-derive it from the presence of `error_code`.
 */
export function stageCarriesError(status: StageStatus): boolean {
  return status !== 'succeeded';
}
