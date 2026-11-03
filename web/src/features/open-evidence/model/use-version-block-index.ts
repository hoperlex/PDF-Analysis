'use client';

/**
 * `getVersionBlocks` for the viewer: the line geometry of one version.
 *
 * The review screen calls this, not the viewer, because that screen owns the queries (the header
 * of `_pages/review/ui/review-page.tsx` says why) and the widgets stay pure. It shares its query
 * key and its answer's shape with the «Блоки» screen's own hook, so a reviewer who has opened one
 * has already paid for the other.
 *
 * The answer is a progressive enhancement and says so by what the viewer does with it: a version
 * whose geometry is `not_produced`, a request that failed and a request still in flight all give
 * `null` here, and the viewer then places the quotation by searching the page text instead. The
 * card beside the page names the method that was used (`targets.ts`), so the fallback is never
 * silent.
 *
 * Ordinary staleness, not the immutable treatment the version's own bytes get: a version can
 * answer `not_produced` today and `produced` after a later run, and a page left open across
 * that run should not go on saying «разметка не построена» for ever.
 */

import { useQuery } from '@tanstack/react-query';

import type { VersionBlockIndex, VersionUid } from '@/shared/api';
import { getVersionBlocks, queryKeys } from '@/shared/api';

export function useVersionBlockIndex(versionUid: VersionUid | null): VersionBlockIndex | null {
  const query = useQuery<VersionBlockIndex>({
    queryKey: queryKeys.versions.blocks(versionUid ?? ''),
    enabled: versionUid !== null && versionUid !== '',
    queryFn: async ({ signal }) => {
      const response = await getVersionBlocks({ path: { version_uid: versionUid ?? '' } }, { signal });
      return response.data;
    },
  });
  return query.data ?? null;
}
