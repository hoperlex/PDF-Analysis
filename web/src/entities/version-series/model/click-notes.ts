/**
 * What a click on a sheet says when there is no pair to open (`version-comparison.js:1220-1250`, `:1274-1278`).
 *
 * A thumbnail of the matrix opens the viewer when its row has a finished pair in the chosen transition A → B.
 * When it has none, the reader is told why in a sentence, and the sentence is chosen here from facts the
 * matrix and the series already hold — never a silent no-op, and never a viewer opened on a sheet with
 * nothing to compare.
 */

import type { ComparisonMatrixColumn, ComparisonSheetPair } from '@/shared/api';

import type { Sides } from './matrix-view';
import { adjacentSides, validSides } from './matrix-view';

export const ONE_VERSION_NOTE = 'В проекте одна версия — сравнивать не с чем.';
export const CHOOSE_TWO_DIFFERENT = 'Выберите две разные версии.';
export const CHAIN_NOTE =
  'Пара собрана по цепочке через промежуточные версии и не сравнивалась: сравниваются только соседние версии.';
export const PAIR_NOT_READY = 'Сравнение этого листа ещё не готово.';

export interface ClickContext {
  readonly columns: readonly ComparisonMatrixColumn[];
  readonly sides: Sides;
  readonly names: ReadonlyMap<string, string>;
  /** Whether a transition A → B has been compared at all (the series has it). */
  readonly transitionExists: boolean;
  /** The pair of the clicked row in A → B, if there is one. */
  readonly pair: ComparisonSheetPair | null;
  /** The version column of the clicked sheet. */
  readonly versionUid: string;
}

export type ClickAnswer = { readonly open: ComparisonSheetPair } | { readonly note: string };

export function answerClick(context: ClickContext): ClickAnswer {
  const { columns, sides, names, transitionExists, pair, versionUid } = context;
  if (columns.length < 2) return { note: ONE_VERSION_NOTE };
  if (!validSides(sides, columns)) return { note: CHOOSE_TWO_DIFFERENT };
  if (!adjacentSides(sides, columns)) return { note: CHAIN_NOTE };
  const a = names.get(sides.a ?? '') ?? '№?';
  const b = names.get(sides.b ?? '') ?? '№?';
  if (!transitionExists) {
    return {
      note: `Переход ${a} → ${b} ещё не посчитан: запустите «Сравнение соседних» на вкладке «Проекты и этапы».`,
    };
  }
  if (pair === null) {
    const other = versionUid === sides.a ? b : a;
    return { note: `У листа нет пары в версии ${other}.` };
  }
  if (pair.state !== 'done' || pair.status === undefined) return { note: PAIR_NOT_READY };
  return { open: pair };
}
