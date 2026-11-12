/**
 * Where a finding stands: on text spans, or on portal blocks (`CRIT-SEAL-50`, contract 1.51.0; `D-683`, 1.52.0).
 *
 * A finding of a `one_list` run that comes from a drawing or a cross-check stands on the blocks of the portal: its
 * observation has `grounding_kind = portal_block`, no text span, and the places in the finding's `block_evidence`. A
 * text finding has none of the three new members (absent means text), and its places are the observation's `evidence`.
 * The rule is one function, read by the admission gate, the list's pages and the card, so they cannot disagree.
 */

import type { Finding, FindingBlockEvidence, FindingDetail } from '@/shared/api';

type Grounded = Pick<Finding | FindingDetail, 'observation' | 'block_evidence'>;

/** The blocks that hold the finding's evidence, in the server's order; none for a text finding. */
export function blockEvidenceOf(finding: Grounded): readonly FindingBlockEvidence[] {
  return finding.block_evidence ?? [];
}

/**
 * True when the finding stands on portal blocks: its observation is grounded on a block and the server named at least one.
 * A `portal_block` observation with no block is not grounded on anything, and is not this.
 */
export function groundedOnBlocks(finding: Grounded): boolean {
  return finding.observation.grounding_kind === 'portal_block' && blockEvidenceOf(finding).length > 0;
}

/**
 * True when the card has no text span to quote and stands on its blocks alone: a block-grounded finding whose observation
 * carries no `evidence`. Such a finding opens on the page with a frame at each block, not in the quotation viewer, which
 * refuses an observation with no evidence. A finding that has text spans (even one that also names blocks) is a text finding's card.
 */
export function standsOnBlocksOnly(finding: Grounded): boolean {
  return groundedOnBlocks(finding) && finding.observation.evidence.length === 0;
}
