/**
 * The schemes of the blocks row (`HOSTS-ENSEMBLE-01`, ADR-0028 decisions 11 and 12): a **closed list of three**, and the row is
 * one of them or nothing. The legs and the judge of an ensemble are never edited one by one.
 *
 * - `claude_opus_judge_sonnet`: one Opus leg and a Sonnet judge (`blocks:leg1`, `blocks:judge`), the set «Только Claude»;
 * - `codex_astra_sol_judge`: two Codex legs and a judge (`blocks:leg1`, `blocks:leg2`, `blocks:judge`), the set «Только Codex»;
 * - `codex_astra_single`: one Astra, `blocks:main`, which the original allows.
 *
 * A single Claude on the blocks row is not on the list and never will be: the server refuses it (`block_scheme_not_listed`).
 *
 * This is the same list as `BLOCK_SCHEMES` of `src/auditmanager/runs/stage_layout.py`; the server validates a revision against its
 * own copy, so a copy that drifted here is refused, never stored. A scheme is read off a draft by (role, model, effort) of its
 * cells and nothing else. The names the form shows are derived from the models, so a model is called what it is called everywhere
 * (`modelLabel`); no name is typed twice.
 */

import type { ModelEffort, StageCellRole, StageLayoutCell } from '@/shared/api';
import { modelLabel } from '@/entities/executor-host';

export const BLOCK_SCHEME_IDS = ['claude_opus_judge_sonnet', 'codex_astra_sol_judge', 'codex_astra_single'] as const;
export type BlockSchemeId = (typeof BLOCK_SCHEME_IDS)[number];

export interface BlockSchemeCell {
  readonly role: StageCellRole;
  readonly model_id: string;
  readonly effort: ModelEffort;
}

export interface BlockScheme {
  readonly id: BlockSchemeId;
  /** «Opus 5.5, судья Sonnet 5.5»: the models, said once each in the order of the roles. */
  readonly label: string;
  /** The cells in the order of the roles: `main`, the legs, the judge. */
  readonly cells: readonly BlockSchemeCell[];
}

const OPUS = 'claude-opus-5-5';
const SONNET = 'claude-sonnet-5-5';
const SOL_61 = 'gpt-6.1-sol';
const SOL = 'gpt-6-sol';
const ASTRA = 'gpt-6-astra';

/** «Opus 5.5, судья Sonnet 5.5»; a scheme with no judge says so: «gpt-6-astra, без судьи». */
export function schemeLabel(cells: readonly BlockSchemeCell[]): string {
  const legs = cells.filter((cell) => cell.role !== 'judge').map((cell) => modelLabel(cell.model_id)).join(' + ');
  const judge = cells.find((cell) => cell.role === 'judge');
  return judge === undefined ? `${legs}, без судьи` : `${legs}, судья ${modelLabel(judge.model_id)}`;
}

function scheme(id: BlockSchemeId, cells: readonly BlockSchemeCell[]): BlockScheme {
  return { id, label: schemeLabel(cells), cells };
}

export const BLOCK_SCHEMES: readonly BlockScheme[] = [
  scheme('claude_opus_judge_sonnet', [
    { role: 'leg1', model_id: OPUS, effort: 'medium' },
    { role: 'judge', model_id: SONNET, effort: 'medium' },
  ]),
  scheme('codex_astra_sol_judge', [
    { role: 'leg1', model_id: ASTRA, effort: 'medium' },
    { role: 'leg2', model_id: SOL, effort: 'medium' },
    { role: 'judge', model_id: SOL_61, effort: 'medium' },
  ]),
  scheme('codex_astra_single', [{ role: 'main', model_id: ASTRA, effort: 'medium' }]),
];

export function blockSchemeById(id: BlockSchemeId): BlockScheme {
  return BLOCK_SCHEMES.find((candidate) => candidate.id === id) as BlockScheme;
}

const ROLE_POSITION: Readonly<Record<StageCellRole, number>> = { main: 0, leg1: 1, leg2: 2, judge: 3 };

/**
 * The scheme the blocks cells of a draft or a revision are, or `null` when they are none of the three (a revision stored before
 * the list was closed, or a draft that has not chosen). Cells of other rows are ignored.
 */
export function blockSchemeOf(cells: readonly Pick<StageLayoutCell, 'row' | 'role' | 'model_id' | 'effort'>[]): BlockScheme | null {
  const own = cells
    .filter((cell) => cell.row === 'blocks')
    .sort((a, b) => ROLE_POSITION[a.role] - ROLE_POSITION[b.role]);
  if (own.length === 0) return null;
  return BLOCK_SCHEMES.find((candidate) => candidate.cells.length === own.length
    && candidate.cells.every((cell, at) => {
      const other = own[at] as (typeof own)[number];
      return cell.role === other.role && cell.model_id === other.model_id && cell.effort === other.effort;
    })) ?? null;
}
