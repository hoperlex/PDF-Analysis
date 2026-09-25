'use client';

/**
 * `getVersionBlocks` — the block index for one version. `W45-BLOCKS`.
 *
 * Local to this page rather than an `entities` hook: no other screen reads block
 * geometry, and `R-25`/`PROTOTYPE_PROFILE.md` §7.2 defer the section verticals that
 * might.
 *
 * `staleTime: Infinity` for the "produced" case would be premature: this deployment can
 * answer `not_produced` today and `produced` after a later run of the same version, and a
 * page a reviewer leaves open across that run should not go on saying "not built yet"
 * forever. So this query has the client's ordinary staleness (refetch on mount / window
 * focus) rather than the immutable-content treatment `useDocumentVersion` gives a
 * published version's own bytes.
 */

import { useQuery } from '@tanstack/react-query';

import type { VersionBlockIndex, VersionUid } from '@/shared/api';
import { getVersionBlocks, queryKeys } from '@/shared/api';

export function useVersionBlocks(versionUid: VersionUid | null) {
  return useQuery<VersionBlockIndex>({
    queryKey: queryKeys.versions.blocks(versionUid ?? ''),
    enabled: versionUid !== null && versionUid !== '',
    queryFn: async () => {
      const response = await getVersionBlocks({ path: { version_uid: versionUid ?? '' } });
      return response.data;
    },
  });
}
