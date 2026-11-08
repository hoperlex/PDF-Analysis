/**
 * Whether a portal block carries anything a reader could read (`UI-PARITY-C6`, the original's «Без сущностей»).
 *
 * The original splits the blocks no finding names into «Замечаний не выявлено» (the model read them) and «Без значимого
 * содержимого» (the algorithm did not take them: stamps, empty areas, service inserts). This product keeps no record of
 * which blocks a run read, so the split is by what the block itself holds, which the response states:
 *
 *   - a STAMP holds neither an image nor text: no meaningful content;
 *   - a TEXT block holds its recognised text; one the portal recognised nothing in is an empty area;
 *   - an IMAGE block holds an image, whether or not this product could cut its crop.
 */

import type { PortalBlock } from '@/shared/api';

export function hasMeaningfulContent(block: PortalBlock): boolean {
  if (block.block_type === 'stamp') return false;
  if (block.block_type === 'text') return block.recognised_text !== undefined;
  return true;
}
