'use client';

import { useQuery } from '@tanstack/react-query';

import type { AnalysisPresetList } from '@/shared/api';
import { listAnalysisPresets } from '@/shared/api';

/**
 * The saved presets of how a run starts (`ANALYSIS-PRESETS-01`).
 *
 * The key lives here and not in `shared/api`'s registry: a preset is read by two screens (the
 * settings list and the start control) and written by one feature, and all three agree on this one
 * list. Every read is stale the moment it settles, so a revision or an archive an administrator
 * just made is what the next person sees; the commands invalidate it, and «Обновить» refetches.
 */
export const ANALYSIS_PRESETS_KEY = ['analysis-presets'] as const;

export function analysisPresetsQueryOptions() {
  return {
    queryKey: ANALYSIS_PRESETS_KEY,
    queryFn: async () => (await listAnalysisPresets({})).data,
    refetchOnWindowFocus: 'always',
    staleTime: 0,
  } as const;
}

export function useAnalysisPresets() {
  return useQuery<AnalysisPresetList>(analysisPresetsQueryOptions());
}
