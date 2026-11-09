/**
 * The plan a start would freeze, as `getRunStartReadiness` states it (`READINESS-WEB-01`, plan 2026-11-09 §8 and §9.4): the cells of
 * the rows this run takes, each with its model, its effort and the access it would run with.
 *
 * Pure: the readiness answer in, the rows a person reads out. A row the run does not take (the critic and the refinement belong to
 * the third version) has no cell in the answer and is not a row here; nothing is invented to fill the six. The words are the
 * layout's own (`./vocabulary.ts`), so a model and an effort are called the same thing here as in «Модели по этапам».
 */

import type { ExecutorModelAccess, ModelEffort, RunStartReadinessCell, StageCellRole, StageRowKey } from '@/shared/api';
import { STAGE_ROW_KEY_VALUES } from '@/shared/api';
import { modelLabel } from '@/entities/executor-host';

import { rowCells } from './table';
import { STAGE_EFFORT_LABELS, STAGE_ROLE_LABELS, STAGE_ROW_LABELS } from './vocabulary';

export interface PlanCell {
  readonly cellKey: string;
  readonly role: StageCellRole;
  /** «первая ветка», «судья»; empty for the one answer of a row (`STAGE_ROLE_LABELS.main`). */
  readonly roleLabel: string;
  readonly modelId: string;
  /** «Opus 5.5». */
  readonly model: string;
  readonly effort: ModelEffort;
  /** «среднее». */
  readonly effortLabel: string;
  /** The access the cell would run with; `null` when no server can serve it. */
  readonly access: ExecutorModelAccess | null;
  readonly available: boolean;
}

export interface PlanRow {
  readonly row: StageRowKey;
  /** «Анализ блоков». */
  readonly label: string;
  readonly cells: readonly PlanCell[];
}

/** The rows of the plan, in the order the original lists them; a row with no cell is left out. */
export function readinessPlan(cells: readonly RunStartReadinessCell[]): readonly PlanRow[] {
  return STAGE_ROW_KEY_VALUES.flatMap((row) => {
    const own = rowCells(cells, row);
    if (own.length === 0) return [];
    return [{
      row,
      label: STAGE_ROW_LABELS[row],
      cells: own.map((cell) => ({
        cellKey: cell.cell_key,
        role: cell.role,
        roleLabel: STAGE_ROLE_LABELS[cell.role],
        modelId: cell.model_id,
        model: modelLabel(cell.model_id),
        effort: cell.effort,
        effortLabel: STAGE_EFFORT_LABELS[cell.effort],
        access: cell.access ?? null,
        available: cell.available,
      })),
    }];
  });
}

/**
 * The cells of the plan no server can serve, each as «Нет Opus 5.5 — Анализ блоков»: the model that is missing and the row that
 * needs it. A model that several cells of one row name (the legs of a scheme) is said once for that row.
 */
export function missingModelSentences(cells: readonly RunStartReadinessCell[]): readonly string[] {
  const seen = new Set<string>();
  const sentences: string[] = [];
  for (const plan of readinessPlan(cells)) {
    for (const cell of plan.cells) {
      if (cell.available) continue;
      const sentence = `Нет ${cell.model} — ${plan.label}`;
      if (seen.has(sentence)) continue;
      seen.add(sentence);
      sentences.push(sentence);
    }
  }
  return sentences;
}
