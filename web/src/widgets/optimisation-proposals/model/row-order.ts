/**
 * `UIP-S09-01`: the order of the rows of a table page, as the original draws its table -- those still waiting first, then the accepted,
 * then those sent back for revision, the rejected last -- so a page the expert is working through keeps its open work on top and its
 * settled rows below.
 *
 * It orders the rows of ONE page and changes nothing else: the number of a proposal (`ordinal`) is the server's and stays what it was,
 * and the pages themselves are still the server's, in its own order. A row moves only when the verdict of another row of the same page
 * stands before it in this order; within one verdict the rows keep their number order. The ordering across pages needs a sort on the
 * server and is not made here (`UIP-S09-01`, open question). Pure: rows in, the same rows out, the input untouched.
 */

import type { OptimisationProposal, ProposalDecisionState } from '@/shared/api';

/** A verdict's place: waiting, accepted, for revision, rejected. A `Record`, so a verdict the contract adds cannot be left without one. */
const RANK: Readonly<Record<ProposalDecisionState, number>> = {
  pending: 0,
  accept: 1,
  revise: 2,
  reject: 3,
};

type Row = Pick<OptimisationProposal, 'current_verdict' | 'ordinal'>;

/** The rows of a page in the order of the table: by verdict, then by number; the same array is never returned and the input is not changed. */
export function orderProposalRows<T extends Row>(items: readonly T[]): readonly T[] {
  return items
    .map((row, index) => ({ row, index }))
    .sort(
      (a, b) =>
        RANK[a.row.current_verdict] - RANK[b.row.current_verdict] ||
        a.row.ordinal - b.row.ordinal ||
        a.index - b.index,
    )
    .map(({ row }) => row);
}
