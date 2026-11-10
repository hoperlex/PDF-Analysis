/**
 * The sets of models (`HOSTS-WEB-01`, plan 2026-11-09 §4.3): «Только Claude» and «Только Codex», as the original's
 * `docs/claude_only_mode.md` and `docs/codex_only_mode.md` name them, «модель · усилие» for each of the six rows.
 *
 * **These are choices offered to an administrator, not a rule.** A set only fills the form; the server accepts a revision
 * only if every cell is a pair of the model catalogue (`listModelCatalogue`), and a set is offered only when every model it
 * names is served by some server now. The blocks row of a set is one of the three schemes of the closed list
 * (`./block-schemes.ts`, `HOSTS-ENSEMBLE-01`): «Только Claude» is an Opus leg and a Sonnet judge, «Только Codex» is two legs and a
 * judge, so a set has more than six cells, and the legs and the judge count as models of the set.
 *
 * A cell is a model and an effort, and nothing about the length of an answer or the time of a call (`LIMITS-01`, `R-153n` and
 * `R-153o`): no answer cap reaches a model, and the window of a call is a constant of the server, from the original. The form has no
 * field for either, and the web keeps no copy of them.
 */

import type {
  ModelCatalogue,
  ModelEffort,
  StageCellRole,
  StageLayoutCell,
  StageModelKit,
  StageRowKey,
} from '@/shared/api';
import { STAGE_ROW_KEY_VALUES } from '@/shared/api';

import { blockSchemeById } from './block-schemes';
import type { BlockScheme } from './block-schemes';
import { comparisonKitPairs } from './comparison';

interface KitCell { readonly role: StageCellRole; readonly model_id: string; readonly effort: ModelEffort }

/** One cell of a row that has a single answer. */
const main = (model_id: string, effort: ModelEffort = 'medium'): readonly KitCell[] => [{ role: 'main', model_id, effort }];

/** The cells of a scheme, as a set's row. */
const scheme = (candidate: BlockScheme): readonly KitCell[] => candidate.cells.map((cell) => ({ ...cell }));

type KitTable = Readonly<Record<StageRowKey, readonly KitCell[]>>;

const CLAUDE_ONLY: KitTable = {
  text: main('claude-sonnet-5-5'),
  blocks: scheme(blockSchemeById('claude_opus_judge_sonnet')),
  cross_check: main('claude-sonnet-5-5'),
  norms: main('claude-sonnet-5-5'),
  review: main('claude-sonnet-5-5'),
  correction: main('claude-sonnet-5-5'),
};

const CODEX_ONLY: KitTable = {
  text: main('gpt-6.1-sol'),
  blocks: scheme(blockSchemeById('codex_astra_sol_judge')),
  cross_check: main('gpt-6-sol'),
  norms: main('gpt-6-astra'),
  review: main('gpt-6-sol'),
  correction: main('gpt-6.1-sol'),
};

/** The two named sets; «Свой набор» has no table, it is any edit. */
export const NAMED_KITS = ['claude_only', 'codex_only'] as const satisfies readonly StageModelKit[];
export type NamedKit = (typeof NAMED_KITS)[number];

const KIT_TABLES: Readonly<Record<NamedKit, KitTable>> = {
  claude_only: CLAUDE_ONLY,
  codex_only: CODEX_ONLY,
};

export function isNamedKit(kit: StageModelKit): kit is NamedKit {
  return kit === 'claude_only' || kit === 'codex_only';
}

export function cellKeyOf(row: StageRowKey, role: StageLayoutCell['role'] = 'main'): string {
  return `${row}:${role}`;
}

/** Every cell of a set, row by row, in the order of the roles inside a row. */
function kitTable(kit: NamedKit): readonly { readonly row: StageRowKey; readonly cell: KitCell }[] {
  return STAGE_ROW_KEY_VALUES.flatMap((row) => KIT_TABLES[kit][row].map((cell) => ({ row, cell })));
}

/**
 * The models a set names, the legs and the judge of the blocks row among them, and the models of its four comparison cells
 * (`./comparison.ts`).
 */
export function kitModelIds(kit: NamedKit): readonly string[] {
  return [...new Set([...kitTable(kit).map(({ cell }) => cell.model_id), ...comparisonKitPairs(kit).map((pair) => pair.model_id)])];
}

/** The cells of a set, row by row, in the order of the roles inside a row. */
export function kitCells(kit: NamedKit): StageLayoutCell[] {
  return kitTable(kit).map(({ row, cell }) => ({
    cell_key: cellKeyOf(row, cell.role),
    row,
    role: cell.role,
    model_id: cell.model_id,
    effort: cell.effort,
  }));
}

/** The cells of the blocks row for a scheme. */
export function blockSchemeCells(candidate: BlockScheme): StageLayoutCell[] {
  return candidate.cells.map((cell) => ({
    cell_key: cellKeyOf('blocks', cell.role),
    row: 'blocks',
    role: cell.role,
    model_id: cell.model_id,
    effort: cell.effort,
  }));
}

/** The efforts the catalogue allows for a model, or none when the catalogue does not name it. */
export function effortsOf(catalogue: ModelCatalogue | undefined, modelId: string): readonly ModelEffort[] {
  const efforts = new Set<ModelEffort>();
  for (const entry of catalogue?.items ?? []) {
    if (entry.model_id === modelId) for (const effort of entry.efforts) efforts.add(effort);
  }
  return [...efforts];
}

/** Whether (model, effort) is a pair of the catalogue. */
export function pairIsInCatalogue(catalogue: ModelCatalogue | undefined, modelId: string, effort: ModelEffort): boolean {
  return effortsOf(catalogue, modelId).includes(effort);
}

/** Whether every cell is a pair of the catalogue and its model is served by some server now. */
function cellsAreOffered(
  cells: readonly { readonly model_id: string; readonly effort: ModelEffort }[],
  catalogue: ModelCatalogue | undefined,
  availableModelIds: readonly string[],
): boolean {
  const available = new Set(availableModelIds);
  return cells.every((cell) => available.has(cell.model_id) && pairIsInCatalogue(catalogue, cell.model_id, cell.effort));
}

/**
 * Whether a set can be offered: every cell of it (the legs and the judge of the blocks row, and the four comparison cells, too) is a
 * pair of the catalogue, and every model it names is served by some server now. A set that cannot be used is not drawn (plan §6: an unavailable thing is not
 * listed).
 */
export function kitIsOffered(kit: NamedKit, catalogue: ModelCatalogue | undefined, availableModelIds: readonly string[]): boolean {
  return cellsAreOffered([...kitTable(kit).map(({ cell }) => cell), ...comparisonKitPairs(kit)], catalogue, availableModelIds);
}

/** Whether a scheme of the blocks row can be offered, on the same terms as a set. */
export function blockSchemeIsOffered(
  candidate: BlockScheme,
  catalogue: ModelCatalogue | undefined,
  availableModelIds: readonly string[],
): boolean {
  return cellsAreOffered(candidate.cells, catalogue, availableModelIds);
}
