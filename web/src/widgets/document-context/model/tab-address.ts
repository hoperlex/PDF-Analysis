/**
 * Where another version, or the neighbouring document, opens **on the same tab** (`UIP-G-09`): the original's strip keeps
 * its tab when the version or the card changes, and so does the frame.
 *
 * Pure, so the claim is a function a test calls. A tab that belongs to a version opens that tab of the other version;
 * a tab that needs a run («Разбор», «Лог», the run itself) opens the other version's run, and when it has none it opens
 * the version's «Инфо» and not a link to nowhere. The two tabs that belong to the document and not to a version (the
 * document's own page and its «Оптимизация») keep their place when the other thing is a neighbouring document, and open the
 * chosen version's «Инфо» when the other thing is a version: they have no version of their own to keep.
 */

import type { DocumentAudit, RunStatus } from '@/shared/api';
import { routes } from '@/shared/lib';

import { latestResultRun, runLogAddress } from './version-tabs';
import type { TabLevel } from './version-tabs';

/** What an address needs to know of the place it leads to. */
export interface TabTarget {
  readonly projectUid: string;
  readonly documentUid: string;
  readonly versionUid: string;
  /** The version's latest run that published a result, or `null`. */
  readonly resultRunId: string | null;
  /** The version's latest run of any state, or `null`. */
  readonly latestRunId: string | null;
}

/** The address of `level` at `target`. */
export function levelAddress(level: TabLevel, target: TabTarget): string {
  const info = routes.version(target.projectUid, target.versionUid);
  switch (level) {
    case 'version':
      return info;
    case 'blocks':
      return routes.versionBlocks(target.projectUid, target.versionUid);
    case 'review':
      return target.resultRunId === null ? info : routes.review(target.projectUid, target.resultRunId);
    case 'log':
      return target.latestRunId === null ? info : runLogAddress(target.projectUid, target.latestRunId);
    case 'run':
      return target.latestRunId === null ? info : routes.run(target.projectUid, target.latestRunId);
    case 'optimisation':
      return routes.documentOptimisation(target.projectUid, target.documentUid);
    case 'document':
      return routes.document(target.projectUid, target.documentUid);
  }
}

/** The target of a version whose runs have been read (newest first). */
export function targetOfRuns(
  base: Pick<TabTarget, 'projectUid' | 'documentUid' | 'versionUid'>,
  runs: readonly RunStatus[] | undefined,
): TabTarget {
  return {
    ...base,
    resultRunId: latestResultRun(runs)?.run_id ?? null,
    latestRunId: runs?.[0]?.run_id ?? null,
  };
}

/**
 * The target of a version known by its audit, as the section listing carries it (`UIP-S04-01`): the result run is the
 * audit's, and the latest run is the one in flight, or else the result run. A later run that failed is not in the
 * audit, so «Лог» of a neighbour may open the run before it; it never opens a run of another version.
 */
export function targetOfAudit(
  base: Pick<TabTarget, 'projectUid' | 'documentUid' | 'versionUid'>,
  audit: DocumentAudit | undefined,
): TabTarget {
  return {
    ...base,
    resultRunId: audit?.result_run_id ?? null,
    latestRunId: audit?.active_run?.run_id ?? audit?.result_run_id ?? null,
  };
}

/**
 * Choosing another version of the same document: the tab stays, except the document's own, which have no version to
 * stay on and open the chosen version's «Инфо».
 */
export function versionChoiceLevel(level: TabLevel): TabLevel {
  return level === 'document' || level === 'optimisation' ? 'version' : level;
}

/** Whether the address of `level` needs the runs of the version it leads to. */
export function levelNeedsRuns(level: TabLevel): boolean {
  return level === 'review' || level === 'log' || level === 'run';
}
