/**
 * The draft of a revision of the layout (`HOSTS-WEB-01`, plan 2026-11-09 §4.3 and §7.4): pure functions, so each rule of the
 * form is a function a test calls.
 *
 * A draft is a set and the six cells. Choosing «Только Claude» or «Только Codex» fills the cells from the set; any edit of a
 * cell after that makes the draft «Свой набор» (plan §4.3: «Свой набор» is any edit of an administrator). **Every cell must be a
 * pair of the catalogue** (a model with an effort it allows): the form offers only such pairs, and the server checks again.
 * A model is offered when some server can serve it now, and the model already in the cell is offered too, so a draft never
 * silently drops what is in force.
 *
 * **The comparison cells** (`CMP-WEB-01`): a draft also holds the four cells of the comparison of versions. A named set fills them from
 * its table, as it fills the six rows; «Свой набор» holds what the revision stored, and a revision stored without them holds none, so
 * the four rows are empty and nothing is invented. Either all four are chosen or none (the server refuses anything between), and a
 * request carries them only when they are chosen.
 */

import type {
  ComparisonLayoutKind,
  ModelCatalogue,
  ModelEffort,
  ReviseStageModelLayoutRequest,
  StageComparisonCell,
  StageLayoutCell,
  StageModelKit,
  StageModelLayout,
} from '@/shared/api';
import { COMPARISON_LAYOUT_KIND_VALUES, STAGE_ROW_KEY_VALUES } from '@/shared/api';
import {
  BLOCKS_SCHEME_PROBLEM,
  BLOCK_SCHEMES,
  COMPARISON_DEFAULT_EFFORT,
  COMPARISON_PAIR_PROBLEM,
  COMPARISON_PARTIAL_PROBLEM,
  NAMED_KITS,
  blockSchemeCells,
  blockSchemeIsOffered,
  blockSchemeOf,
  comparisonKitCells,
  effortsOf,
  isNamedKit,
  kitCells,
  kitIsOffered,
  newComparisonCell,
  pairIsInCatalogue,
  rowCells,
  sortedComparisonCells,
} from '@/entities/stage-layout';
import type { BlockScheme, BlockSchemeId, NamedKit } from '@/entities/stage-layout';

export interface LayoutDraft {
  readonly kit: StageModelKit;
  readonly cells: readonly StageLayoutCell[];
  /** The comparison cells chosen so far, each kind at most once; absent or empty: none chosen. */
  readonly comparison?: readonly StageComparisonCell[] | undefined;
}

/** The sets the form offers: those every server-served model of which is in the catalogue, then «Свой набор». */
export function offeredKits(
  catalogue: ModelCatalogue | undefined,
  availableModelIds: readonly string[],
  currentKit: StageModelKit | undefined,
): readonly StageModelKit[] {
  const named = NAMED_KITS.filter((kit) => kitIsOffered(kit, catalogue, availableModelIds) || kit === currentKit);
  return [...named, 'custom'];
}

/** Where the form starts: the revision in force, or else the first set that can be offered. `null`: nothing to start from. */
export function initialDraft(
  layout: StageModelLayout,
  catalogue: ModelCatalogue | undefined,
  availableModelIds: readonly string[],
): LayoutDraft | null {
  if (layout.current !== undefined) {
    return {
      kit: layout.current.kit,
      cells: layout.current.cells.map((cell) => ({ ...cell })),
      comparison: sortedComparisonCells(layout.current.comparison_cells ?? []).map((cell) => ({ ...cell })),
    };
  }
  const first = NAMED_KITS.find((kit) => kitIsOffered(kit, catalogue, availableModelIds));
  return first === undefined ? null : { kit: first, cells: kitCells(first), comparison: comparisonKitCells(first) };
}

/** Choosing a set. «Свой набор» keeps the cells as they are. */
export function chooseKit(draft: LayoutDraft, kit: StageModelKit): LayoutDraft {
  if (!isNamedKit(kit)) return { ...draft, kit: 'custom' };
  return { kit, cells: kitCells(kit as NamedKit), comparison: comparisonKitCells(kit as NamedKit) };
}

function replaceCell(draft: LayoutDraft, cellKey: string, change: (cell: StageLayoutCell) => StageLayoutCell): LayoutDraft {
  return { ...draft, kit: 'custom', cells: draft.cells.map((cell) => (cell.cell_key === cellKey ? change(cell) : cell)) };
}

/** The effort a cell takes when its model changes: the one it had if the new model allows it, else `medium`, else the first. */
function effortFor(catalogue: ModelCatalogue | undefined, modelId: string, wanted: ModelEffort): ModelEffort {
  const allowed = effortsOf(catalogue, modelId);
  if (allowed.includes(wanted)) return wanted;
  if (allowed.includes('medium')) return 'medium';
  return allowed[0] ?? wanted;
}

export function setCellModel(draft: LayoutDraft, cellKey: string, modelId: string, catalogue: ModelCatalogue | undefined): LayoutDraft {
  return replaceCell(draft, cellKey, (cell) => ({ ...cell, model_id: modelId, effort: effortFor(catalogue, modelId, cell.effort) }));
}

export function setCellEffort(draft: LayoutDraft, cellKey: string, effort: ModelEffort): LayoutDraft {
  return replaceCell(draft, cellKey, (cell) => ({ ...cell, effort }));
}

/**
 * The blocks row is chosen as one scheme of the closed list (`HOSTS-ENSEMBLE-01`), never cell by cell: the cells of the other
 * rows stay as they are and the cells of the row become the scheme's.
 */
export function setBlockScheme(draft: LayoutDraft, schemeId: BlockSchemeId): LayoutDraft {
  const chosen = BLOCK_SCHEMES.find((candidate) => candidate.id === schemeId);
  if (chosen === undefined) return draft;
  const cells = STAGE_ROW_KEY_VALUES.flatMap((row) => (row === 'blocks' ? blockSchemeCells(chosen) : rowCells(draft.cells, row)));
  return { ...draft, kit: 'custom', cells };
}

function replaceComparison(
  draft: LayoutDraft,
  kind: ComparisonLayoutKind,
  change: (cell: StageComparisonCell | undefined) => StageComparisonCell | undefined,
): LayoutDraft {
  const own = draft.comparison ?? [];
  const next = change(own.find((cell) => cell.work_kind === kind));
  const rest = own.filter((cell) => cell.work_kind !== kind);
  return { ...draft, kit: 'custom', comparison: sortedComparisonCells(next === undefined ? rest : [...rest, next]) };
}

/**
 * A model for one kind of the comparison of versions. A kind that has none yet takes the model, the high effort the catalogue allows
 * for it (else the effort `effortFor` falls back to); a kind that has one keeps its effort where the new model allows it.
 */
export function setComparisonModel(
  draft: LayoutDraft,
  kind: ComparisonLayoutKind,
  modelId: string,
  catalogue: ModelCatalogue | undefined,
): LayoutDraft {
  return replaceComparison(draft, kind, (cell) => (cell === undefined
    ? newComparisonCell(kind, modelId, effortFor(catalogue, modelId, COMPARISON_DEFAULT_EFFORT))
    : { ...cell, model_id: modelId, effort: effortFor(catalogue, modelId, cell.effort) }));
}

export function setComparisonEffort(draft: LayoutDraft, kind: ComparisonLayoutKind, effort: ModelEffort): LayoutDraft {
  return replaceComparison(draft, kind, (cell) => (cell === undefined ? undefined : { ...cell, effort }));
}

/**
 * The schemes the blocks row offers: those every model of which some server can serve and the catalogue names with that effort,
 * and the scheme the row already is (so a draft never silently drops what is in force).
 */
export function offeredBlockSchemes(
  draft: LayoutDraft,
  catalogue: ModelCatalogue | undefined,
  availableModelIds: readonly string[],
): readonly BlockScheme[] {
  const own = blockSchemeOf(draft.cells);
  return BLOCK_SCHEMES.filter((candidate) => candidate === own || blockSchemeIsOffered(candidate, catalogue, availableModelIds));
}

/** The models a cell offers: what some server can serve and the catalogue names, and the model the cell has (a comparison kind with none has none). */
export function modelOptions(
  cell: Pick<StageLayoutCell, 'model_id'> | undefined,
  catalogue: ModelCatalogue | undefined,
  availableModelIds: readonly string[],
): readonly string[] {
  const named = new Set((catalogue?.items ?? []).map((entry) => entry.model_id));
  const offered = availableModelIds.filter((id) => named.has(id));
  return cell === undefined || offered.includes(cell.model_id) ? offered : [cell.model_id, ...offered];
}

/** What stops the draft from being saved, in words; `null` when it can be saved. */
export function draftProblem(draft: LayoutDraft, catalogue: ModelCatalogue | undefined): string | null {
  if (draft.cells.length === 0) return 'Набор моделей пуст: выберите модели по этапам.';
  for (const cell of draft.cells) {
    if (!pairIsInCatalogue(catalogue, cell.model_id, cell.effort)) {
      return 'Для одной из строк выбрано сочетание модели и усилия, которого нет в каталоге.';
    }
  }
  // The comparison cells are all four or none: the server refuses a layout that names some kinds and not others.
  const comparison = draft.comparison ?? [];
  if (comparison.length > 0 && comparison.length !== COMPARISON_LAYOUT_KIND_VALUES.length) return COMPARISON_PARTIAL_PROBLEM;
  for (const cell of comparison) {
    if (!pairIsInCatalogue(catalogue, cell.model_id, cell.effort)) return COMPARISON_PAIR_PROBLEM;
  }
  // The blocks row is one of the three schemes; a revision of any other pairing is refused by the server (`block_scheme_not_listed`).
  if (draft.cells.some((cell) => cell.row === 'blocks') && blockSchemeOf(draft.cells) === null) return BLOCKS_SCHEME_PROBLEM;
  return null;
}

/**
 * The request: the kit and every cell, and the comparison cells **when any are chosen** — all four, each kind once, in the order of the
 * kinds. A «Свой набор» with none chosen sends none, so the server stores none and refuses a comparison rather than serving it with a
 * model nobody chose; a named set sends its table.
 */
export function draftRequest(draft: LayoutDraft): ReviseStageModelLayoutRequest {
  const comparison = sortedComparisonCells(draft.comparison ?? []);
  return {
    kit: draft.kit,
    cells: draft.cells.map((cell) => ({ ...cell })),
    ...(comparison.length > 0 ? { comparison_cells: comparison.map((cell) => ({ ...cell })) } : {}),
  };
}

/** Whether the draft differs from the revision in force (nothing is saved for an unchanged draft). */
export function draftChanged(draft: LayoutDraft, layout: StageModelLayout): boolean {
  const current = layout.current;
  if (current === undefined) return true;
  if (current.kit !== draft.kit || current.cells.length !== draft.cells.length) return true;
  const cellsChanged = draft.cells.some((cell) => {
    const was = rowCells(current.cells, cell.row).find((other) => other.cell_key === cell.cell_key);
    return was === undefined || was.model_id !== cell.model_id || was.effort !== cell.effort;
  });
  if (cellsChanged) return true;
  const comparison = draft.comparison ?? [];
  const stored = current.comparison_cells ?? [];
  return comparison.length !== stored.length || comparison.some((cell) => {
    const was = stored.find((other) => other.work_kind === cell.work_kind);
    return was === undefined || was.model_id !== cell.model_id || was.effort !== cell.effort;
  });
}
