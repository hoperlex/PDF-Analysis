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

/**
 * `UI-PARITY` «Блоки»: the page selector above the tiles.
 *
 * The original's selector is «Все блоки (N)» and one button per page with its count. The counts
 * here are of the blocks LOADED so far (the API pages by cursor), so a page the cursor has cut
 * shows what has arrived; the view says so beside the selector while another page of blocks is
 * waiting. Nothing is fetched for a count.
 */
export type PageSelection = 'all' | number;

export interface PageChip {
  readonly pageNumber: number;
  /** How many of the loaded blocks the page holds. */
  readonly count: number;
  readonly differingLabel: number | null;
}

/** One chip per loaded PDF page, in the order the sections are shown. */
export function pageChips(sections: readonly PortalPageSection[]): readonly PageChip[] {
  return sections.map((section) => ({
    pageNumber: section.pageNumber,
    count: section.blocks.length,
    differingLabel: section.differingLabel,
  }));
}

/** A selection of a page that is no longer among the loaded sections is the whole list again. */
export function effectiveSelection(sections: readonly PortalPageSection[], selection: PageSelection): PageSelection {
  if (selection === 'all') return 'all';
  return sections.some((section) => section.pageNumber === selection) ? selection : 'all';
}

/** The sections a selection shows: all of them, or the one page. */
export function sectionsOfSelection(
  sections: readonly PortalPageSection[],
  selection: PageSelection,
): readonly PortalPageSection[] {
  const chosen = effectiveSelection(sections, selection);
  return chosen === 'all' ? sections : sections.filter((section) => section.pageNumber === chosen);
}

/** The blocks of a selection in the order the tiles show them: the order «i / n» walks. */
export function blocksOfSelection(
  sections: readonly PortalPageSection[],
  selection: PageSelection,
): readonly PortalBlock[] {
  return sectionsOfSelection(sections, selection).flatMap((section) => section.blocks);
}

/**
 * The index ‹ or › leads to, or `null` at either end: the walk stops where the selection stops,
 * it does not wrap, and it does not leave the selection for the next page.
 */
export function stepIndex(index: number, count: number, direction: 1 | -1): number | null {
  const next = index + direction;
  return next >= 0 && next < count ? next : null;
}
