'use client';

/**
 * The run's findings, read for the tiles of «Блоки» (see `page-findings.ts` for what they may say).
 *
 * Three reads, in order: the version's first page of runs (newest first, `useRunList`), to learn which
 * run's findings the reader has before them -- the latest that published a result, else the run whose
 * geometry stage read the bundle (`scopeRunId`); then that run's status, to learn whether it published
 * findings at all and when it started; and then its complete finding list, the same read the review
 * screen fills (`runFindingsQueryOptions`), so a reader who came from «Разбор» finds both in the cache.
 * The findings are not asked for a run that has none to give, and no run is asked for while the list of
 * runs is still on its way.
 *
 * A fourth read, `listRunFindingBlocks` (`UI-PARITY-C6`), is asked for the same run once its findings are in: the portal
 * blocks that hold each finding. It numbers the tiles by block when it was produced; while it is on its way, when it is
 * not produced and when it fails, the tiles keep the page numbers and say so (a link that cannot be read does not take
 * the findings down with it).
 */

import { useQuery } from '@tanstack/react-query';

import type { RunId, VersionUid } from '@/shared/api';
import { runHasPublishedResult, runStatusQueryOptions, useRunList } from '@/entities/audit-run';
import { findingBlockIndex, useRunFindingBlocks } from '@/entities/block';
import { runFindingsQueryOptions } from '@/entities/finding';

import { NO_PAGE_FINDINGS, completeFindingsOf, findingsByBlock, findingsByPage, scopeRunId } from './page-findings';
import type { PageFindingsReading } from './page-findings';

export function usePageFindings(versionUid: VersionUid, geometryRunId: RunId | null): PageFindingsReading {
  const runs = useRunList(versionUid);
  const runId = scopeRunId(runs.isPending ? 'pending' : runs.data === undefined ? 'unreadable' : runs.data.items, geometryRunId);
  const status = useQuery({ ...runStatusQueryOptions((runId ?? '') as RunId), enabled: runId !== null });
  const published =
    status.data !== undefined && runHasPublishedResult(status.data.state, status.data.analysis_profile_id);
  const findings = useQuery({ ...runFindingsQueryOptions((runId ?? '') as RunId), enabled: runId !== null && published });
  const links = useRunFindingBlocks(runId, published && findings.data !== undefined);

  if (runId === null) return NO_PAGE_FINDINGS;
  if (status.isError) return { kind: 'unreadable', runId };
  if (status.data === undefined) return NO_PAGE_FINDINGS;
  if (!published) return { kind: 'no-result', runId };
  if (findings.isError) return { kind: 'unreadable', runId };
  if (findings.data === undefined) return NO_PAGE_FINDINGS;
  const items = completeFindingsOf(findings.data);
  if (items === null) return { kind: 'unreadable', runId };
  const index = findingBlockIndex(links.data);
  return {
    kind: 'read',
    runId,
    byPage: findingsByPage(items),
    runAt: status.data.created_at,
    ...(index === null ? {} : { blocks: { byBlock: findingsByBlock(items, index), unlinkedPages: index.unlinkedPages } }),
  };
}
