'use client';

import { useQuery } from '@tanstack/react-query';

import { getProductVersion, listReleases, queryKeys } from '@/shared/api';

export function useReleases(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.releases.list(),
    queryFn: async () => (await listReleases({})).data,
    enabled,
    retry: false,
  });
}

export function useProductVersion(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.releases.version(),
    queryFn: async () => (await getProductVersion({})).data,
    enabled,
    retry: false,
  });
}
