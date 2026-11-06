/**
 * What the finding list says about a finding, as plain functions: its pages, its verdict's bucket, its place in the run.
 * No React and no query, so the list, the table and their tests read the same words.
 */

import type { Finding, Verdict } from '@/shared/api';
import type { FindingGroup } from '@/entities/finding';

/**
 * `UI-A-70`, `UI-A-71`: the verdicts of the run at a glance and a filter by them, as the original's
 * «Экспертная оценка» counter and its pending → accepted → rejected order. The page loads every finding of
 * the run (`R-150i`), so the counts and the filter are over the whole run, never over one page.
 * `needs_manual_review` waits for the expert like `pending` (`UI-PARITY-METRICS`).
 */
export type VerdictFilter = 'all' | 'waiting' | 'accepted' | 'rejected';

const WAITING: ReadonlySet<Verdict> = new Set<Verdict>(['pending', 'needs_manual_review']);

export function verdictBucket(verdict: Verdict): Exclude<VerdictFilter, 'all'> {
  if (WAITING.has(verdict)) return 'waiting';
  return verdict === 'accepted' ? 'accepted' : 'rejected';
}

/**
 * `UI-PARITY-P0O`: a finding's pages as the original states them, with the sheet first («Лист 3 · стр. 5») when the
 * portal geometry names a sheet for every page; otherwise the PDF pages alone, never a page number passed off as a sheet.
 */
export function pagesLabel(pages: readonly number[], sheetOf?: (page: number) => number | undefined): string {
  const { sheet, pages: pageText } = pagesParts(pages, sheetOf);
  return sheet === null ? pageText : `${sheet} · ${pageText}`;
}

/** The same two statements apart, for a table cell that sets the sheet over the PDF page as the original's «Лист» column does. */
export function pagesParts(
  pages: readonly number[],
  sheetOf?: (page: number) => number | undefined,
): { readonly sheet: string | null; readonly pages: string } {
  const sheets = sheetOf === undefined ? [] : pages.map((page) => sheetOf(page));
  const known = pages.length > 0 && sheets.length === pages.length && sheets.every((sheet) => sheet !== undefined);
  const pageText = `стр. ${pages.join(', ')}`;
  if (!known) return { sheet: null, pages: pageText };
  return { sheet: `${pages.length === 1 ? 'Лист' : 'Листы'} ${sheets.join(', ')}`, pages: pageText };
}

/**
 * The number each finding of the run carries on screen, counted over the whole run in the order the list shows it.
 * It stays the same when a filter hides its neighbours, so «№ 7» is still «№ 7» under «Ожидают решения». It is a
 * label for reading aloud; the finding's identity is its `finding_uid`.
 */
export function findingNumbers(groups: readonly FindingGroup<Finding>[]): ReadonlyMap<string, number> {
  const numbers = new Map<string, number>();
  for (const group of groups) {
    for (const finding of group.findings) numbers.set(finding.finding_uid, numbers.size + 1);
  }
  return numbers;
}
