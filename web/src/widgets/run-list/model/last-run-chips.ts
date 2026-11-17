/**
 * What the card «Последний прогон» says of a run's stages (`UIP-S04-03`): the chips of the run, how each stands, how long it took,
 * and the hint of a chip. Pure: the run the list read and the stages `getRunStages` answered in, chips and words out.
 *
 * **The same chips as the run page.** The run page draws `runChips` (the stage rows of the run, and the extended review's procedures
 * for the chips the rows say nothing about); the stages answer lists the chips the run has with their state and times, read on the
 * server from the same three places. The card has the run's status and the stages and not the extended review's reading, so it takes
 * the chips of the status (`runChips`, with no procedures) and lets the stages complete them: a chip only the stages list (the
 * complex cross-check) is drawn from the stages, and where both say something the stages' words are the chip's (the server read the
 * journal and the procedures, the screen only the rows). Before the stages are read the chips are the status's alone. Nothing here
 * decides a state: every word is the server's.
 *
 * **No model on the card.** A chip's hint is its full name; the model of the stage (the plan's pin, or «2 модели») is added to it
 * for an administrator and for nobody else (`Г12-B`). The card has no token, no cost and no model line of its own.
 */

import type { RunStages, RunStatus } from '@/shared/api';
import {
  PC01_STAGE_IDS,
  RUN_CHIPS,
  elapsedMs,
  planModelIds,
  runChips,
  shortModelName,
  stageOfChip,
} from '@/entities/audit-run';
import type { RunChip, RunChipDefinition } from '@/entities/audit-run';
import { stageIdsTakenBefore } from '@/features/restart-run';

/**
 * The stage ids this run took from the run it was started from: `started_from_run_id` comes with `start_stage_id` (a start from a stage)
 * or with `restart_point` (a restart, `RUN-RESTART-01`), not with both.
 */
export function reusedStageIdsOf(
  status: Pick<RunStatus, 'started_from_run_id' | 'start_stage_id' | 'restart_point'>,
): ReadonlySet<string> | undefined {
  if (status.started_from_run_id === undefined) return undefined;
  if (status.restart_point !== undefined) return stageIdsTakenBefore(status.restart_point);
  if (status.start_stage_id === undefined) return undefined;
  const index = (PC01_STAGE_IDS as readonly string[]).indexOf(status.start_stage_id);
  return index < 0 ? undefined : new Set(PC01_STAGE_IDS.slice(0, index));
}

/** The chip of a definition the status has no row for, drawn from what the stages say of it. */
function chipOfStages(definition: RunChipDefinition, stage: NonNullable<ReturnType<typeof stageOfChip>>): RunChip {
  const facts = stage.facts;
  const reused = facts.reused_from_run_id !== undefined;
  return {
    definition,
    state: facts.state,
    stages: [],
    procedures: [],
    startedAt: facts.started_at ?? null,
    finishedAt: facts.finished_at ?? null,
    elapsedMs: reused ? null : elapsedMs(facts.started_at, facts.finished_at),
    reused,
    errorCode: facts.last_error_code ?? null,
  };
}

/**
 * The chips of the run in the rail's order. A chip the status has and the stages list takes the stages' state, times and error; a
 * chip only one of them has is drawn from that one. With the stages not read (`null`) the chips are the status's.
 */
export function lastRunChips(status: RunStatus, stages: RunStages | null): readonly RunChip[] {
  const base = runChips({ status, procedures: [], reused: reusedStageIdsOf(status) });
  if (stages === null) return base;
  const chips: RunChip[] = [];
  for (const definition of RUN_CHIPS) {
    const own = base.find((chip) => chip.definition.id === definition.id) ?? null;
    const stage = stageOfChip(stages, definition.id);
    if (stage === null) {
      if (own !== null) chips.push(own);
      continue;
    }
    if (own === null) {
      chips.push(chipOfStages(definition, stage));
      continue;
    }
    const facts = stage.facts;
    const reused = own.reused || facts.reused_from_run_id !== undefined;
    const startedAt = facts.started_at ?? own.startedAt;
    const finishedAt = facts.finished_at ?? own.finishedAt;
    chips.push({
      ...own,
      state: facts.state,
      startedAt,
      finishedAt,
      elapsedMs: reused ? null : elapsedMs(startedAt, finishedAt),
      reused,
      errorCode: facts.last_error_code ?? own.errorCode,
    });
  }
  return chips;
}

/**
 * The hint of a chip: the stage's full name, and for an administrator the model the stage was planned on («Модель: Opus 5.5», «Модели:
 * Opus 5.5 · Sonnet 5.5»). A stage that calls no model, or one the stages did not read, has the name alone.
 */
export function chipHint(chip: RunChip, stages: RunStages | null, admin: boolean): string {
  const name = chip.definition.full;
  if (!admin || !chip.definition.callsModel) return name;
  const names = planModelIds(stageOfChip(stages, chip.definition.id)).map((id) => shortModelName(id) ?? id);
  if (names.length === 0) return name;
  return `${name} · ${names.length === 1 ? 'Модель' : 'Модели'}: ${names.join(' · ')}`;
}
