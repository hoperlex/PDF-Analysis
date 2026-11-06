'use client';

/**
 * The run's findings, read for the tiles of «Блоки» (see `page-findings.ts` for what they may say).
 *
 * Two reads, in order: the run's status, to learn whether it published findings at all, and then its
 * complete finding list, the same read the review screen fills (`runFindingsQueryOptions`), so a
 * reader who came from «Разбор» finds both in the cache. The findings are not asked for a run that
 * has none to give.
 */

import { useQuery } from '@tanstack/react-query';

import type { RunId } from '@/shared/api';
import { runHasPublishedResult, runStatusQueryOptions } from '@/entities/audit-run';
import { runFindingsQueryOptions } from '@/entities/finding';

import { NO_PAGE_FINDINGS, completeFindingsOf, findingsByPage } from './page-findings';
import type { PageFindingsReading } from './page-findings';

export function usePageFindings(runId: RunId | null): PageFindingsReading {
  const status = useQuery({ ...runStatusQueryOptions((runId ?? '') as RunId), enabled: runId !== null });
  const published =
    status.data !== undefined && runHasPublishedResult(status.data.state, status.data.analysis_profile_id);
  const findings = useQuery({ ...runFindingsQueryOptions((runId ?? '') as RunId), enabled: runId !== null && published });

  if (runId === null) return NO_PAGE_FINDINGS;
  if (status.isError) return { kind: 'unreadable', runId };
  if (status.data === undefined) return NO_PAGE_FINDINGS;
  if (!published) return { kind: 'no-result', runId };
  if (findings.isError) return { kind: 'unreadable', runId };
  if (findings.data === undefined) return NO_PAGE_FINDINGS;
  const items = completeFindingsOf(findings.data);
  return items === null ? { kind: 'unreadable', runId } : { kind: 'read', runId, byPage: findingsByPage(items) };
}
