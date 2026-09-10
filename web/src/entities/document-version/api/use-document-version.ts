'use client';

/**
 * Read one published document version.
 *
 * A published version is immutable, so this query has no reason to refetch and no reason
 * to expire: `staleTime: Infinity` states that as a fact about the aggregate rather than
 * as a caching preference.
 */

import { useQuery } from '@tanstack/react-query';

import type { DocumentVersion, VersionUid } from '@/shared/api';
import { getDocumentVersion, queryKeys } from '@/shared/api';

export function useDocumentVersion(versionUid: VersionUid | null) {
  return useQuery<DocumentVersion>({
    queryKey: queryKeys.versions.detail(versionUid ?? ''),
    enabled: versionUid !== null && versionUid !== '',
    staleTime: Infinity,
    queryFn: async () => {
      const response = await getDocumentVersion({ path: { version_uid: versionUid ?? '' } });
      return response.data;
    },
  });
}
