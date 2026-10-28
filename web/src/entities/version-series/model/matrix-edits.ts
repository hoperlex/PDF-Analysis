/**
 * What a reader's hand does to the draft: «Связать» on a candidate, a thumbnail dropped on a cell, «⤫
 * Отвязать в отдельную строку», «Отметить, что этого листа в версии нет» (`version-comparison.js:1220-1330`,
 * CMP-MATRIX-01 section 10).
 *
 * Each gesture becomes one edit the server understands (`link`, `unlink`, `mark_absent`) or a refusal in
 * words, before anything is sent: a link joins two different versions, so the reference sheet of the row must
 * be in another version than the sheet that joins it; a lone sheet has nothing to be unlinked from. These are
 * the contract's own preconditions (`comparison_edit_invalid`), checked early so a reader is told at the cell
 * and not after the batch; the server still checks them all.
 */

import type { ComparisonMatrixCandidate, ComparisonMatrixRow, ComparisonPageRef } from '@/shared/api';

import type { DraftEdit } from './draft';
import { cellOf, isSoleSheet, referencePage, samePage } from './matrix-view';

export type GestureResult = { readonly edit: DraftEdit } | { readonly refusal: string };

export const NO_REFERENCE_SHEET = 'В этой строке нет листа другой версии, с которым можно связать.';
export const WRONG_COLUMN = 'Лист можно перенести только в столбец его версии.';
export const ALREADY_THERE = 'Этот лист уже стоит в этой строке.';
export const SOLE_SHEET = 'В строке один лист: отвязывать его не от чего.';

/** The media type a dragged thumbnail carries; its text is the page's coordinate. */
export const DRAG_TYPE = 'application/x-am-sheet';

export function dragPayload(page: ComparisonPageRef): string {
  return JSON.stringify({
    version_uid: page.version_uid,
    page_number: page.page_number,
    ...(page.page_profile_id === undefined ? {} : { page_profile_id: page.page_profile_id }),
  });
}

/** A dragged page, read back; anything that is not a page coordinate is `null`, never a guess. */
export function parseDragged(text: string): ComparisonPageRef | null {
  try {
    const value: unknown = JSON.parse(text);
    if (typeof value !== 'object' || value === null) return null;
    const record = value as Record<string, unknown>;
    const version = record['version_uid'];
    const number = record['page_number'];
    const profile = record['page_profile_id'];
    if (typeof version !== 'string' || typeof number !== 'number' || !Number.isInteger(number) || number < 1) return null;
    return {
      version_uid: version,
      page_number: number,
      ...(typeof profile === 'string' ? { page_profile_id: profile } : {}),
    };
  } catch {
    return null;
  }
}

/** «Связать»: the candidate of an unmatched cell joins the row. */
export function linkCandidate(
  row: ComparisonMatrixRow,
  versionUid: string,
  candidate: ComparisonMatrixCandidate,
): GestureResult {
  const reference = referencePage(row, candidate.page.version_uid);
  if (reference === null || candidate.page.version_uid !== versionUid) return { refusal: NO_REFERENCE_SHEET };
  return { edit: { kind: 'link', page: reference, otherPage: candidate.page } };
}

/** A thumbnail dropped on the cell of `versionUid` in `row`. */
export function dropOnCell(row: ComparisonMatrixRow, versionUid: string, dragged: ComparisonPageRef): GestureResult {
  if (dragged.version_uid !== versionUid) return { refusal: WRONG_COLUMN };
  if (samePage(cellOf(row, versionUid)?.page, dragged)) return { refusal: ALREADY_THERE };
  const reference = referencePage(row, versionUid);
  if (reference === null) return { refusal: NO_REFERENCE_SHEET };
  return { edit: { kind: 'link', page: reference, otherPage: dragged } };
}

/** «⤫ Отвязать в отдельную строку». */
export function unlinkSheet(row: ComparisonMatrixRow, page: ComparisonPageRef): GestureResult {
  if (isSoleSheet(row)) return { refusal: SOLE_SHEET };
  return { edit: { kind: 'unlink', page } };
}

/** «Отметить, что этого листа в версии нет». */
export function markAbsent(row: ComparisonMatrixRow, versionUid: string): GestureResult {
  const reference = referencePage(row, versionUid);
  if (reference === null) return { refusal: NO_REFERENCE_SHEET };
  return { edit: { kind: 'mark_absent', page: reference, absentVersionUid: versionUid } };
}
