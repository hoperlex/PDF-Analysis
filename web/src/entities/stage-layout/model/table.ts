/**
 * The table of «Модели по этапам» (`HOSTS-WEB-01`, plan 2026-11-09 §7.4): six rows, «строка — модель · усилие», read from the
 * revision in force.
 *
 * A row holds one cell, or several when the row is an ensemble scheme (the legs and the judge). The row says
 * «⚠ нет на серверах» when the server's own `unavailable_cell_keys` names any of its cells, and only then: a row whose model
 * is served carries no mark at all (the problem is shown, the normal is not).
 */

import type { StageLayoutCell, StageModelLayout, StageRowKey } from '@/shared/api';
import { STAGE_ROW_KEY_VALUES } from '@/shared/api';
import { modelLabel } from '@/entities/executor-host';

import { STAGE_EFFORT_LABELS, STAGE_ROLE_LABELS } from './vocabulary';

/** The order of the roles inside a row. */
const ROLE_ORDER = ['main', 'leg1', 'leg2', 'judge'] as const;

export interface CellReading {
  readonly cellKey: string;
  readonly role: StageLayoutCell['role'];
  /** «Opus 5.5 · среднее», with the role in front when the row has several cells. */
  readonly text: string;
  readonly unavailable: boolean;
}

export interface TableRow {
  readonly row: StageRowKey;
  readonly cells: readonly CellReading[];
  /** Any cell of the row names a model no server can serve now. */
  readonly problem: boolean;
}

/** «Opus 5.5 · среднее». */
export function cellText(cell: Pick<StageLayoutCell, 'model_id' | 'effort'>): string {
  return `${modelLabel(cell.model_id)} · ${STAGE_EFFORT_LABELS[cell.effort]}`;
}

/** The cells of one row of a revision, in the order of the roles. */
export function rowCells(cells: readonly StageLayoutCell[], row: StageRowKey): readonly StageLayoutCell[] {
  return cells
    .filter((cell) => cell.row === row)
    .sort((a, b) => ROLE_ORDER.indexOf(a.role) - ROLE_ORDER.indexOf(b.role));
}

/**
 * The six rows of the revision in force. A row the revision has no cell for is still a row, with no cells (an incomplete
 * revision is a server defect; the table says so by being empty there rather than inventing a model).
 */
export function layoutTable(layout: StageModelLayout): readonly TableRow[] {
  const unavailable = new Set(layout.unavailable_cell_keys);
  const cells = layout.current?.cells ?? [];
  return STAGE_ROW_KEY_VALUES.map((row) => {
    const own = rowCells(cells, row);
    const several = own.length > 1;
    const readings = own.map((cell) => {
      const role = STAGE_ROLE_LABELS[cell.role];
      return {
        cellKey: cell.cell_key,
        role: cell.role,
        text: several && role !== '' ? `${role}: ${cellText(cell)}` : cellText(cell),
        unavailable: unavailable.has(cell.cell_key),
      };
    });
    return { row, cells: readings, problem: readings.some((reading) => reading.unavailable) };
  });
}

/**
 * The row of the layout a phase of the code belongs to (plan 2026-11-09 §4.1), for a screen that names the stage of a task:
 * the preparation, the merge, the quote check and the report have no row and no model, and answer `null`.
 */
export function rowOfStageKey(stageKey: string): StageRowKey | null {
  const phase = stageKey.split(':')[0] ?? stageKey;
  switch (phase) {
    case 'text_analysis':
      return 'text';
    case 'blocks':
      return 'blocks';
    case 'comprehensive_analysis':
    case 'parameter_passport':
      return 'cross_check';
    case 'norm_verification':
      return 'norms';
    case 'finding_review':
      return 'review';
    case 'finding_correction':
      return 'correction';
    default:
      return null;
  }
}
