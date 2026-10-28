/**
 * The order of the versions of a document set, as the dialog «Порядок версий» edits it
 * (`frontend/static/js/version-comparison.js:503-523`, `:1557-1572`).
 *
 * The order is the reader's word: a number in a file name, «Изм.» on the stamp and the issue date are hints only. The
 * dialog moves one version a step at a time; the new revision is appended with the revision the reader saw
 * (`appendComparisonVersionOrder`, `409 comparison_version_order_stale` on a moved base). The order never changes the
 * ordinal of the documents' versions (ADR-0025 decision 16, `D-5`).
 */

import type { ComparisonVersionOrder } from '@/shared/api';

/** Move the version at `index` one place up (`-1`) or down (`+1`); a move off either end changes nothing. */
export function moveVersion(order: readonly string[], index: number, direction: -1 | 1): string[] {
  const target = index + direction;
  if (index < 0 || index >= order.length || target < 0 || target >= order.length) return [...order];
  const next = [...order];
  const moved = next[index] as string;
  next[index] = next[target] as string;
  next[target] = moved;
  return next;
}

export function sameOrder(a: readonly string[], b: readonly string[]): boolean {
  return a.length === b.length && a.every((uid, position) => uid === b[position]);
}

/** The revision number to put in `base_revision_no`: the latest the reader saw, or `0` for none. */
export function baseRevisionOf(latest: ComparisonVersionOrder | null | undefined): number {
  return latest?.revision_no ?? 0;
}

export const ORDER_DIALOG_TEXT =
  'Порядок задаёте вы. Номер в имени файла, «Изм.» по штампам и дата выпуска — только подсказки.';
export const ORDER_SAVE_HINT =
  'Сохранить порядок. Сопоставление листов пересоберётся, а сохранённая сводка переходов станет «для прежнего порядка версий».';
