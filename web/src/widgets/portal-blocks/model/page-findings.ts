/**
 * What a run's findings can honestly say about a block or a page of blocks.
 *
 * **Two scopes, and the tile says which.** A finding's evidence is a quotation with a PDF page number and offsets into the
 * text layer; `Evidence.block_id` is a secondary anchor into the text-line index, not the portal's block list. Since
 * contract 1.41.0 the server derives, on read, which portal blocks hold a finding's evidence (`listRunFindingBlocks`;
 * the rule and its misses are `analysis/geometry/finding_blocks.py`'s), and then the number on a tile is the number of the
 * run's findings that sit in THAT block (`findingsByBlock`; scope `block`). Where that relation is not known -- the run has
 * no text-layer geometry, the version no portal geometry, or the read failed -- the number is what it was before: the
 * run's findings that cite the tile's PAGE (`findingsByPage`; no scope member), and every sentence around it says
 * «на странице». A block on a page where the server could not place evidence has no number in the block scope: its
 * findings are unknown, and a zero there would read as «checked, nothing found».
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
 * DECIDED severity of the findings picks the tone; one whose findings are all undecided gets the neutral one.
 */

import type { Finding, PortalBlock, RunId, RunStatus, Severity } from '@/shared/api';
import { SEVERITY_VALUES } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { runHasPublishedResult } from '@/entities/audit-run';
import type { FindingBlockIndex } from '@/entities/block';
import { admitFindings } from '@/entities/finding';
import { declaredPages } from '@/entities/finding-observation';

export interface PageFindings {
  /**
   * `block` when the findings are those whose evidence sits in the block (`UI-PARITY-C6`); absent when they are the
   * findings that cite the block's page.
   */
  readonly scope?: 'block' | undefined;
  /** Findings of the run that cite this page (or sit in this block) at least once; a finding doing so twice counts once. */
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

/**
 * The run's admitted findings, by the portal blocks that hold their evidence (`UI-PARITY-C6`). A finding in two blocks is
 * in both; a finding the index names no block for is in none. Only blocks that hold a finding have an entry.
 */
export function findingsByBlock(findings: readonly Finding[], index: FindingBlockIndex): ReadonlyMap<string, PageFindings> {
  const grouped = new Map<string, Finding[]>();
  for (const finding of admitFindings(findings).findings) {
    for (const blockId of index.byFinding.get(finding.finding_uid) ?? []) {
      const held = grouped.get(blockId);
      if (held === undefined) grouped.set(blockId, [finding]);
      else held.push(finding);
    }
  }
  const byBlock = new Map<string, PageFindings>();
  for (const [blockId, held] of grouped) {
    byBlock.set(blockId, { scope: 'block', count: held.length, worst: worstDecided(held), findings: held });
  }
  return byBlock;
}

/** `SEVERITY_VALUES` runs from the worst to the mildest, so the first decided one is the worst. */
export function worstDecided(findings: readonly Finding[]): Severity | null {
  for (const severity of SEVERITY_VALUES) {
    if (findings.some((finding) => finding.decided_severity === severity)) return severity;
  }
  return null;
}

/** What the block scope adds to a reading: the findings by block, and the pages whose blocks have no number. */
export interface BlockFindings {
  readonly byBlock: ReadonlyMap<string, PageFindings>;
  readonly unlinkedPages: ReadonlySet<number>;
}

/**
 * What the tiles may show about findings.
 *
 *   `none`         no run is named, or its answer has not arrived: no number and no sentence;
 *   `no-result`    the run published no findings (failed, cancelled, still going): a sentence;
 *   `unreadable`   the run or its findings could not be read: a sentence;
 *   `read`         the run's findings, by page, and the instant the run started (`created_at`) when
 *                  the run's status carried it; `blocks` is present only when the server's block links for the run
 *                  were produced, and then the tiles speak of blocks, not pages.
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
      readonly blocks?: BlockFindings | undefined;
    };

export const NO_PAGE_FINDINGS: PageFindingsReading = { kind: 'none' };

/** The reading for one page: what the tile and the block view say, or `null` when no number may be shown. */
export function pageReading(reading: PageFindingsReading, page: number): PageFindings | null {
  if (reading.kind !== 'read') return null;
  return reading.byPage.get(page) ?? { count: 0, worst: null, findings: [] };
}

/**
 * The reading for one block: what its tile and the block view say, or `null` when no number may be shown.
 *
 * With the server's block links, the findings that sit in the block (zero is a fact there: `scope: 'block'`), and `null`
 * for a block on a page where the server could not place evidence. Without them, the block's page as `pageReading` says.
 */
export function blockReading(reading: PageFindingsReading, block: PortalBlock): PageFindings | null {
  if (reading.kind !== 'read') return null;
  if (reading.blocks === undefined) return pageReading(reading, block.page_number);
  if (reading.blocks.unlinkedPages.has(block.page_number)) return null;
  return reading.blocks.byBlock.get(block.portal_block_id) ?? { scope: 'block', count: 0, worst: null, findings: [] };
}

/**
 * The version's latest run that published a result, or `null` when none of `runs` did.
 *
 * `listRuns` answers newest first and this keeps its order: the first run that
 * `runHasPublishedResult` accepts is the latest, so nothing is sorted here (a sort would hide a
 * server that broke its order).
 */
export function latestPublishedRunId(runs: readonly RunStatus[]): RunId | null {
  const published = runs.find((run) => runHasPublishedResult(run.state));
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
