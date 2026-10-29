'use client';

/**
 * Two small reads: the raster of a page (for a viewer opened on an added or removed sheet, which has no
 * canvas of its own, `getVersionPageProfile`) and the read-only summary of the comparison queue
 * (`getComparisonQueueSummary`, the block «Сравнение» of «Очередь»).
 */

import { useQuery } from '@tanstack/react-query';

import type { ComparisonPageProfileId, ComparisonQueueSummary, VersionPageProfile } from '@/shared/api';
import { getComparisonQueueSummary, getVersionPageProfile } from '@/shared/api';

import { COMPARISON_KEYS } from './keys';

export function usePageProfile(profileId: ComparisonPageProfileId | null) {
  return useQuery<VersionPageProfile>({
    queryKey: COMPARISON_KEYS.profile(profileId ?? 'none'),
    queryFn: async () =>
      (await getVersionPageProfile({ path: { comparison_page_profile_id: profileId as ComparisonPageProfileId } })).data,
    enabled: profileId !== null,
    retry: false,
  });
}

export function useComparisonQueueSummary() {
  return useQuery<ComparisonQueueSummary>({
    queryKey: COMPARISON_KEYS.queue(),
    queryFn: async () => (await getComparisonQueueSummary({})).data,
    retry: false,
  });
}
