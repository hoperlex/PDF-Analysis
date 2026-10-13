/**
 * The loaded pages of `listVersionPortalBlocks`, read back as the screen shows them.
 *
 * The API pages a version's blocks by cursor, ordered by `page_number`, `ordinal` (null
 * last) and `portal_block_id`, and the cursor carries that key and nothing else. So the
 * blocks in the order the reader sees them are exactly the loaded pages concatenated in the
 * order they were loaded: nothing here re-sorts, de-duplicates or fills a gap. A sort would
 * hide a server that broke its order; a de-duplication would hide a server that repeated a
 * block across a cursor; both are failures the screen should show rather than repair.
 *
 * A PDF page can straddle two API pages (the cursor cuts by block, not by PDF page), so the
 * grouping is by `page_number` over the concatenation: the second half of a page's blocks
 * joins the section its first half opened.
 */

import type { PortalBlock, PortalBlockPage } from '@/shared/api';

/** Every block of every loaded page, in the order the pages were loaded. */
export function loadedPortalBlocks(pages: readonly PortalBlockPage[]): readonly PortalBlock[] {
  return pages.flatMap((page) => page.items);
}

/** One PDF page's section: its true page number, the portal's label, its blocks in order. */
export interface PortalPageSection {
  readonly pageNumber: number;
  /** The portal's own label when it differs from the PDF page number; `null` when equal. */
  readonly differingLabel: number | null;
  readonly blocks: readonly PortalBlock[];
}

/**
 * Group the blocks by PDF page, in first-seen order of the page and API order within it.
 *
 * `page_label` is the portal's own label of the page; the section shows the one its first
 * block carries.
 */
export function sectionsByPage(blocks: readonly PortalBlock[]): readonly PortalPageSection[] {
  const order: number[] = [];
  const byPage = new Map<number, { label: number; blocks: PortalBlock[] }>();
  for (const block of blocks) {
    let section = byPage.get(block.page_number);
    if (section === undefined) {
      section = { label: block.page_label, blocks: [] };
      byPage.set(block.page_number, section);
      order.push(block.page_number);
    }
    section.blocks.push(block);
  }
  return order.map((pageNumber) => {
    const section = byPage.get(pageNumber) as { label: number; blocks: PortalBlock[] };
    return {
      pageNumber,
      differingLabel: section.label === pageNumber ? null : section.label,
      blocks: section.blocks,
    };
  });
}

/** The continuation a reader's «Показать ещё» asks for: the last loaded page's cursor. */
export function nextPortalCursor(lastPage: PortalBlockPage): string | undefined {
  return lastPage.page.next_cursor ?? undefined;
}
