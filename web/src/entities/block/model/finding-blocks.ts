/**
 * The portal blocks a run's findings sit in, as `listRunFindingBlocks` answers them (`UI-PARITY-C6`, contract 1.41.0).
 *
 * The server derives the relation on read from the evidence's place on its page and the portal's block boxes; it stores
 * nothing and moves no evidence (`analysis/geometry/finding_blocks.py` gives the rule and its misses). What the screens
 * need from the answer is small and is decided here, once:
 *
 *   - **Absent is not empty.** `not_produced` (no text-layer geometry for the run, or no portal geometry for the version)
 *     is no index at all, so nothing a screen says about a block's findings may rest on it; an index exists only for
 *     `produced`. Inside an index a finding with no block is a finding the server looked for and found none.
 *   - **An unlinked page is unknown, not free.** A block on a page in `unlinked_pages` has no number and is in no list
 *     of blocks «without findings»: the server could not place evidence on that page.
 *   - **A finding the answer does not name has no blocks to show**, never a guess from its page.
 */

import type { RunFindingBlockLinks } from '@/shared/api';

export interface FindingBlockIndex {
  /** Pages of the portal geometry on which no link can be derived. */
  readonly unlinkedPages: ReadonlySet<number>;
  /** Each named finding's portal block ids, in the portal list's order. */
  readonly byFinding: ReadonlyMap<string, readonly string[]>;
}

/** The index a produced answer is, or `null` when there is none (not produced, not read yet, or failed). */
export function findingBlockIndex(links: RunFindingBlockLinks | undefined): FindingBlockIndex | null {
  if (links === undefined || links.status !== 'produced') return null;
  return {
    unlinkedPages: new Set(links.unlinked_pages),
    byFinding: new Map(links.items.map((item) => [item.finding_uid, item.portal_block_ids])),
  };
}

const NO_BLOCKS: readonly string[] = [];

/** The ids of the blocks that hold a finding's evidence; empty when the index does not name the finding or names none. */
export function blocksOfFinding(index: FindingBlockIndex | null, findingUid: string): readonly string[] {
  return index?.byFinding.get(findingUid) ?? NO_BLOCKS;
}
