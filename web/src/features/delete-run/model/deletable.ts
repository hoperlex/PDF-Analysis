/**
 * `RUN-DELETE-01`: which runs may be deleted, and by whom.
 *
 * Deleting takes a run out of every list (the server keeps a tombstone; its findings and the expert's decisions stay stored). Only a run
 * that ended without a clean result is noise worth removing: `partial`, `failed` and `cancelled`. A `published` run is the result, and a
 * run that has not ended is cancelled first. The server refuses everything else with a `409`; the screen stops offering it.
 */

import type { RunState } from '@/shared/api';

export const DELETABLE_STATES: ReadonlySet<RunState> = new Set<RunState>(['partial', 'failed', 'cancelled']);

/** A partial, failed or cancelled run may be deleted; an unknown state is not offered. */
export function deletable(state: RunState | undefined): boolean {
  return state !== undefined && DELETABLE_STATES.has(state);
}

/** The roles `deleteRun` admits, the same as `cancelRun`; an unknown account is left to the server. */
export function mayDelete(roles: readonly string[] | undefined): boolean {
  return roles === undefined || roles.includes('expert') || roles.includes('admin');
}
