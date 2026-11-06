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
 * **The run is the version's latest that published a result** (`scopeRunId`): the geometry run
 * is a run that read the bundle, and a later run of the same version is the one whose findings the
 * reader has before them in «Разбор». Only when no run in the version's first page of runs
 * published anything does the count fall back to the run whose geometry stage read this bundle
 * (`produced_by_run_id`), and then the sentence says what that run did. Whichever run it is, the
 * tile and the sentence say which one and when it started («по прогону от <time>»). If the run
 * published no findings, or they cannot be read, the tiles carry no number at all and a sentence says
 * why, rather than a zero that reads as «checked, nothing found».
 *
 * **The tone is the expert's.** A finding's canonical severity is `decided_severity` (`R-151j`);
 * the model's proposal is not an expert decision and does not colour anything here. The worst
 * DECIDED severity of the page's findings picks the tone; a page whose findings are all
 * undecided gets the neutral one.
 */

import type { Finding, RunId, RunStatus, Severity } from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { runHasPublishedResult } from '@/entities/audit-run';
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
 *   `read`         the run's findings, by page, and the instant the run started (`created_at`) when
 *                  the run's status carried it.
 */
export type PageFindingsReading =
  | { readonly kind: 'none' }
  | { readonly kind: 'no-result'; readonly runId: RunId }
  | { readonly kind: 'unreadable'; readonly runId: RunId }
  | {
      readonly kind: 'read';
      readonly runId: RunId;
      readonly byPage: ReadonlyMap<number, PageFindings>;
      readonly runAt?: string | undefined;
    };

export const NO_PAGE_FINDINGS: PageFindingsReading = { kind: 'none' };

/** The reading for one page: what the tile and the block view say, or `null` when no number may be shown. */
export function pageReading(reading: PageFindingsReading, page: number): PageFindings | null {
  if (reading.kind !== 'read') return null;
  return reading.byPage.get(page) ?? { count: 0, worst: null, findings: [] };
}

/**
 * The version's latest run that published a result, or `null` when none of `runs` did.
 *
 * `listRuns` answers newest first and this keeps its order: the first run that
 * `runHasPublishedResult` accepts is the latest, so nothing is sorted here (a sort would hide a
 * server that broke its order). A run of the v3 beta profile publishes no canonical findings and is
 * not taken for one.
 */
export function latestPublishedRunId(runs: readonly RunStatus[]): RunId | null {
  const published = runs.find((run) => runHasPublishedResult(run.state, run.analysis_profile_id));
  return published === undefined ? null : published.run_id;
}

/**
 * The run whose findings number the tiles.
 *
 *   a list still on its way   `null`: no run is guessed, so the wrong run's findings are not fetched
 *                              to be replaced a moment later;
 *   a list that was read      its latest published run, else the run whose geometry stage read the bundle;
 *   a list that failed        the geometry run: the tiles still say which run the numbers are from.
 */
export function scopeRunId(
  runs: readonly RunStatus[] | 'pending' | 'unreadable',
  geometryRunId: RunId | null,
): RunId | null {
  if (runs === 'pending') return null;
  if (runs === 'unreadable') return geometryRunId;
  return latestPublishedRunId(runs) ?? geometryRunId;
}

/**
 * «по прогону от <time>»: the words a tile's title and the block view use to say which run a count is
 * from, or `null` when the run's start is not known. The instant is the shared UTC stamp.
 */
export function runSourcePhrase(runAt: string | undefined): string | null {
  return runAt === undefined ? null : `по прогону от ${formatInstant(runAt)}`;
}
