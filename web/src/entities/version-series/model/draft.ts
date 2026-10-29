/**
 * The draft of manual edits to the sheet matrix (`version-comparison.js:1297-1408`, plan §1.1).
 *
 * A reader's drags, «Связать», «⤫» and «Отметить, что этого листа в версии нет» are not sent one by one:
 * they collect in a draft that is applied in one batch, against the revision of the matrix it was started
 * on (`applyComparisonMatrixEdits`, CMP-SEAL-C1 decision 1). If the matrix moved meanwhile the server
 * answers `409 comparison_matrix_stale`; the draft is then **rebased** on the matrix read again: its base
 * becomes the fresh revision, and an edit whose page is no longer in the matrix is taken out of the draft
 * **and reported**, never dropped silently. The server decides what an edit means (this file never replays
 * one): the draft only holds the inputs and says them in words.
 *
 * Plain data and pure functions, so every rule has a test.
 */

import type {
  ApplyComparisonMatrixEditsRequest,
  ComparisonMatrix,
  ComparisonMatrixEditInput,
  ComparisonMatrixRevision,
  ComparisonPageRef,
} from '@/shared/api';

import { pageKey } from './matrix-view';

export type DraftEdit =
  | { readonly kind: 'link'; readonly page: ComparisonPageRef; readonly otherPage: ComparisonPageRef }
  | { readonly kind: 'unlink'; readonly page: ComparisonPageRef }
  | { readonly kind: 'mark_absent'; readonly page: ComparisonPageRef; readonly absentVersionUid: string };

export interface Draft {
  /** The revision the first edit was made against; `null` for an empty draft. */
  readonly base: ComparisonMatrixRevision | null;
  readonly edits: readonly DraftEdit[];
}

export const EMPTY_DRAFT: Draft = { base: null, edits: [] };

/** The most edits one batch may carry (`comparison_edits_limit`, `ApplyComparisonMatrixEditsRequest`). */
export const DRAFT_LIMIT = 500;

function sameEdit(a: DraftEdit, b: DraftEdit): boolean {
  if (a.kind !== b.kind || pageKey(a.page) !== pageKey(b.page)) return false;
  if (a.kind === 'link' && b.kind === 'link') return pageKey(a.otherPage) === pageKey(b.otherPage);
  if (a.kind === 'mark_absent' && b.kind === 'mark_absent') return a.absentVersionUid === b.absentVersionUid;
  return true;
}

export function revisionKey(revision: ComparisonMatrixRevision): string {
  return `${revision.matrix_id}#${revision.edit_no}`;
}

/**
 * Add an edit. The first edit fixes the base revision; an edit equal to one already in the draft changes
 * nothing; a full draft refuses (`null`), so the screen can say why instead of the server doing it later.
 */
export function addEdit(draft: Draft, revision: ComparisonMatrixRevision, edit: DraftEdit): Draft | null {
  if (draft.edits.some((held) => sameEdit(held, edit))) return draft;
  if (draft.edits.length >= DRAFT_LIMIT) return null;
  return { base: draft.base ?? revision, edits: [...draft.edits, edit] };
}

/** «Отменить правку» while a draft exists: the last edit goes (`undoEdit`, `:1394`). */
export function removeLast(draft: Draft): Draft {
  const edits = draft.edits.slice(0, -1);
  return edits.length === 0 ? EMPTY_DRAFT : { base: draft.base, edits };
}

export function removeAt(draft: Draft, index: number): Draft {
  const edits = draft.edits.filter((_, position) => position !== index);
  return edits.length === 0 ? EMPTY_DRAFT : { base: draft.base, edits };
}

function pageInput(page: ComparisonPageRef): ComparisonPageRef {
  return {
    version_uid: page.version_uid,
    page_number: page.page_number,
    ...(page.page_profile_id === undefined ? {} : { page_profile_id: page.page_profile_id }),
  };
}

export function toInput(edit: DraftEdit): ComparisonMatrixEditInput {
  switch (edit.kind) {
    case 'link':
      return { kind: 'link', page: pageInput(edit.page), other_page: pageInput(edit.otherPage) };
    case 'unlink':
      return { kind: 'unlink', page: pageInput(edit.page) };
    case 'mark_absent':
      return { kind: 'mark_absent', page: pageInput(edit.page), absent_version_uid: edit.absentVersionUid };
  }
}

/** The request of the batch, or `null` for an empty draft. */
export function requestOf(draft: Draft): ApplyComparisonMatrixEditsRequest | null {
  if (draft.base === null || draft.edits.length === 0) return null;
  return { base_revision: draft.base, edits: draft.edits.map(toInput) };
}

/** Whether the matrix moved under a draft: the draft's base is not the revision on the screen. */
export function isStale(draft: Draft, current: ComparisonMatrixRevision | undefined): boolean {
  return draft.base !== null && current !== undefined && revisionKey(draft.base) !== revisionKey(current);
}

export interface Rebased {
  readonly draft: Draft;
  /** The edits taken out because a page they name is not in the fresh matrix. */
  readonly dropped: readonly DraftEdit[];
}

function pagesOf(matrix: ComparisonMatrix): Set<string> {
  const keys = new Set<string>();
  for (const row of matrix.rows ?? []) {
    for (const cell of row.cells) {
      if (cell.page !== undefined) keys.add(pageKey(cell.page));
      // A page an unmatched cell offers is a page of the matrix too: «Связать» names it.
      for (const candidate of cell.candidates ?? []) keys.add(pageKey(candidate.page));
    }
  }
  for (const page of matrix.unassigned_pages ?? []) keys.add(pageKey(page));
  return keys;
}

function namedPages(edit: DraftEdit): ComparisonPageRef[] {
  return edit.kind === 'link' ? [edit.page, edit.otherPage] : [edit.page];
}

/**
 * The draft on a matrix that moved: the base becomes the fresh revision and an edit whose page, or whose
 * absent version, the fresh matrix does not have is returned in `dropped`. A matrix without a build has no
 * revision to rebase on: the draft is emptied and everything in it is reported.
 */
export function rebase(draft: Draft, fresh: ComparisonMatrix): Rebased {
  const revision = fresh.revision;
  if (revision === undefined) return { draft: EMPTY_DRAFT, dropped: draft.edits };
  const known = pagesOf(fresh);
  const versions = new Set((fresh.columns ?? []).map((column) => column.version_uid));
  const kept: DraftEdit[] = [];
  const dropped: DraftEdit[] = [];
  for (const edit of draft.edits) {
    const present =
      namedPages(edit).every((page) => known.has(pageKey(page))) &&
      (edit.kind !== 'mark_absent' || versions.has(edit.absentVersionUid));
    (present ? kept : dropped).push(edit);
  }
  return { draft: kept.length === 0 ? EMPTY_DRAFT : { base: revision, edits: kept }, dropped };
}

/** The pages the draft touches, so the matrix can mark their cells. */
export function touchedPages(draft: Draft): Set<string> {
  const keys = new Set<string>();
  for (const edit of draft.edits) for (const page of namedPages(edit)) keys.add(pageKey(page));
  return keys;
}

/** An edit said in words; `versionName` gives the column name of a version. */
export function describeEdit(edit: DraftEdit, versionName: (versionUid: string) => string): string {
  switch (edit.kind) {
    case 'link':
      return (
        `Связать лист ${edit.otherPage.page_number} (версия ${versionName(edit.otherPage.version_uid)}) ` +
        `с листом ${edit.page.page_number} (версия ${versionName(edit.page.version_uid)})`
      );
    case 'unlink':
      return `Отвязать лист ${edit.page.page_number} (версия ${versionName(edit.page.version_uid)}) в отдельную строку`;
    case 'mark_absent':
      return (
        `Отметить, что листа ${edit.page.page_number} (версия ${versionName(edit.page.version_uid)}) ` +
        `нет в версии ${versionName(edit.absentVersionUid)}`
      );
  }
}
