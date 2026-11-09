/**
 * The sets of models (`HOSTS-WEB-01`, plan 2026-11-09 §4.3): «Только Claude» and «Только Codex», as the original's
 * `docs/claude_only_mode.md` and `docs/codex_only_mode.md` name them, «модель · усилие» for each of the six rows.
 *
 * **These are choices offered to an administrator, not a rule.** A set only fills the form; the server accepts a revision
 * only if every cell is a pair of the model catalogue (`listModelCatalogue`), and a set is offered only when every model it
 * names is served by some server now. The ensemble of the blocks row (two legs and a judge) arrives in wave 2; until then the
 * blocks row of each set is its single leg, and the plan names the set so («Только Claude (блоки без судьи)»).
 *
 * The limits of a cell (answer tokens, timeout) are today's constants of the code (ADR-0028: 16000, 6000 and 12000 tokens);
 * a revision in force keeps its own limits for a cell the form changes, and these apply only to a cell the revision has not
 * got. The timeout has no constant in the code to copy for the new kinds of cell; the default is the ceiling of one attempt
 * of the proxy path (`DEFAULT_TIMEOUT_SECONDS`) and the server bounds it (1 to 7200).
 */

import type {
  ModelCatalogue,
  ModelEffort,
  StageLayoutCell,
  StageModelKit,
  StageRowKey,
} from '@/shared/api';
import { STAGE_ROW_KEY_VALUES } from '@/shared/api';

export const DEFAULT_TIMEOUT_SECONDS = 600;

/** The answer limits that are constants of the code today. */
export const DEFAULT_ANSWER_TOKENS: Readonly<Record<StageRowKey, number>> = {
  text: 16000,
  blocks: 6000,
  cross_check: 6000,
  norms: 12000,
  review: 6000,
  correction: 6000,
};

interface KitCell { readonly model_id: string; readonly effort: ModelEffort }

const CLAUDE_ONLY: Readonly<Record<StageRowKey, KitCell>> = {
  text: { model_id: 'claude-sonnet-5-5', effort: 'medium' },
  blocks: { model_id: 'claude-opus-5-5', effort: 'medium' },
  cross_check: { model_id: 'claude-sonnet-5-5', effort: 'medium' },
  norms: { model_id: 'claude-sonnet-5-5', effort: 'medium' },
  review: { model_id: 'claude-sonnet-5-5', effort: 'medium' },
  correction: { model_id: 'claude-sonnet-5-5', effort: 'medium' },
};

const CODEX_ONLY: Readonly<Record<StageRowKey, KitCell>> = {
  text: { model_id: 'gpt-6.1-sol', effort: 'medium' },
  blocks: { model_id: 'gpt-6-astra', effort: 'medium' },
  cross_check: { model_id: 'gpt-6-sol', effort: 'medium' },
  norms: { model_id: 'gpt-6-astra', effort: 'medium' },
  review: { model_id: 'gpt-6-sol', effort: 'medium' },
  correction: { model_id: 'gpt-6.1-sol', effort: 'medium' },
};

/** The two named sets; «Свой набор» has no table, it is any edit. */
export const NAMED_KITS = ['claude_only', 'codex_only'] as const satisfies readonly StageModelKit[];
export type NamedKit = (typeof NAMED_KITS)[number];

const KIT_TABLES: Readonly<Record<NamedKit, Readonly<Record<StageRowKey, KitCell>>>> = {
  claude_only: CLAUDE_ONLY,
  codex_only: CODEX_ONLY,
};

export function isNamedKit(kit: StageModelKit): kit is NamedKit {
  return kit === 'claude_only' || kit === 'codex_only';
}

export function cellKeyOf(row: StageRowKey, role: StageLayoutCell['role'] = 'main'): string {
  return `${row}:${role}`;
}

/** The models a set names. */
export function kitModelIds(kit: NamedKit): readonly string[] {
  return [...new Set(STAGE_ROW_KEY_VALUES.map((row) => KIT_TABLES[kit][row].model_id))];
}

/**
 * The cells of a set. A cell the revision in force already has keeps its limits; the rest take today's constants.
 */
export function kitCells(kit: NamedKit, current: readonly StageLayoutCell[]): StageLayoutCell[] {
  return STAGE_ROW_KEY_VALUES.map((row) => {
    const key = cellKeyOf(row);
    const had = current.find((cell) => cell.cell_key === key);
    const choice = KIT_TABLES[kit][row];
    return {
      cell_key: key,
      row,
      role: 'main',
      model_id: choice.model_id,
      effort: choice.effort,
      max_output_tokens: had?.max_output_tokens ?? DEFAULT_ANSWER_TOKENS[row],
      timeout_seconds: had?.timeout_seconds ?? DEFAULT_TIMEOUT_SECONDS,
    };
  });
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

/**
 * Whether a set can be offered: every cell of it is a pair of the catalogue, and every model it names is served by some
 * server now. A set that cannot be used is not drawn (plan §6: an unavailable thing is not listed).
 */
export function kitIsOffered(kit: NamedKit, catalogue: ModelCatalogue | undefined, availableModelIds: readonly string[]): boolean {
  const available = new Set(availableModelIds);
  return STAGE_ROW_KEY_VALUES.every((row) => {
    const choice = KIT_TABLES[kit][row];
    return available.has(choice.model_id) && pairIsInCatalogue(catalogue, choice.model_id, choice.effort);
  });
}
