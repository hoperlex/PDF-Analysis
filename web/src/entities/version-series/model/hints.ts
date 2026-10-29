/**
 * The AI flags and hints in the cells of the sheet matrix (`version-comparison.js:372-409`; seal §3 decision 4).
 *
 * The AI check of doubtful pairs writes no client-visible member of a cell. Its accepted answers become accepted AI links (the
 * matrix then marks the cell «ИИ»); every other answer is a **hint** read by `listComparisonAiPairHints`, and a client joins it to
 * a cell by `(version_uid, page)`: the hint's `version_uid` is the version of the cell it concerns and its `page` is the sheet of
 * the older version the question was about — which is a matched cell of the same row. Nothing here changes the matrix; a manual
 * edit wins over every hint.
 */

import type { ComparisonAiPairHint, ComparisonMatrixCell, ComparisonMatrixRow, ComparisonPageRef } from '@/shared/api';

import { PAIR_DECISION_LABELS } from './ai-words';
import { samePage } from './matrix-view';

/** The hints of one cell: those whose cell is in this version and whose sheet stands in this row. */
export function hintsFor(
  hints: readonly ComparisonAiPairHint[],
  row: ComparisonMatrixRow,
  cell: ComparisonMatrixCell,
): readonly ComparisonAiPairHint[] {
  return hints.filter(
    (hint) =>
      hint.version_uid === cell.version_uid &&
      row.cells.some((candidate) => candidate.page !== undefined && samePage(candidate.page, hint.page as ComparisonPageRef)),
  );
}

export type HintMark = 'moon' | 'doubt' | 'confirmed' | 'none';

/**
 * How a decision shows in the cell. «🌙 ИИ: вероятно стр. N» is a hint with a candidate page (an unmatched cell); «ИИ ?» is the AI
 * being **against** the algorithm's pair or unsure of it; the accepted link is the cell's own «ИИ» and needs no mark here; an
 * answer that was dropped or never came is said once, quietly.
 */
export function hintMark(hint: ComparisonAiPairHint): HintMark {
  switch (hint.decision) {
    case 'link_accepted': return 'confirmed';
    case 'hint_table':
    case 'hint_confidence':
    case 'hint_taken':
    case 'hint_shared':
    case 'hint_reverse': return hint.hint_page === undefined ? 'doubt' : 'moon';
    case 'none': return 'none';
    case 'medium_other':
    case 'medium_none':
    case 'medium_weak': return 'doubt';
    case 'medium_confirm': return 'confirmed';
    case 'answer_mismatch':
    case 'failed': return 'none';
  }
}

export const MOON = '🌙';

/** The short text drawn in the cell. */
export function hintText(hint: ComparisonAiPairHint): string {
  const mark = hintMark(hint);
  if (mark === 'moon' && hint.hint_page !== undefined) return `${MOON} ИИ: вероятно стр. ${hint.hint_page.page_number}`;
  if (mark === 'doubt') return 'ИИ ?';
  if (mark === 'confirmed') return 'ИИ ✓';
  return hint.decision === 'none' ? `${MOON} ИИ: подходящего листа нет` : 'ИИ: ответа нет';
}

/** The longer text, for a `title`: the decision in words and the model's own sentence, which is not confirmed by an engineer. */
export function hintTitle(hint: ComparisonAiPairHint): string {
  const stale = hint.stale ? ' Вопрос задан к прежней сборке сопоставления.' : '';
  return `${PAIR_DECISION_LABELS[hint.decision]}.${stale}`;
}

/** The newest hint per cell wins (the list answers newest first); stale ones are shown dimmed, never hidden. */
export function newestHint(hints: readonly ComparisonAiPairHint[]): ComparisonAiPairHint | undefined {
  return hints.find((hint) => !hint.stale) ?? hints[0];
}
