/**
 * `UI-A-60` / `R-151i`: a run started from a stage of an earlier run, as the run page tells it.
 *
 * `RunStatus.started_from_run_id` and `start_stage_id` come together or not at all. The stages before the start stage are the
 * earlier run's (the server wrote their rows as `succeeded` with the same artifacts); the start stage and the later ones were
 * computed by this run. Nothing here decides what may be reused -- the server did, and refused otherwise.
 */

import type { RunStatus, StageId } from '@/shared/api';
import { PC01_STAGE_IDS } from '@/entities/audit-run';

export interface StartedFrom {
  readonly sourceRunId: string;
  readonly stageId: StageId;
  /** The stage's place in the rail, from 1. */
  readonly ordinal: number;
  /** The stages this run took from the source run. */
  readonly reusedStageIds: ReadonlySet<string>;
}

export function startedFrom(status: Pick<RunStatus, 'started_from_run_id' | 'start_stage_id'>): StartedFrom | null {
  const sourceRunId = status.started_from_run_id;
  const stageId = status.start_stage_id;
  if (sourceRunId === undefined || stageId === undefined) return null;
  const index = (PC01_STAGE_IDS as readonly string[]).indexOf(stageId);
  if (index < 0) return null;
  return { sourceRunId, stageId, ordinal: index + 1, reusedStageIds: new Set(PC01_STAGE_IDS.slice(0, index)) };
}
