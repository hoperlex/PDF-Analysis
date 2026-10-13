/**
 * Loading a version's portal blocks page by page (`W55B-WEB-BLOCKS`): every block once, in
 * the API's order, each next page asked for with the cursor the last page returned — and
 * the crop address the `<img>` loads from.
 *
 * The infinite query is driven for real (`QueryClient.fetchInfiniteQuery` and
 * `fetchNextPage` over the widget's own query options) against a stand-in `fetch` that
 * serves a block list by cursor, so the request sequence asserted is the one the
 * application sends.
 */

import { InfiniteQueryObserver, QueryClient } from '@tanstack/react-query';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { PortalBlock, PortalBlockPage } from '@/shared/api';
import { MissingConfigurationError } from '@/shared/config';
import {
  PORTAL_BLOCK_PAGE_LIMIT,
  loadedPortalBlocks,
  portalBlockCropUrl,
  portalBlocksQueryOptions,
  sectionsByPage,
} from '@/entities/block';

import { BLOCKS_VERSION_UID, blockId, portalPage, textBlock } from './fixtures';

/** `n` blocks over pages of `perPage` PDF pages' worth, ordered as the API orders them. */
function blockList(n: number): PortalBlock[] {
  return Array.from({ length: n }, (_, i) =>
    textBlock({ portal_block_id: blockId(i + 1), page_number: Math.floor(i / 3) + 1, page_label: Math.floor(i / 3) + 1, ordinal: (i % 3) + 1 }),
  );
}

interface Served {
  readonly urls: string[];
}

/** A `fetch` that answers `listVersionPortalBlocks` from `all`, `limit` at a time, by cursor. */
function serve(all: readonly PortalBlock[]): Served {
  const urls: string[] = [];
  vi.stubGlobal('fetch', async (input: string) => {
    urls.push(input);
    const url = new URL(input, 'http://web.test');
    const limit = Number(url.searchParams.get('limit'));
    const cursor = url.searchParams.get('cursor');
    const start = cursor === null ? 0 : Number(cursor.replace('after-', ''));
    const items = all.slice(start, start + limit);
    const next = start + limit < all.length ? `after-${start + limit}` : null;
    const body: PortalBlockPage = portalPage(items, { block_count: all.length, page: { next_cursor: next } });
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  return { urls };
}

function client(): QueryClient {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

beforeEach(() => {
  vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '/bff/v1');
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe('each «Показать ещё» asks for the next page with the last page’s cursor', () => {
  it('loads every block exactly once, in order, across three pages', async () => {
    const all = blockList(PORTAL_BLOCK_PAGE_LIMIT * 2 + 7);
    const served = serve(all);
    const queries = client();
    const observer = new InfiniteQueryObserver(queries, portalBlocksQueryOptions(BLOCKS_VERSION_UID));
    const stop = observer.subscribe(() => {});
    try {
      await vi.waitFor(() => expect(observer.getCurrentResult().isSuccess).toBe(true));
      expect(observer.getCurrentResult().hasNextPage).toBe(true);
      await observer.fetchNextPage();
      await observer.fetchNextPage();
      const result = observer.getCurrentResult();
      expect(result.hasNextPage).toBe(false);

      const loaded = loadedPortalBlocks(result.data?.pages ?? []);
      expect(loaded.map((block) => block.portal_block_id)).toEqual(all.map((block) => block.portal_block_id));
      expect(new Set(loaded.map((block) => block.portal_block_id)).size).toBe(all.length);

      // The request sequence: no cursor, then each page's own continuation, each at the
      // declared page size -- and no request the reader did not ask for.
      expect(served.urls).toHaveLength(3);
      const params = served.urls.map((u) => new URL(u, 'http://web.test').searchParams);
      expect(params.map((p) => p.get('cursor'))).toEqual([null, `after-${PORTAL_BLOCK_PAGE_LIMIT}`, `after-${PORTAL_BLOCK_PAGE_LIMIT * 2}`]);
      expect(params.every((p) => p.get('limit') === String(PORTAL_BLOCK_PAGE_LIMIT))).toBe(true);
      expect(served.urls[0]).toContain(`/bff/v1/versions/${BLOCKS_VERSION_UID}/portal-blocks?`);
    } finally {
      stop();
    }
  });

  it('reads the first page only until the reader asks for more', async () => {
    const served = serve(blockList(PORTAL_BLOCK_PAGE_LIMIT * 3));
    const observer = new InfiniteQueryObserver(client(), portalBlocksQueryOptions(BLOCKS_VERSION_UID));
    const stop = observer.subscribe(() => {});
    try {
      await vi.waitFor(() => expect(observer.getCurrentResult().isSuccess).toBe(true));
      await new Promise((resolve) => setTimeout(resolve, 20));
      expect(served.urls).toHaveLength(1);
      expect(observer.getCurrentResult().data?.pages).toHaveLength(1);
    } finally {
      stop();
    }
  });
});

describe('the loaded pages read back as sections by PDF page', () => {
  it('joins a PDF page the cursor split across two API pages into one section', () => {
    const all = blockList(6); // pages 1 and 2, three blocks each
    const first = portalPage(all.slice(0, 4), { page: { next_cursor: 'c1' } });
    const second = portalPage(all.slice(4), { page: { next_cursor: null } });
    const sections = sectionsByPage(loadedPortalBlocks([first, second]));
    expect(sections.map((s) => s.pageNumber)).toEqual([1, 2]);
    expect(sections.map((s) => s.blocks.map((b) => b.portal_block_id))).toEqual([
      all.slice(0, 3).map((b) => b.portal_block_id),
      all.slice(3).map((b) => b.portal_block_id),
    ]);
  });

  it('repairs nothing: a block the server repeated is shown twice, not hidden', () => {
    const block = textBlock();
    const sections = sectionsByPage(loadedPortalBlocks([portalPage([block]), portalPage([block])]));
    expect(sections).toHaveLength(1);
    expect(sections[0]?.blocks).toHaveLength(2);
  });

  it('names the portal label only where it differs from the PDF page', () => {
    const sections = sectionsByPage([
      textBlock({ page_number: 1, page_label: 1 }),
      textBlock({ portal_block_id: blockId(9), page_number: 2, page_label: 7 }),
    ]);
    expect(sections.map((s) => s.differingLabel)).toEqual([null, 7]);
  });
});

describe('the crop address', () => {
  it('is the contract path under the configured base, each identifier encoded', () => {
    expect(portalBlockCropUrl(BLOCKS_VERSION_UID, blockId(2))).toBe(
      `/bff/v1/versions/${BLOCKS_VERSION_UID}/portal-blocks/${blockId(2)}/crop`,
    );
    expect(portalBlockCropUrl('ver_a/b', 'blk_c?d')).toBe('/bff/v1/versions/ver_a%2Fb/portal-blocks/blk_c%3Fd/crop');
  });

  it('refuses an unconfigured build rather than defaulting', () => {
    vi.stubEnv('NEXT_PUBLIC_API_BASE_URL', '');
    expect(() => portalBlockCropUrl(BLOCKS_VERSION_UID, blockId(2))).toThrow(MissingConfigurationError);
  });
});
