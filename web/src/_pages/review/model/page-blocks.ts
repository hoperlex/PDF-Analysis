/**
 * Which portal blocks the strip under «Разбор»'s page may show for one cited page (`UI-A-74`).
 *
 * A finding names PAGES, never a portal block, so the strip is the blocks of the page the viewer is on and
 * says so. The blocks are the ones the «Блоки» tab already read for the version (`usePortalBlocks`, one
 * cursor read cached for the whole version); nothing is asked per finding. The API pages the list by cursor
 * ordered by page number, so what has been loaded is a prefix of the version's blocks:
 *
 *   - a page before the last loaded block's page is COMPLETE, whether it holds blocks or none;
 *   - the last loaded block's page may continue in the next cursor page (the cursor cuts by block, not by PDF
 *     page), so its blocks are shown with a sentence saying the page may have more;
 *   - a page after the last loaded block's page is NOT LOADED while another cursor page exists. That is not
 *     «no blocks», and the strip says so instead of staying silent.
 *
 * A version no run has read a bundle for answers `not_produced`, and a produced version with nothing on the
 * page has nothing to show: both are `none`, and `none` draws no strip at all.
 */

import type { PortalBlock, PortalBlockPage } from '@/shared/api';
import { loadedPortalBlocks } from '@/entities/block';

export type PageBlocksReading =
  | { readonly kind: 'none' }
  /** The blocks loaded for the page; `complete` is false while the page may continue in the next cursor page. */
  | { readonly kind: 'blocks'; readonly page: number; readonly blocks: readonly PortalBlock[]; readonly complete: boolean }
  /** The page lies beyond what has been loaded, and another cursor page exists. */
  | { readonly kind: 'not-loaded'; readonly page: number }
  /** The version's blocks could not be read. */
  | { readonly kind: 'unreadable'; readonly page: number };

export interface PageBlocksSource {
  /** The loaded cursor pages, or `undefined` when nothing has been read. */
  readonly pages: readonly PortalBlockPage[] | undefined;
  /** Whether the API reported a cursor page after the last one loaded. */
  readonly hasMore: boolean;
}

/** What the strip shows for `page`, from the cursor pages loaded so far. `pages: undefined` is a failed read. */
export function readPageBlocks({ pages, hasMore }: PageBlocksSource, page: number): PageBlocksReading {
  if (pages === undefined) return { kind: 'unreadable', page };
  const first = pages[0];
  if (first === undefined || first.status === 'not_produced') return { kind: 'none' };

  const loaded = loadedPortalBlocks(pages);
  const onPage = loaded.filter((block) => block.page_number === page);
  const lastLoadedPage = loaded.reduce((last, block) => Math.max(last, block.page_number), 0);

  if (onPage.length > 0) {
    return { kind: 'blocks', page, blocks: onPage, complete: !hasMore || page < lastLoadedPage };
  }
  return hasMore && page > lastLoadedPage ? { kind: 'not-loaded', page } : { kind: 'none' };
}

/**
 * The page the strip is about: the page the viewer is on when it is one the finding cites, otherwise the
 * first cited page (the viewer falls back the same way); `null` when the finding cites none.
 */
export function stripPageOf(citedPages: readonly number[], activePage: number | null): number | null {
  if (activePage !== null && citedPages.includes(activePage)) return activePage;
  return citedPages[0] ?? null;
}
