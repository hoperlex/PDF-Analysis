'use client';

import { useQuery } from '@tanstack/react-query';

import type { AnalysisProfileList } from '@/shared/api';
import { listAnalysisProfiles, queryKeys } from '@/shared/api';

/**
 * `listAnalysisProfiles` (`W59-ANALYSIS-SETTINGS-01`): the text-profile registry the server
 * routes runs through. One read, no paging — the answer is always the fifteen sections.
 *
 * The application's default freshness applies: the registry changes only when the server is
 * redeployed, so a tab return need not re-read it, and «Обновить» on the screen still does.
 */
export function analysisProfilesQueryOptions() {
  return {
    queryKey: queryKeys.analysis.profiles(),
    queryFn: async () => (await listAnalysisProfiles({})).data,
  } as const;
}

export function useAnalysisProfiles() {
  return useQuery<AnalysisProfileList>(analysisProfilesQueryOptions());
}
