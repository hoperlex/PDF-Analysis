/**
 * The list «Отличия: N» (`CMP-VIEWER-01`): which differences it shows, and the walk through them with ← and →.
 *
 * The original hides the shifts by default and keeps them behind a toggle «сдвиги (не изменение): N — показать в
 * списке» (`version-comparison-viewer.js:142-144`), and does the same for the look of lines «оформление линий: N —
 * показать в списке» (`:139-141`): a shifted element is the same element, and a thicker line is not a change of the
 * drawing. They are counted and offered, never dropped without saying.
 */

import type { ComparisonDifference } from '@/shared/api';

import { SHIFT_CLASSES, STYLE_ONLY_CLASS } from './labels';

export interface DifferenceFilter {
  readonly showShifts: boolean;
  readonly showStyleOnly: boolean;
}

export interface DifferenceCounts {
  /** The differences the list shows with this filter. */
  readonly shown: number;
  /** Shifts, which are not changes (hidden unless asked for). */
  readonly shifts: number;
  /** Differences in the look of a line only (hidden unless asked for). */
  readonly styleOnly: number;
}

export function isShift(difference: ComparisonDifference): boolean {
  return SHIFT_CLASSES.includes(difference.region_class);
}

export function isStyleOnly(difference: ComparisonDifference): boolean {
  return difference.region_class === STYLE_ONLY_CLASS;
}

export function isShown(difference: ComparisonDifference, filter: DifferenceFilter): boolean {
  if (isShift(difference)) return filter.showShifts;
  if (isStyleOnly(difference)) return filter.showStyleOnly;
  return true;
}

/** The indices (into the result's own list) of the differences shown, in the engine's order. */
export function shownIndices(differences: readonly ComparisonDifference[], filter: DifferenceFilter): number[] {
  const indices: number[] = [];
  differences.forEach((difference, index) => {
    if (isShown(difference, filter)) indices.push(index);
  });
  return indices;
}

export function countDifferences(
  differences: readonly ComparisonDifference[],
  filter: DifferenceFilter,
): DifferenceCounts {
  return {
    shown: shownIndices(differences, filter).length,
    shifts: differences.filter(isShift).length,
    styleOnly: differences.filter(isStyleOnly).length,
  };
}

/**
 * The difference that ← (`-1`) or → (`+1`) reaches from `current` among the shown ones, wrapping round; `null` when
 * none is shown. No current difference: → reaches the first and ← the last.
 */
export function stepDifference(
  differences: readonly ComparisonDifference[],
  filter: DifferenceFilter,
  current: number | null,
  direction: -1 | 1,
): number | null {
  const indices = shownIndices(differences, filter);
  if (indices.length === 0) return null;
  const at = current === null ? -1 : indices.indexOf(current);
  if (at === -1) return direction === 1 ? (indices[0] as number) : (indices[indices.length - 1] as number);
  return indices[(at + direction + indices.length) % indices.length] as number;
}
