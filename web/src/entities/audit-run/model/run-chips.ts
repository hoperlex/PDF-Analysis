/**
 * What the rail says about a run: its chips and how each stands (`RUN-SCREEN-01a`, plan §9.2).
 *
 * A chip's state is read from two places and nowhere else. The **stage states** the run reports (`RunStatus.stages`, the PC-01
 * stages) are canonical for the chips they cover. The extended review's **procedures** carry the rest (`block_analysis`,
 * `comprehensive_analysis`, `finding_merge`, `norm_verification`, `finding_review`, `finding_correction`); they are read only
 * for a chip the stage states say nothing about. A chip that neither source mentions is **not in this run** and is not drawn.
 *
 * Two states are the screen's reading of the run rather than a status the server wrote, and only while the run is open:
 * the first chip that has not started is `running` (the run is on it), or `waiting` when the run is still in the queue
 * (`RunStatus.state === 'queued'`). Neither is stored, and a terminal run has neither.
 *
 * No token figure is read: the contract has none per phase, and a chip with no figure shows none (the plan's wave 2 adds them).
 */

import type { RunStatus } from '@/shared/api';

import type { ProcedureReading } from './extended-readings';
import { elapsedMs, isRunAnimating, stageRows } from './run-presentation';
import type { StageRow } from './run-presentation';
import { RUN_CHIPS } from './stage-dictionary';
import type { RunChipDefinition } from './stage-dictionary';

export type ChipState = 'pending' | 'waiting' | 'running' | 'done' | 'partial' | 'failed' | 'skipped' | 'unavailable';

/** The words of each state; «выполнен», «частично», «отказ» and «пропущен» are `StageStatusBadge`'s own. */
export const CHIP_STATE_LABELS: Readonly<Record<ChipState, string>> = {
  pending: 'не начат',
  waiting: 'ждёт',
  running: 'идёт',
  done: 'выполнен',
  partial: 'частично',
  failed: 'отказ',
  skipped: 'пропущен',
  unavailable: 'недоступен',
};

/** A state after which the chip does no more work. */
const COMPLETED: ReadonlySet<ChipState> = new Set(['done', 'partial', 'skipped', 'unavailable']);

export interface RunChip {
  readonly definition: RunChipDefinition;
  readonly state: ChipState;
  /** The PC-01 stage rows the chip covers (empty for a chip that exists only in the extended review). */
  readonly stages: readonly StageRow[];
  /** The extended review's procedures the chip covers. */
  readonly procedures: readonly ProcedureReading[];
  /** The earliest start among the rows this run computed; `null` where there is none. */
  readonly startedAt: string | null;
  readonly finishedAt: string | null;
  /** The chip's duration where both ends exist; a chip taken from an earlier run has none (`reused`). */
  readonly elapsedMs: number | null;
  /** Every stage row of the chip was taken by reference from the run this one was started from. */
  readonly reused: boolean;
  readonly errorCode: string | null;
}

export interface RunChipsInput {
  readonly status: Pick<RunStatus, 'state' | 'stages' | 'interrupted_reason'>;
  readonly procedures: readonly ProcedureReading[];
  /** The stage ids this run took from the run it was started from (`startedFrom(...).reusedStageIds`). */
  readonly reused?: ReadonlySet<string> | undefined;
}

function stateOfRows(rows: readonly StageRow[], open: boolean): ChipState | null {
  const reported = rows.flatMap((row) => (row.status === null ? [] : [row.status]));
  if (reported.length === 0) return null;
  if (reported.includes('failed')) return 'failed';
  if (reported.includes('partial')) return 'partial';
  if (reported.length < rows.length) return open ? 'running' : 'partial';
  return reported.every((status) => status === 'skipped') ? 'skipped' : 'done';
}

function stateOfProcedures(procedures: readonly ProcedureReading[]): ChipState | null {
  if (procedures.length === 0) return null;
  const statuses = procedures.map((procedure) => procedure.status);
  if (statuses.includes('failed')) return 'failed';
  if (statuses.some((status) => status === 'running' || status === 'repairing')) return 'running';
  if (statuses.includes('partial')) return 'partial';
  if (statuses.every((status) => status === 'completed')) return 'done';
  if (statuses.every((status) => status === 'skipped')) return 'skipped';
  if (statuses.every((status) => status === 'unavailable')) return 'unavailable';
  if (statuses.every((status) => status === 'queued')) return 'pending';
  if (statuses.every((status) => status === 'completed' || status === 'skipped')) return 'done';
  return statuses.includes('queued') ? 'running' : 'partial';
}

const earliest = (values: readonly string[]): string | null =>
  values.length === 0 ? null : values.reduce((a, b) => (Date.parse(b) < Date.parse(a) ? b : a));
const latest = (values: readonly string[]): string | null =>
  values.length === 0 ? null : values.reduce((a, b) => (Date.parse(b) > Date.parse(a) ? b : a));

/**
 * The chips of a run, in the rail's order. A chip appears when a stage row or a procedure mentions it.
 */
export function runChips({ status, procedures, reused }: RunChipsInput): readonly RunChip[] {
  const rows = stageRows(status);
  const open = isRunAnimating(status);

  const chips: RunChip[] = [];
  for (const definition of RUN_CHIPS) {
    const chipRows = rows.filter((row) => definition.stageIds.includes(row.stageId));
    const chipProcedures = procedures.filter((procedure) => definition.stageIds.includes(procedure.id));
    if (chipRows.length === 0 && chipProcedures.length === 0) continue;

    const computed = chipRows.filter((row) => reused?.has(row.stageId) !== true);
    const started = computed.flatMap((row) => (row.startedAt === null ? [] : [row.startedAt]));
    const finished = computed.flatMap((row) => (row.finishedAt === null ? [] : [row.finishedAt]));
    const startedAt = earliest(started);
    const finishedAt = computed.length > 0 && finished.length === computed.length ? latest(finished) : null;
    const failing = chipRows.find((row) => row.status === 'failed' || row.status === 'partial');

    chips.push({
      definition,
      state: stateOfRows(chipRows, open) ?? stateOfProcedures(chipProcedures) ?? 'pending',
      stages: chipRows,
      procedures: chipProcedures,
      startedAt,
      finishedAt,
      elapsedMs: elapsedMs(startedAt, finishedAt),
      reused: chipRows.length > 0 && chipRows.every((row) => reused?.has(row.stageId) === true),
      errorCode: failing?.errorCode ?? chipProcedures.find((procedure) => procedure.errorCode !== null)?.errorCode ?? null,
    });
  }

  if (!open || chips.some((chip) => chip.state === 'running')) return chips;
  const next = chips.findIndex((chip) => chip.state === 'pending');
  if (next < 0) return chips;
  return chips.map((chip, at) => (at === next ? { ...chip, state: status.state === 'queued' ? 'waiting' : 'running' } : chip));
}

export interface ChipProgress {
  /** Chips in this run. */
  readonly total: number;
  /** Chips that did their work: done, partial, skipped or unavailable. A failed chip is not counted. */
  readonly completed: number;
  /** The chip the run is on (or waits to start), if the run is open and one is. */
  readonly live: RunChip | null;
  /** The live chip's place among the chips of this run, from 1; `null` without one. */
  readonly liveIndex: number | null;
}

export function chipProgress(chips: readonly RunChip[]): ChipProgress {
  const at = chips.findIndex((chip) => chip.state === 'running' || chip.state === 'waiting');
  return {
    total: chips.length,
    completed: chips.filter((chip) => COMPLETED.has(chip.state)).length,
    live: at < 0 ? null : (chips[at] as RunChip),
    liveIndex: at < 0 ? null : at + 1,
  };
}
