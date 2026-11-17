/**
 * The rows of the window «Модели по этапам» of a start (`UIP-S05-01`, pair S05): the six stages of an analysis, each with the cells
 * that would do its work and a phrase for what actually runs.
 *
 * Pure: the answer the readiness gave (or, while the layout is off, the saved layout) in, the six rows a person reads out. Nothing is
 * invented to fill a row: a stage the run does not take has no cell and says why in the phrase, and a number or a server the answer
 * does not carry is not written.
 *
 * Two sources, one row shape. On the layout's route the cells are the plan a start would freeze (`readinessPlan`), each with the access
 * it would run with. With the layout off, the route is the one as before, and the window shows the layout as it is saved, read through
 * the same plan rows, so the table has one shape: a cell of the saved layout has no access (no start has bound one) and says only
 * whether a server can serve it.
 */

import type { RunStartReadiness, RunStartReadinessCell, StageCellRole, StageModelKit, StageModelLayout, StageRowKey } from '@/shared/api';
import { STAGE_ROW_KEY_VALUES } from '@/shared/api';
import { STAGE_ROW_LABELS, readinessPlan } from '@/entities/stage-layout';
import type { PlanCell } from '@/entities/stage-layout';

export const COLUMN_STAGE = 'Этап';
export const COLUMN_MODEL = 'Модель';
export const COLUMN_EFFORT = 'Усилие';
export const COLUMN_ACCESS = 'Доступ';
export const COLUMN_FACT = 'Фактически работает';
export const CLOSE_LABEL = 'Закрыть';

/** What a stage that no model answers says of itself under plan v2: the critic and the refinement run by the original's rules. */
export const BY_ORIGINAL_RULES = 'без модели (правила оригинала)';
/** A stage the run does not take: it has no cell in the plan. */
export const NOT_IN_RUN = 'не входит в запуск';
/** The three words of a window that has no plan to read: the layout is off, the server chooses the route, the readiness was not read. */
export const FACT_OLD_ROUTE = 'прежний маршрут';
export const FACT_AUTOMATIC = 'автоматически';
export const FACT_NOT_READ = 'не прочитано';

/** The three sets in the order the original lists them; the one in force is marked and none of them is a switch here. */
export const KITS_IN_ORDER: readonly StageModelKit[] = ['claude_only', 'codex_only', 'custom'];

/** The rows the original's rules serve without a model under plan v2. */
const ORIGINAL_RULES_ROWS: ReadonlySet<StageRowKey> = new Set<StageRowKey>(['review', 'correction']);

/**
 * What the window has to draw from. `plan`: the layout is on and the answer states the plan. The others: no plan to read, and the
 * table is the saved layout; each names the one word the fact column says.
 */
export type StageModelsSource =
  | { readonly kind: 'plan'; readonly readiness: RunStartReadiness }
  | { readonly kind: 'legacy' }
  | { readonly kind: 'automatic' }
  | { readonly kind: 'unread' };

export interface StageModelsRow {
  readonly row: StageRowKey;
  readonly label: string;
  /** The cells in the order of the roles; empty for a stage the run does not take. */
  readonly cells: readonly PlanCell[];
  /** «одна модель», «ветка и судья», «не входит в запуск», … */
  readonly fact: string;
}

/**
 * What a row of cells says it does, by the roles of its cells: one answer, a leg and a judge, two legs that run side by side and a judge.
 * A shape the layout does not offer is said by its parts, never guessed into one of those.
 */
export function factOfRoles(roles: readonly StageCellRole[]): string {
  const parts: string[] = [];
  const legs = roles.filter((role) => role === 'leg1' || role === 'leg2').length;
  if (roles.includes('main')) parts.push('одна модель');
  if (legs === 1) parts.push('ветка');
  if (legs >= 2) parts.push('две ветки параллельно');
  if (roles.includes('judge')) parts.push('судья');
  return parts.join(' и ');
}

function rowsOf(cells: readonly RunStartReadinessCell[], factOf: (row: StageRowKey, own: readonly PlanCell[]) => string): readonly StageModelsRow[] {
  const planned = new Map(readinessPlan(cells).map((plan) => [plan.row, plan.cells] as const));
  return STAGE_ROW_KEY_VALUES.map((row) => {
    const own = planned.get(row) ?? [];
    return { row, label: STAGE_ROW_LABELS[row], cells: own, fact: factOf(row, own) };
  });
}

/** The six rows of the plan a start would freeze. A stage with no cell is out of the run, or, under plan v2, served by the original's rules. */
export function planStageRows(readiness: RunStartReadiness): readonly StageModelsRow[] {
  return rowsOf(readiness.cells, (row, own) => {
    if (own.length > 0) return factOfRoles(own.map((cell) => cell.role));
    return readiness.extended_plan === 'v2' && ORIGINAL_RULES_ROWS.has(row) ? BY_ORIGINAL_RULES : NOT_IN_RUN;
  });
}

/** The six rows of the saved layout, every one saying the same `fact`: there is no plan, so there is no fact to read from one. */
export function layoutStageRows(layout: StageModelLayout, fact: string): readonly StageModelsRow[] {
  const unavailable = new Set(layout.unavailable_cell_keys);
  const cells: RunStartReadinessCell[] = (layout.current?.cells ?? []).map((cell) => ({
    cell_key: cell.cell_key,
    row: cell.row,
    role: cell.role,
    model_id: cell.model_id,
    effort: cell.effort,
    available: !unavailable.has(cell.cell_key),
    reasons: [],
  }));
  return rowsOf(cells, () => fact);
}

/** The word of the fact column for a source that has no plan. */
export function factWordOf(source: Exclude<StageModelsSource, { readonly kind: 'plan' }>): string {
  switch (source.kind) {
    case 'legacy':
      return FACT_OLD_ROUTE;
    case 'automatic':
      return FACT_AUTOMATIC;
    case 'unread':
      return FACT_NOT_READ;
  }
}

/** The set in force, or `null` when nothing names one: a window draws no set it cannot name. */
export function kitOf(source: StageModelsSource, layout: StageModelLayout | undefined): StageModelKit | null {
  if (source.kind === 'plan') return source.readiness.kit ?? null;
  return layout?.current?.kit ?? null;
}
