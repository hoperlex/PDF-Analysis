'use client';

/**
 * Read one published document version.
 *
 * A published version is immutable, so this query has no reason to refetch and no reason
 * to expire: `staleTime: Infinity` states that as a fact about the aggregate rather than
 * as a caching preference.
 *
 * `W59-SECTION-UI-01`: the one field that can still change is `classification`, written
 * once by an expert. The bytes and the manifest stay immutable; the classification command
 * (`features/classify-version`) writes its answer into this entry and invalidates it, so
 * the infinite stale time never shows a classification the server has since recorded.
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
