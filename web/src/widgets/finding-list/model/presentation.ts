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
export type VerdictFilter = 'active' | 'all' | 'waiting' | 'accepted' | 'rejected';

const WAITING: ReadonlySet<Verdict> = new Set<Verdict>(['pending', 'needs_manual_review']);

export function verdictBucket(verdict: Verdict): Exclude<VerdictFilter, 'all' | 'active'> {
  if (WAITING.has(verdict)) return 'waiting';
  return verdict === 'accepted' ? 'accepted' : 'rejected';
}

const BUCKET_RANK: Readonly<Record<Exclude<VerdictFilter, 'all' | 'active'>, number>> = { waiting: 0, accepted: 1, rejected: 2 };

/**
 * `UI-A-71`: the original's order, pending → accepted → rejected, with the run's own order kept inside each of the three
 * (a stable sort; `Array.prototype.sort` is stable since ES2019). The original sorts its flat table this way once the
 * run holds any decision, which is the same thing as always sorting: a run without a decision is all pending.
 */
export function inVerdictOrder(findings: readonly Finding[]): readonly Finding[] {
  return [...findings].sort((a, b) => BUCKET_RANK[verdictBucket(a.current_verdict)] - BUCKET_RANK[verdictBucket(b.current_verdict)]);
}

/** The list keeps its category headings and puts the verdicts in order inside each. */
export function groupsInVerdictOrder(groups: readonly FindingGroup<Finding>[]): readonly FindingGroup<Finding>[] {
  return groups.map((group) => ({ ...group, findings: inVerdictOrder(group.findings) }));
}

/**
 * The findings in the order the screen shows them: by category in the list, as the original's flat table in the table.
 * What walks the findings one by one («Во весь экран», ‹ ›) takes this order, so it never steps in a way the eye cannot follow.
 */
export function findingsAsShown(groups: readonly FindingGroup<Finding>[], view: 'list' | 'table'): readonly Finding[] {
  return view === 'table'
    ? inVerdictOrder(groups.flatMap((group) => group.findings))
    : groupsInVerdictOrder(groups).flatMap((group) => group.findings);
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
  if (pages.length === 0) return { sheet: null, pages: 'Страница не подтверждена' };
  const sheets = sheetOf === undefined ? [] : pages.map((page) => sheetOf(page));
  const known = pages.length > 0 && sheets.length === pages.length && sheets.every((sheet) => sheet !== undefined);
  const pageText = `стр. ${pages.join(', ')}`;
  if (!known) return { sheet: null, pages: pageText };
  return { sheet: `${pages.length === 1 ? 'Лист' : 'Листы'} ${sheets.join(', ')}`, pages: pageText };
}

/**
 * The number each finding of the run carries on screen, counted over the whole run in the order the run lists them (by
 * category), before any verdict order. It stays the same when a filter hides its neighbours and when a decision moves the
 * row, so «№ 7» is still «№ 7» under «Ожидают решения» and after it is accepted; like the original's ID, the numbers read
 * out of sequence down a table once the verdicts have set the order. It is a label for reading aloud; the finding's identity
 * is its `finding_uid`.
 */
export function findingNumbers(groups: readonly FindingGroup<Finding>[]): ReadonlyMap<string, number> {
  const numbers = new Map<string, number>();
  for (const group of groups) {
    for (const finding of group.findings) numbers.set(finding.finding_uid, numbers.size + 1);
  }
  return numbers;
}
