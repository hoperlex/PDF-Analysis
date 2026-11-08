/**
 * «Без сущностей»: the blocks no finding of the run holds (`UI-PARITY-C6`, the original's `UI-A-84`).
 *
 * The list exists only when the run's block links are known (`PageFindingsReading.blocks`): without them «no finding in
 * this block» is not a fact anyone has. Inside it, a block on a page where the server could not place evidence
 * (`unlinkedPages`) is in neither list: it is unknown, not free of findings. The rest of the blocks that no finding holds
 * are split as the original splits them, by what the block itself holds (`hasMeaningfulContent`): the original says the
 * model read the first kind and the algorithm took the second out, a record this product does not keep, so the
 * headings here say what is known -- no finding of the run sits in the block; the block has nothing to read.
 */

import type { PortalBlock } from '@/shared/api';
import { hasMeaningfulContent } from '@/entities/block';

import type { PageFindingsReading } from './page-findings';

export interface NoEntityBlocks {
  /** «Замечаний не выявлено»: blocks with something to read that no finding of the run sits in. */
  readonly withoutFindings: readonly PortalBlock[];
  /** «Без значимого содержимого»: blocks with nothing to read (a stamp, an area the portal recognised nothing in). */
  readonly withoutContent: readonly PortalBlock[];
}

/** The loaded blocks that no finding holds, in the order given; `null` when the block links are not known. */
export function blocksWithoutFindings(blocks: readonly PortalBlock[], reading: PageFindingsReading): NoEntityBlocks | null {
  if (reading.kind !== 'read' || reading.blocks === undefined) return null;
  const { byBlock, unlinkedPages } = reading.blocks;
  const withoutFindings: PortalBlock[] = [];
  const withoutContent: PortalBlock[] = [];
  for (const block of blocks) {
    if (unlinkedPages.has(block.page_number) || byBlock.has(block.portal_block_id)) continue;
    (hasMeaningfulContent(block) ? withoutFindings : withoutContent).push(block);
  }
  return { withoutFindings, withoutContent };
}

/** The blocks of both lists in the order a block view walks them: the first list, then the second. */
export function noEntityWalk(groups: NoEntityBlocks): readonly PortalBlock[] {
  return [...groups.withoutFindings, ...groups.withoutContent];
}
