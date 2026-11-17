/**
 * A run started from an earlier run, as the run page tells it: a start from a stage (`UI-A-60` / `R-151i`) or a restart from a chip
 * (`RUN-RESTART-01` / `R-155a`).
 *
 * `RunStatus.started_from_run_id` comes with `start_stage_id` for a start from a stage and with `restart_point` for a restart, never with
 * both (`start_stage_id` is absent for a restart). The stages before the start are the earlier run's (the server wrote their rows as
 * `succeeded` with the same artifacts, or took their replies); the start and the later ones were computed by this run. Nothing here
 * decides what may be reused -- the server did, and refused otherwise.
 */

import type { RestartPoint, RunStatus, StageId } from '@/shared/api';
import { PC01_STAGE_IDS } from '@/entities/audit-run';
import { stageIdsTakenBefore } from '@/features/restart-run';

interface StartedFromBase {
  readonly sourceRunId: string;
  /** The stages this run took from the source run. */
  readonly reusedStageIds: ReadonlySet<string>;
}

/** A start from a stage of an ended run (`startRunFromStage`). */
export interface StartedFromStage extends StartedFromBase {
  readonly kind: 'stage';
  readonly stageId: StageId;
  /** The stage's place in the rail, from 1. */
  readonly ordinal: number;
}

/** A restart from a chip of a run that ended without a clean result (`restartRun`). */
export interface StartedFromRestart extends StartedFromBase {
  readonly kind: 'restart';
  readonly point: RestartPoint;
}

export type StartedFrom = StartedFromStage | StartedFromRestart;

export function startedFrom(
  status: Pick<RunStatus, 'started_from_run_id' | 'start_stage_id' | 'restart_point'>,
): StartedFrom | null {
  const sourceRunId = status.started_from_run_id;
  if (sourceRunId === undefined) return null;
  if (status.restart_point !== undefined) {
    return { kind: 'restart', sourceRunId, point: status.restart_point, reusedStageIds: stageIdsTakenBefore(status.restart_point) };
  }
  const stageId = status.start_stage_id;
  if (stageId === undefined) return null;
  const index = (PC01_STAGE_IDS as readonly string[]).indexOf(stageId);
  if (index < 0) return null;
  return { kind: 'stage', sourceRunId, stageId, ordinal: index + 1, reusedStageIds: new Set(PC01_STAGE_IDS.slice(0, index)) };
}
