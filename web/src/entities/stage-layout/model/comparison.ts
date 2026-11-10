/**
 * The comparison cells of the layout (`HOSTS-CMP-01`, ADR-0028 decision 19; the web part is `CMP-WEB-01`): one cell for each of the four
 * kinds of work of the comparison of versions that call a model, kept in the revision beside the six rows and in no run's plan.
 *
 * - **The sets.** «Только Claude» serves all four kinds on Sonnet 5.5, «Только Codex» on gpt-6-astra and gpt-6.1-sol, each at the high effort.
 *   These are the tables `COMPARISON_PRESET_CELLS` of `src/auditmanager/runs/stage_layout.py`; the server accepts a named set only if its
 *   comparison cells have these models and efforts, so a copy that drifted is refused, never stored. `tests/unit/stage-layout/comparison-drift.test.ts`
 *   reads the Python source and compares.
 * - **The limits.** The answer limit and the call window of each kind are the constants of the code (`COMPARISON_DEFAULT_MAX_OUTPUT_TOKENS`,
 *   `COMPARISON_DEFAULT_TIMEOUT_SECONDS`); a revision in force keeps its own for a kind the form changes, and these apply to a kind it has none for.
 * - **«Свой набор» has no table.** A custom revision stored without comparison cells has none: the comparison is then refused by the server, so
 *   the form shows the four rows empty and says so. **Nothing here invents a model for a kind nobody chose.**
 */

import type { ComparisonLayoutKind, ModelEffort, StageComparisonCell, StageModelLayout } from '@/shared/api';
import { COMPARISON_LAYOUT_KIND_VALUES } from '@/shared/api';

import type { NamedKit } from './kits';
import { cellText } from './table';
import { COMPARISON_KIND_LABELS } from './vocabulary';

/** The answer limit, in tokens, of each kind: the constant its module carried before the layout. */
export const COMPARISON_DEFAULT_TOKENS: Readonly<Record<ComparisonLayoutKind, number>> = {
  comparison_pair_check: 1200,
  comparison_sheet_changes: 8192,
  comparison_spec: 32000,
  comparison_report: 8000,
};

/** The call window, in seconds, of each kind, as the original sets it. */
export const COMPARISON_DEFAULT_TIMEOUT: Readonly<Record<ComparisonLayoutKind, number>> = {
  comparison_pair_check: 900,
  comparison_sheet_changes: 1800,
  comparison_spec: 900,
  comparison_report: 2400,
};

/** The effort a kind takes when a model is first chosen for it in «Свой набор»: both sets, and the original, use the high one. */
export const COMPARISON_DEFAULT_EFFORT: ModelEffort = 'high';

interface KitPair { readonly model_id: string; readonly effort: ModelEffort }
type KitComparisonTable = Readonly<Record<ComparisonLayoutKind, KitPair>>;

const SONNET: KitPair = { model_id: 'claude-sonnet-5-5', effort: 'high' };
const ASTRA: KitPair = { model_id: 'gpt-6-astra', effort: 'high' };
const SOL_61: KitPair = { model_id: 'gpt-6.1-sol', effort: 'high' };

const CLAUDE_ONLY: KitComparisonTable = {
  comparison_pair_check: SONNET,
  comparison_sheet_changes: SONNET,
  comparison_spec: SONNET,
  comparison_report: SONNET,
};

const CODEX_ONLY: KitComparisonTable = {
  comparison_pair_check: ASTRA,
  comparison_sheet_changes: SOL_61,
  comparison_spec: ASTRA,
  comparison_report: SOL_61,
};

const KIT_TABLES: Readonly<Record<NamedKit, KitComparisonTable>> = { claude_only: CLAUDE_ONLY, codex_only: CODEX_ONLY };

/** The key the server gives the cell of a kind, `<kind>:main`; the keys of `unavailable_cell_keys` are these. */
export function comparisonCellKey(kind: ComparisonLayoutKind): string {
  return `${kind}:main`;
}

/** The (model, effort) pair of every kind of a set, in the order of the kinds. */
export function comparisonKitPairs(kit: NamedKit): readonly KitPair[] {
  return COMPARISON_LAYOUT_KIND_VALUES.map((kind) => KIT_TABLES[kit][kind]);
}

/**
 * The four comparison cells of a set. A kind the draft or the revision already has keeps its limits; the rest take the constants of the
 * code. The kind is the cell's own row, so the order is the order of the kinds.
 */
export function comparisonKitCells(kit: NamedKit, current: readonly StageComparisonCell[]): StageComparisonCell[] {
  return COMPARISON_LAYOUT_KIND_VALUES.map((kind) => {
    const had = current.find((candidate) => candidate.work_kind === kind);
    return {
      work_kind: kind,
      model_id: KIT_TABLES[kit][kind].model_id,
      effort: KIT_TABLES[kit][kind].effort,
      max_output_tokens: had?.max_output_tokens ?? COMPARISON_DEFAULT_TOKENS[kind],
      timeout_seconds: had?.timeout_seconds ?? COMPARISON_DEFAULT_TIMEOUT[kind],
    };
  });
}

/** The cell a model is first chosen for in «Свой набор»: the model, the effort the caller allows, the constants of the code for the limits. */
export function newComparisonCell(kind: ComparisonLayoutKind, modelId: string, effort: ModelEffort): StageComparisonCell {
  return {
    work_kind: kind,
    model_id: modelId,
    effort,
    max_output_tokens: COMPARISON_DEFAULT_TOKENS[kind],
    timeout_seconds: COMPARISON_DEFAULT_TIMEOUT[kind],
  };
}

/** The cells in the order of the kinds, whatever order they came in; a kind that is not one of the four is left out. */
export function sortedComparisonCells(cells: readonly StageComparisonCell[]): StageComparisonCell[] {
  return COMPARISON_LAYOUT_KIND_VALUES.flatMap((kind) => cells.filter((cell) => cell.work_kind === kind).slice(0, 1));
}

export interface ComparisonReading {
  readonly kind: ComparisonLayoutKind;
  /** «Пары листов». */
  readonly label: string;
  readonly effort: ModelEffort;
  /** «Sonnet 5.5 · высокое». */
  readonly text: string;
  /** The server names the cell's model as served by no server now. */
  readonly unavailable: boolean;
}

/**
 * The comparison cells of the revision in force, one line per kind in the order of the kinds. A revision with none (a «Свой набор» saved
 * before the cells, or without them) has no line: nothing is invented to fill the four.
 */
export function comparisonTable(layout: StageModelLayout): readonly ComparisonReading[] {
  const unavailable = new Set(layout.unavailable_cell_keys);
  return sortedComparisonCells(layout.current?.comparison_cells ?? []).map((cell) => ({
    kind: cell.work_kind,
    label: COMPARISON_KIND_LABELS[cell.work_kind],
    effort: cell.effort,
    text: cellText(cell),
    unavailable: unavailable.has(comparisonCellKey(cell.work_kind)),
  }));
}
