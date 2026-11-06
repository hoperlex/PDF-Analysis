/**
 * What a run's findings can honestly say about a page of blocks.
 *
 * **A finding points at pages, not at blocks.** Its evidence is a quotation with a PDF page number
 * and offsets into the text layer (`Evidence`); `Evidence.block_id` is a secondary anchor into the
 * text-line index, which is not the portal's block list, and the API names no portal block for
 * a finding. The original counted findings on a block; this product cannot, and a count on a tile
 * that pretended to be the block's would be a number nobody can check. So the number on a tile is
 * the number of the run's findings that cite the tile's PAGE, and every sentence around it says
 * «на странице».
 *
 * **The run is the one the block list names.** `produced_by_run_id` is the run whose geometry
 * stage read this bundle. If that run published no findings, or they cannot be read, the tiles
 * carry no number at all and a sentence says why, rather than a zero that reads as «checked,
 * nothing found».
 *
 * **The tone is the expert's.** A finding's canonical severity is `decided_severity` (`R-151j`);
 * the model's proposal is not an expert decision and does not colour anything here. The worst
 * DECIDED severity of the page's findings picks the tone; a page whose findings are all
 * undecided gets the neutral one.
 */

import type { Finding, RunId, Severity } from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';
import { admitFindings } from '@/entities/finding';
import { declaredPages } from '@/entities/finding-observation';

export interface PageFindings {
  /** Findings of the run that cite this page at least once; a finding citing it twice counts once. */
  readonly count: number;
  /** The worst severity an expert decided among them, or `null` when none is decided. */
  readonly worst: Severity | null;
  readonly findings: readonly Finding[];
}

/**
 * The findings list inside the cached value of `queryKeys.runs.findings(runId)`, or `null` when the
 * value is not the shape that key holds (`CompleteRunFindings`: `{ data: { items } }`).
 *
 * The key is filled by one `queryFn` and always holds that envelope, so `null` is not a case the
 * product produces; it is here so that a value of another shape (a hand-seeded cache, a future
 * reseal) ends as the sentence «не удалось прочитать» and not as a screen that throws. Never an empty
 * list: an empty list would read as «checked, nothing found».
 */
export function completeFindingsOf(cached: unknown): readonly Finding[] | null {
  if (typeof cached !== 'object' || cached === null || !('data' in cached)) return null;
  const page = cached.data;
  if (typeof page !== 'object' || page === null || !('items' in page) || !Array.isArray(page.items)) return null;
  return page.items as readonly Finding[];
}

/** The run's admitted findings, by the PDF pages they cite. A finding on two pages is on both. */
export function findingsByPage(findings: readonly Finding[]): ReadonlyMap<number, PageFindings> {
  const grouped = new Map<number, Finding[]>();
  for (const finding of admitFindings(findings).findings) {
    for (const page of declaredPages(finding.observation)) {
      const onPage = grouped.get(page);
      if (onPage === undefined) grouped.set(page, [finding]);
      else onPage.push(finding);
    }
  }
  const byPage = new Map<number, PageFindings>();
  for (const [page, onPage] of grouped) {
    byPage.set(page, { count: onPage.length, worst: worstDecided(onPage), findings: onPage });
  }
  return byPage;
}

/** `SEVERITY_VALUES` runs from the worst to the mildest, so the first decided one is the worst. */
export function worstDecided(findings: readonly Finding[]): Severity | null {
  for (const severity of SEVERITY_VALUES) {
    if (findings.some((finding) => finding.decided_severity === severity)) return severity;
  }
  return null;
}

/**
 * What the tiles may show about findings.
 *
 *   `none`         no run is named, or its answer has not arrived: no number and no sentence;
 *   `no-result`    the run published no findings (failed, cancelled, still going): a sentence;
 *   `unreadable`   the run or its findings could not be read: a sentence;
 *   `read`         the run's findings, by page.
 */
export type PageFindingsReading =
  | { readonly kind: 'none' }
  | { readonly kind: 'no-result'; readonly runId: RunId }
  | { readonly kind: 'unreadable'; readonly runId: RunId }
  | { readonly kind: 'read'; readonly runId: RunId; readonly byPage: ReadonlyMap<number, PageFindings> };

export const NO_PAGE_FINDINGS: PageFindingsReading = { kind: 'none' };

/** The reading for one page: what the tile and the block view say, or `null` when no number may be shown. */
export function pageReading(reading: PageFindingsReading, page: number): PageFindings | null {
  if (reading.kind !== 'read') return null;
  return reading.byPage.get(page) ?? { count: 0, worst: null, findings: [] };
}
