'use client';

/**
 * `getComparisonOverview` — the table of «Проекты и этапы». Reading it starts nothing.
 *
 * The page polls every 5 s while anything is being computed or uploaded and every 30 s otherwise
 * (`version-comparison-projects.js:296-300`); `refetchInterval` reads the answer it just got.
 */

import { useQuery } from '@tanstack/react-query';

import type { ComparisonOverview, ProjectUid } from '@/shared/api';
import { getComparisonOverview } from '@/shared/api';

import { anythingRunning } from '../model/overview-view';

import { COMPARISON_KEYS } from './keys';

export const OVERVIEW_BUSY_POLL_MS = 5_000;
export const OVERVIEW_IDLE_POLL_MS = 30_000;

export function overviewQueryOptions(projectUid: ProjectUid) {
  return {
    queryKey: COMPARISON_KEYS.overview(projectUid),
    queryFn: async (): Promise<ComparisonOverview> => (await getComparisonOverview({ path: { project_uid: projectUid } })).data,
    refetchInterval: (query: { readonly state: { readonly data: ComparisonOverview | undefined } }) => {
      const data = query.state.data;
      if (data === undefined) return false;
      return anythingRunning(data.sets, data.pending_uploads.length) ? OVERVIEW_BUSY_POLL_MS : OVERVIEW_IDLE_POLL_MS;
    },
    retry: false,
  } as const;
}

export function useComparisonOverview(projectUid: ProjectUid | null) {
  return useQuery<ComparisonOverview>({
    ...overviewQueryOptions(projectUid ?? 'none'),
    enabled: projectUid !== null,
  });
}
