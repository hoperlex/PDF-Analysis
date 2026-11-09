/**
 * What a run's stages (`getRunStages`) say of the models of a chip, read for the rail and the window «Этапы анализа раздела».
 *
 * Pure: the answer in, a few words out. A chip's plan is its list of cells (a single answer, or the legs and the judge of an
 * ensemble); the rail has room for one short line under the chip's name, and this is that line:
 *
 * - every cell on one model: its short name («Opus 5.5»);
 * - cells on several models: their number («2 модели»), the names in the tooltip;
 * - no cell with a model (a chip that calls none, or a chip the answer does not list): nothing.
 *
 * Nothing is guessed: a cell that names no model is not counted, and a name this module cannot shorten is the pin as it is
 * (`shortModelName`).
 */

import type { RunStage, RunStageCell, RunStages } from '@/shared/api';

import { shortModelName } from './model-short-name';

/** The stage entry of a chip, or `null` where the answer has none (not read yet, or the run does not have the chip). */
export function stageOfChip(stages: RunStages | null | undefined, chip: string): RunStage | null {
  return stages?.items.find((item) => item.chip === chip) ?? null;
}

/** The distinct models of a chip's plan, in the order of the cells; a cell with no model is skipped. */
export function planModelIds(stage: RunStage | null): readonly string[] {
  if (stage === null) return [];
  const ids = stage.plan.flatMap((cell: RunStageCell) => (cell.model_id === undefined ? [] : [cell.model_id]));
  return [...new Set(ids)];
}

/** «2 модели», «5 моделей»: the plural of «модель» after a number of two or more. */
export function modelsCount(count: number): string {
  const lastTwo = count % 100;
  const last = count % 10;
  const word = last >= 2 && last <= 4 && !(lastTwo >= 12 && lastTwo <= 14) ? 'модели' : 'моделей';
  return `${count} ${word}`;
}

export interface ChipModelLine {
  /** What the rail prints under the chip's name. */
  readonly text: string;
  /** What the tooltip says: the pin of the one model, or the short names of all of them. */
  readonly title: string;
}

/** The rail's one line for a chip, or `null` where the chip has no model to name. */
export function chipModelLine(stage: RunStage | null): ChipModelLine | null {
  const ids = planModelIds(stage);
  if (ids.length === 0) return null;
  const names = ids.map((id) => shortModelName(id) ?? id);
  if (ids.length === 1) return { text: names[0] as string, title: ids[0] as string };
  return { text: modelsCount(ids.length), title: names.join(' · ') };
}
