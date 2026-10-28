/**
 * Reading the effective matrix for the screen: the cell of a row in a version, the page that stands for a
 * row when an edit names it, the pair of a row in the chosen transition, the rows «только изменения»
 * leaves (`version-comparison.js:347-430`).
 *
 * A page is a version and a coordinate in it (`ComparisonPageRef`); a row is valid within one revision
 * (CMP-MATRIX-01 section 5): nothing here keeps a row id across a reload.
 */

import type {
  ComparisonMatrixCell,
  ComparisonMatrixColumn,
  ComparisonMatrixRow,
  ComparisonPageRef,
  ComparisonSheetPair,
  ComparisonSheetStatus,
} from '@/shared/api';

export function pageKey(page: Pick<ComparisonPageRef, 'version_uid' | 'page_number'>): string {
  return `${page.version_uid}#${page.page_number}`;
}

export function samePage(
  a: Pick<ComparisonPageRef, 'version_uid' | 'page_number'> | undefined,
  b: Pick<ComparisonPageRef, 'version_uid' | 'page_number'> | undefined,
): boolean {
  return a !== undefined && b !== undefined && pageKey(a) === pageKey(b);
}

export function cellOf(row: ComparisonMatrixRow, versionUid: string): ComparisonMatrixCell | undefined {
  return row.cells.find((cell) => cell.version_uid === versionUid);
}

export function matchedCells(row: ComparisonMatrixRow): ComparisonMatrixCell[] {
  return row.cells.filter((cell) => cell.state === 'matched' && cell.page !== undefined);
}

/**
 * The page an edit names for a row: the first matched sheet of the row that is not in `exceptVersionUid`
 * (a link joins two different versions, so the reference must not be in the version of the page that joins).
 */
export function referencePage(row: ComparisonMatrixRow, exceptVersionUid?: string): ComparisonPageRef | null {
  for (const cell of matchedCells(row)) {
    if (cell.page !== undefined && cell.version_uid !== exceptVersionUid) return cell.page;
  }
  return null;
}

/** A row that holds one matched sheet only: there is nothing to unlink it from. */
export function isSoleSheet(row: ComparisonMatrixRow): boolean {
  return matchedCells(row).length <= 1;
}

/** What the row head says: the title, then the sheet number (`display_title`). */
export function rowHeading(row: ComparisonMatrixRow): { readonly title: string; readonly number: string } {
  return { title: row.title ?? '', number: row.sheet_number ?? '' };
}

/** The sides A and B of the chosen pair: the last two versions unless the reader chose (`loadCatalog`, `:731-758`). */
export interface Sides {
  readonly a: string | null;
  readonly b: string | null;
}

export function defaultSides(columns: readonly ComparisonMatrixColumn[]): Sides {
  const last = columns.at(-1);
  const previous = columns.at(-2);
  return { a: previous?.version_uid ?? null, b: last?.version_uid ?? null };
}

/** Whether a pair is valid: two different versions of the matrix (`Выберите две разные версии.`). */
export function validSides(sides: Sides, columns: readonly ComparisonMatrixColumn[]): boolean {
  if (sides.a === null || sides.b === null || sides.a === sides.b) return false;
  const known = new Set(columns.map((column) => column.version_uid));
  return known.has(sides.a) && known.has(sides.b);
}

/** Whether the sides are neighbours in the matrix's order (only neighbours are compared). */
export function adjacentSides(sides: Sides, columns: readonly ComparisonMatrixColumn[]): boolean {
  if (sides.a === null || sides.b === null) return false;
  const left = columns.findIndex((column) => column.version_uid === sides.a);
  const right = columns.findIndex((column) => column.version_uid === sides.b);
  return left >= 0 && right === left + 1;
}

/** The sheet pair of a row in the compared transition, or `null` when the row has none there. */
export function pairOfRow(
  row: ComparisonMatrixRow,
  sides: Sides,
  pairs: readonly ComparisonSheetPair[],
): ComparisonSheetPair | null {
  if (sides.a === null || sides.b === null) return null;
  const left = cellOf(row, sides.a)?.page;
  const right = cellOf(row, sides.b)?.page;
  if (left === undefined && right === undefined) return null;
  return (
    pairs.find(
      (pair) =>
        (left === undefined ? pair.page_a === undefined : samePage(pair.page_a?.page, left)) &&
        (right === undefined ? pair.page_b === undefined : samePage(pair.page_b?.page, right)),
    ) ?? null
  );
}

const UNCHANGED: readonly ComparisonSheetStatus[] = ['same', 'same_zones_changed'];

/** «только изменения»: the rows whose pair is neither the same nor the same but for service zones (`:349`). */
export function changedRows(
  rows: readonly ComparisonMatrixRow[],
  sides: Sides,
  pairs: readonly ComparisonSheetPair[],
): ComparisonMatrixRow[] {
  return rows.filter((row) => {
    const status = pairOfRow(row, sides, pairs)?.status;
    return status !== undefined && !UNCHANGED.includes(status);
  });
}

/** The pairs of a transition that can be opened, in the order of the rows: the neighbours the viewer steps over. */
export function openablePairs(pairs: readonly ComparisonSheetPair[]): ComparisonSheetPair[] {
  return pairs.filter((pair) => pair.state === 'done' && pair.status !== undefined);
}

/** A split cell reads «⇉» when the same row's next version holds a split sheet too, else «◫» (the parts). */
export function splitDirection(row: ComparisonMatrixRow, versionUid: string): 'whole' | 'part' {
  const index = row.cells.findIndex((cell) => cell.version_uid === versionUid);
  const next = index >= 0 ? row.cells[index + 1] : undefined;
  return next !== undefined && next.state === 'matched' && next.flags?.includes('split') === true ? 'whole' : 'part';
}

/**
 * The name of a column: «№1», «№2» … by its place in the comparison order (the order, not the document's ordinal). A letter
 * would not do: the interface is Russian (`R-18`), and the original's «V1» is a Latin letter and a digit.
 */
export function columnName(position: number): string {
  return `№${position + 1}`;
}

/** The names of the columns by version, for the sentences that name a version. */
export function columnNames(columns: readonly ComparisonMatrixColumn[]): Map<string, string> {
  return new Map(columns.map((column, position) => [column.version_uid, column.label ?? columnName(position)]));
}
