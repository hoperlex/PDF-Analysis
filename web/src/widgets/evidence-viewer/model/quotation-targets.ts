/**
 * The quotations of one page, as targets for the page viewer. Pure.
 *
 * The id is the contract's `evidence_ordinal` (stable within an observation, and what the cards
 * are keyed by); the badge is the quotation's position in the card list, 1..n, so the number on
 * the frame is the number on the card. The server's line geometry is attached only when the
 * quotation's anchor agrees with the quotation beside it: an anchor that disagrees is already
 * reported on the card as a discrepancy, and lines picked by it would frame text nobody quoted.
 * Such a quotation is searched in the page text instead.
 */

import type { Evidence, VersionBlockIndex } from '@/shared/api';
import type { ViewerTarget } from '@/features/open-evidence';
import { lineRects } from '@/features/open-evidence';
import { anchorMatchesQuotation } from '@/entities/finding-observation';

export function quotationTargetId(item: Pick<Evidence, 'evidence_ordinal'>): string {
  return `q${item.evidence_ordinal}`;
}

export function quotationTargets(
  quotations: readonly Evidence[],
  blockIndex: VersionBlockIndex | null | undefined,
): readonly ViewerTarget[] {
  return quotations.map((item, at) => {
    const rects = anchorMatchesQuotation(item) ? lineRects(blockIndex, item) : null;
    return {
      id: quotationTargetId(item),
      badge: String(at + 1),
      quote: item.quote,
      ...(rects === null ? {} : { rects }),
    };
  });
}
