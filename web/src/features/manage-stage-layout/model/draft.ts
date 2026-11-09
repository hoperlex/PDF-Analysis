/**
 * The draft of a revision of the layout (`HOSTS-WEB-01`, plan 2026-11-09 §4.3 and §7.4): pure functions, so each rule of the
 * form is a function a test calls.
 *
 * A draft is a set and the six cells. Choosing «Только Claude» or «Только Codex» fills the cells from the set; any edit of a
 * cell after that makes the draft «Свой набор» (plan §4.3: «Свой набор» is any edit of an administrator). **Every cell must be a
 * pair of the catalogue** (a model with an effort it allows): the form offers only such pairs, and the server checks again.
 * A model is offered when some server can serve it now, and the model already in the cell is offered too, so a draft never
 * silently drops what is in force.
 */

import type {
  ModelCatalogue,
  ModelEffort,
  ReviseStageModelLayoutRequest,
  StageLayoutCell,
  StageModelKit,
  StageModelLayout,
} from '@/shared/api';
import {
  NAMED_KITS,
  effortsOf,
  isNamedKit,
  kitCells,
  kitIsOffered,
  pairIsInCatalogue,
  rowCells,
} from '@/entities/stage-layout';
import type { NamedKit } from '@/entities/stage-layout';

export interface LayoutDraft {
  readonly kit: StageModelKit;
  readonly cells: readonly StageLayoutCell[];
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
  if (layout.current !== undefined) return { kit: layout.current.kit, cells: layout.current.cells.map((cell) => ({ ...cell })) };
  const first = NAMED_KITS.find((kit) => kitIsOffered(kit, catalogue, availableModelIds));
  return first === undefined ? null : { kit: first, cells: kitCells(first, []) };
}

/** Choosing a set. «Свой набор» keeps the cells as they are. */
export function chooseKit(draft: LayoutDraft, kit: StageModelKit): LayoutDraft {
  if (!isNamedKit(kit)) return { kit: 'custom', cells: draft.cells };
  return { kit, cells: kitCells(kit as NamedKit, draft.cells) };
}

function replaceCell(draft: LayoutDraft, cellKey: string, change: (cell: StageLayoutCell) => StageLayoutCell): LayoutDraft {
  return { kit: 'custom', cells: draft.cells.map((cell) => (cell.cell_key === cellKey ? change(cell) : cell)) };
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

export function setCellLimit(draft: LayoutDraft, cellKey: string, field: 'max_output_tokens' | 'timeout_seconds', value: number): LayoutDraft {
  return replaceCell(draft, cellKey, (cell) => ({ ...cell, [field]: value }));
}

/** The models a cell offers: what some server can serve and the catalogue names, and the model the cell has. */
export function modelOptions(
  cell: StageLayoutCell,
  catalogue: ModelCatalogue | undefined,
  availableModelIds: readonly string[],
): readonly string[] {
  const named = new Set((catalogue?.items ?? []).map((entry) => entry.model_id));
  const offered = availableModelIds.filter((id) => named.has(id));
  return offered.includes(cell.model_id) ? offered : [cell.model_id, ...offered];
}

const TOKENS = { min: 1, max: 65536 } as const;
const TIMEOUT = { min: 1, max: 7200 } as const;

/** What stops the draft from being saved, in words; `null` when it can be saved. */
export function draftProblem(draft: LayoutDraft, catalogue: ModelCatalogue | undefined): string | null {
  if (draft.cells.length === 0) return 'Набор моделей пуст: выберите модели по этапам.';
  for (const cell of draft.cells) {
    if (!pairIsInCatalogue(catalogue, cell.model_id, cell.effort)) {
      return 'Для одной из строк выбрано сочетание модели и усилия, которого нет в каталоге.';
    }
    if (!Number.isInteger(cell.max_output_tokens) || cell.max_output_tokens < TOKENS.min || cell.max_output_tokens > TOKENS.max) {
      return `Ответ, токенов — целое число от ${TOKENS.min} до ${TOKENS.max}.`;
    }
    if (!Number.isInteger(cell.timeout_seconds) || cell.timeout_seconds < TIMEOUT.min || cell.timeout_seconds > TIMEOUT.max) {
      return `Таймаут — целое число секунд от ${TIMEOUT.min} до ${TIMEOUT.max}.`;
    }
  }
  return null;
}

export function draftRequest(draft: LayoutDraft): ReviseStageModelLayoutRequest {
  return { kit: draft.kit, cells: draft.cells.map((cell) => ({ ...cell })) };
}

/** Whether the draft differs from the revision in force (nothing is saved for an unchanged draft). */
export function draftChanged(draft: LayoutDraft, layout: StageModelLayout): boolean {
  const current = layout.current;
  if (current === undefined) return true;
  if (current.kit !== draft.kit || current.cells.length !== draft.cells.length) return true;
  return draft.cells.some((cell) => {
    const was = rowCells(current.cells, cell.row).find((other) => other.cell_key === cell.cell_key);
    return was === undefined || was.model_id !== cell.model_id || was.effort !== cell.effort
      || was.max_output_tokens !== cell.max_output_tokens || was.timeout_seconds !== cell.timeout_seconds;
  });
}
