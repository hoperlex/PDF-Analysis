/**
 * The pause of the vectors as the top strip words it (`ADR-0029` decision 8).
 *
 * The contract's `VectorControl` also carries the night window's state; the strip does not show it (one pause, one badge), so
 * this reduces the read to what the strip draws: paused or not, since when, or that the read failed.
 */

import type { VectorControl } from '@/shared/api';

/** The badge's text; it exists only while the vectors are paused. */
export const VECTORS_PAUSED_LABEL = 'Векторы на паузе';

const CONSEQUENCE = 'прецеденты новых находок появятся после возобновления';

/** The badge's tooltip: since when (already worded, e.g. «с 10:00»; empty when the time is unknown) and what it means for the reader. */
export function vectorsPausedHint(since: string): string {
  return `${VECTORS_PAUSED_LABEL}${since === '' ? '' : ` ${since}`}; ${CONSEQUENCE}`;
}

/** What the strip knows of the vectors: the read answer, or that the read failed. Absent while the first read is in flight. */
export type VectorsPause =
  | { readonly kind: 'read'; readonly paused: boolean; readonly since: string | undefined }
  | { readonly kind: 'unread' };

/**
 * The strip's view of one read. A failed read with an earlier answer in hand keeps the answer (it is the last thing known);
 * a failed read with none says `unread`, never `not paused`.
 */
export function vectorsPauseOf(control: VectorControl | undefined, failed: boolean): VectorsPause | undefined {
  if (control !== undefined) return { kind: 'read', paused: control.paused, since: control.paused_since };
  return failed ? { kind: 'unread' } : undefined;
}
