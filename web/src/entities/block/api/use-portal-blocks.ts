'use client';

/**
 * `listVersionPortalBlocks` — a version's portal blocks, one cursor page at a time
 * (`W55B-WEB-BLOCKS`).
 *
 * **Paged by the reader, never by a loop.** The first page loads with the tab; every later
 * page loads when the reader presses «Показать ещё» (`fetchNextPage`), and only then. A
 * version of ~130 blocks is one or two presses; a 500-page bundle may hold thousands, and a
 * loop that followed every cursor at once would read all of them — every recognised text,
 * every description — before the reader saw the first page. There is no automatic
 * continuation and no cap to raise: the number of requests is the number of presses.
 *
 * **One infinite query, keyed by version and page size** (`queryKeys.versions.portalBlocks`).
 * Each next page is asked for with the cursor the LAST loaded page returned and appended
 * after it, so a block is neither skipped nor repeated across a boundary as long as the
 * server keeps its own order (`entities/block/model/pages.ts` says why the client does not
 * repair one that does not).
 *
 * Freshness is the client's ordinary staleness, as `useVersionBlocks` reasons for the text
 * lines: a version answers `not_produced` until its first run and `produced` after it, and a
 * tab left open across that run should not keep saying "not yet" forever.
 */

import { useInfiniteQuery } from '@tanstack/react-query';

import type { PortalBlockPage, VersionUid } from '@/shared/api';
import { listVersionPortalBlocks, queryKeys } from '@/shared/api';

import { nextPortalCursor } from '../model/pages';

/**
 * Blocks per request. The contract allows 1 to 200 (default 50). A hundred keeps a
 * typical bundle (the owner's export: 129 blocks) to two requests while bounding one
 * response's recognised text; the crops are separate requests the browser makes lazily.
 */
export const PORTAL_BLOCK_PAGE_LIMIT = 100;

export function portalBlocksQueryOptions(versionUid: VersionUid) {
  return {
    queryKey: queryKeys.versions.portalBlocks(versionUid, PORTAL_BLOCK_PAGE_LIMIT),
    queryFn: async ({ pageParam, signal }: { pageParam: string | undefined; signal: AbortSignal }) =>
      (
        await listVersionPortalBlocks(
          {
            path: { version_uid: versionUid },
            query: {
              limit: PORTAL_BLOCK_PAGE_LIMIT,
              ...(pageParam === undefined ? {} : { cursor: pageParam }),
            },
          },
          { signal },
        )
      ).data,
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage: PortalBlockPage) => nextPortalCursor(lastPage),
  } as const;
}

export function usePortalBlocks(versionUid: VersionUid) {
  return useInfiniteQuery(portalBlocksQueryOptions(versionUid));
}
