/**
 * The frames of a block finding on its page (`F8-WEB`, `D-683`, contract 1.52.0).
 *
 * A block finding has no text span to search for: the places it points at are the finding's `block_evidence`, each a block of the
 * portal on a page with a box normalised to that page (`bbox_norm`, 0 to 1, top-left origin). The page viewer frames a normalised
 * region by itself (`ViewerTarget.region`, the second authority of `open-evidence/model/targets.ts`), so a block is a target with a region
 * and no quotation: nothing is searched in the page text, so no frame is ever drawn round text nobody pointed at.
 *
 * A box the viewer cannot frame is said so, in words, and is never guessed: the box of a block that fills the whole page points at
 * nothing, and a box that is not four finite numbers inside the page is not a place. The card says which.
 *
 * Pure: no React, no query.
 */

import type { FindingBlockBox, FindingBlockEvidence } from '@/shared/api';
import type { Region, ViewerTarget } from '@/features/open-evidence';
import { regionOf } from '@/features/open-evidence';

/** How a block's box stands on its page: drawn, the whole page, or not a place. */
export type BlockFrame = 'framed' | 'whole_page' | 'unplaceable';

/** A box this close to the corners of the page is the whole page. */
const WHOLE_PAGE_EPSILON = 0.001;

function regionOfBox(box: FindingBlockBox): Region | null {
  return regionOf([box.x0, box.y0, box.x1, box.y1]);
}

/** Why a block's box has no frame, or that it has one. */
export function blockFrameOf(box: FindingBlockBox): BlockFrame {
  if (regionOfBox(box) !== null) return 'framed';
  const finite = [box.x0, box.y0, box.x1, box.y1].every((part) => typeof part === 'number' && Number.isFinite(part));
  const whole =
    finite && box.x0 <= WHOLE_PAGE_EPSILON && box.y0 <= WHOLE_PAGE_EPSILON && box.x1 >= 1 - WHOLE_PAGE_EPSILON && box.y1 >= 1 - WHOLE_PAGE_EPSILON;
  return whole ? 'whole_page' : 'unplaceable';
}

/** The sentence a block's card says about its frame. */
export const BLOCK_FRAME_SENTENCES: Readonly<Record<BlockFrame, string>> = {
  framed: 'Рамка отмечена по области блока на странице.',
  whole_page: 'Блок занимает всю страницу, поэтому рамка не рисуется.',
  unplaceable: 'Область блока не удалось отметить на странице: рамка не нарисована.',
};

/** One block on a page: its card, and the target the page viewer frames. */
export interface BlockCard {
  /** The target's id and the card's key: the block's place among the finding's blocks and its portal id. */
  readonly id: string;
  /** The number on the frame and on the card. */
  readonly badge: string;
  readonly page: number;
  readonly portalBlockId: string;
  /** The block's recognised text, when the server proved one for it: a recognised reading, never the document's text. */
  readonly recognisedQuote: string | undefined;
  readonly frame: BlockFrame;
  readonly target: ViewerTarget;
}

/** The distinct pages of a finding's blocks, ascending. */
export function blockPages(blocks: readonly FindingBlockEvidence[]): readonly number[] {
  return [...new Set(blocks.map((block) => block.page_number))].sort((left, right) => left - right);
}

/**
 * The cards of one page, in the finding's own order (`ordinal`). The number on a card is its place among the blocks of THIS page,
 * so the frames on a page read 1, 2, 3 whatever the other pages hold.
 */
export function blockCardsOnPage(blocks: readonly FindingBlockEvidence[], page: number): readonly BlockCard[] {
  return blocks
    .filter((block) => block.page_number === page)
    .sort((left, right) => left.ordinal - right.ordinal)
    .map((block, at) => {
      const id = `${block.ordinal}:${block.portal_block_id}`;
      const badge = String(at + 1);
      const region = regionOfBox(block.bbox_norm);
      return {
        id,
        badge,
        page,
        portalBlockId: block.portal_block_id,
        recognisedQuote: block.recognised_quote,
        frame: blockFrameOf(block.bbox_norm),
        target: region === null ? { id, badge } : { id, badge, region },
      };
    });
}
