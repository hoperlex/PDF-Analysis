/**
 * `RUN-RESTART-01` / `R-155a`: what a restart of an ended run is offered for, and what it takes and computes.
 *
 * A run that ended `partial`, `failed` or `cancelled` is restarted from one of the eight chips of the run screen (`RestartPoint`, the
 * contract's own enum; the same words as `RUN_CHIP_IDS`). The chip named is computed with every later one, every earlier one is taken from
 * the source (`restartRun`). The server decides what can be taken and says it in the cost estimate (`reused_restart_points`,
 * `computed_restart_points`) and, when it cannot, in a typed refusal; this file only names the choices.
 */

import type { RestartPoint, RunState, RunStatus } from '@/shared/api';
import { RESTART_POINT_VALUES } from '@/shared/api';
import { RUN_CHIP, RUN_CHIPS } from '@/entities/audit-run';
import type { RunChipId } from '@/entities/audit-run';

/** The chips in the order the rail draws them: the order a restart takes and computes them in. */
export const RESTART_POINTS: readonly RestartPoint[] = RESTART_POINT_VALUES;

/** A chip is a restart point: the compiler refuses the day the two vocabularies part (`stage-dictionary.guard` holds the dictionary). */
export function restartPointOf(chip: RunChipId): RestartPoint {
  return chip;
}

/** The chip's short name, as the rail and the list of the dialog say it. */
export function pointName(point: RestartPoint): string {
  return RUN_CHIP[point].short;
}

/** «Блоки», «Сверка»: the names in one sentence, each in guillemets. */
export function pointNames(points: readonly RestartPoint[]): string {
  return points.map((point) => `«${pointName(point)}»`).join(', ');
}

const ENDED_WITHOUT_RESULT: ReadonlySet<RunState> = new Set<RunState>(['partial', 'failed', 'cancelled']);

/** A run that ended without a clean result may be restarted; a published run is re-audited, and a running one is stopped first (`R-155a`, `R-155d`). */
export function restartableState(state: RunState | undefined): boolean {
  return state !== undefined && ENDED_WITHOUT_RESULT.has(state);
}

/** A run a restart has replaced is deleted from the lists (`R-155g`); there is nothing left to restart. */
export function restartableRun(run: Pick<RunStatus, 'state' | 'replaced_by_run_id'>): boolean {
  return restartableState(run.state) && run.replaced_by_run_id === undefined;
}

/** The roles `restartRun` admits (as `cancelRun` and `reauditRun`); an account not known yet is left to the server. */
export function mayRestart(roles: readonly string[] | undefined): boolean {
  return roles === undefined || roles.includes('expert') || roles.includes('admin');
}

/** The chips before the point: taken from the source. */
export function takenBefore(point: RestartPoint): readonly RestartPoint[] {
  return RESTART_POINTS.slice(0, RESTART_POINTS.indexOf(point));
}

/** The point and every chip after it: computed. */
export function computedFrom(point: RestartPoint): readonly RestartPoint[] {
  return RESTART_POINTS.slice(RESTART_POINTS.indexOf(point));
}

/**
 * The stage ids of the chips a restart from this point took from its source (the rail marks a chip «из прогона» when every stage row of it
 * is in the set). Nothing before the preparation, so a restart from it takes none.
 */
export function stageIdsTakenBefore(point: RestartPoint): ReadonlySet<string> {
  const taken = new Set(takenBefore(point));
  return new Set(RUN_CHIPS.filter((chip) => taken.has(chip.id)).flatMap((chip) => chip.stageIds));
}

/**
 * Whether the chips taken from the source include the norms' answer, which a later search may not repeat: from the critic on, the norms are
 * taken, and a search that gives another result stops the restart at «Нормы» (`restart_request_changed`).
 */
export function takesNorms(point: RestartPoint): boolean {
  return RESTART_POINTS.indexOf(point) > RESTART_POINTS.indexOf('norms');
}
