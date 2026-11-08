/**
 * Which portal blocks the strip «Блоки замечания» may show for one finding (`UI-PARITY-C6`, the original's thumbnails
 * under an opened finding, `UI-A-74`).
 *
 * The finding's block ids come from the server's relation (`listRunFindingBlocks`; `entities/block`'s `blocksOfFinding`),
 * the blocks themselves from the version's portal blocks the «Блоки» tab already read (`usePortalBlocks`, one cursor read
 * cached for the whole version). The cursor pages by page number, so what has been loaded is a prefix of the version's
 * blocks, and a linked block may lie in a page not loaded yet:
 *
 *   - every linked block that has been loaded is shown, in the portal's order;
 *   - the blocks that have not been loaded are counted, and while another cursor page exists the strip says so and offers
 *     the next portion as a press, as the page strip does (never on its own);
 *   - a finding with no linked block draws nothing: the page strip below it is the way to the page's other blocks.
 *
 * Nothing is drawn for a version whose blocks were not produced or could not be read: the page strip already says the
 * second, and a block id with no block behind it is not a thing to show.
 */

import type { PortalBlock, PortalBlockPage } from '@/shared/api';
import { loadedPortalBlocks } from '@/entities/block';

export type FindingBlocksReading =
  | { readonly kind: 'none' }
  | {
      readonly kind: 'blocks';
      /** The linked blocks that have been loaded, in the order the portal lists them. */
      readonly blocks: readonly PortalBlock[];
      /** How many linked blocks are not among the loaded ones. */
      readonly missing: number;
      /** False while a missing block may still arrive with the next cursor page. */
      readonly complete: boolean;
    };

export interface FindingBlocksSource {
  readonly pages: readonly PortalBlockPage[] | undefined;
  readonly hasMore: boolean;
}

export function readFindingBlocks(
  { pages, hasMore }: FindingBlocksSource,
  linkedIds: readonly string[],
): FindingBlocksReading {
  if (linkedIds.length === 0 || pages === undefined) return { kind: 'none' };
  const first = pages[0];
  if (first === undefined || first.status === 'not_produced') return { kind: 'none' };
  const wanted = new Set(linkedIds);
  const blocks = loadedPortalBlocks(pages).filter((block) => wanted.has(block.portal_block_id));
  const missing = wanted.size - new Set(blocks.map((block) => block.portal_block_id)).size;
  return { kind: 'blocks', blocks, missing, complete: missing === 0 || !hasMore };
}
