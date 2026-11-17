/**
 * `UIP-S09-01`: the rows of a table page stand by verdict -- waiting, accepted, for revision, rejected -- and keep their number.
 *
 * `orderProposalRows` is a pure function of the rows of one page. Each half has a case that shows it can fail:
 *
 *   - every verdict has its place and no other order passes (the four are fed in every arrangement a reader could reach, not only the
 *     reverse), the number order holds inside one verdict, and the input is neither changed nor returned;
 *   - what the reader sees is the same rows with the same numbers: drawn by the table, the rows come out in this order and each
 *     keeps its own number, its own `data-decision` and its own decision cell, so a row that moved did not change.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ProposalDecisionState } from '@/shared/api';
import { ProposalTable } from '@/widgets/optimisation-proposals';
import { orderProposalRows } from '@/widgets/optimisation-proposals/model/row-order';

import { newClient, renderScreen } from '../screens/harness';
import { decision, proposal } from './fixtures';

const row = (ordinal: number, verdict: ProposalDecisionState) => ({ ordinal, current_verdict: verdict });
const key = (rows: readonly { ordinal: number; current_verdict: ProposalDecisionState }[]) =>
  rows.map((entry) => `${entry.ordinal}:${entry.current_verdict}`);

describe('the order of the rows of a page', () => {
  it('puts the waiting first, then the accepted, those for revision and the rejected last', () => {
    const page = [row(1, 'reject'), row(2, 'revise'), row(3, 'accept'), row(4, 'pending')];
    expect(key(orderProposalRows(page))).toEqual(['4:pending', '3:accept', '2:revise', '1:reject']);
  });

  it('gives the same order whatever order the page came in', () => {
    const verdicts: readonly ProposalDecisionState[] = ['pending', 'accept', 'revise', 'reject'];
    const expected = ['pending', 'accept', 'revise', 'reject'];
    // Every arrangement of the four verdicts (24), so an order that is right for the reverse and for one rotation only fails.
    const arrangements = (rest: readonly ProposalDecisionState[]): ProposalDecisionState[][] =>
      rest.length <= 1
        ? [[...rest]]
        : rest.flatMap((first, index) =>
            arrangements([...rest.slice(0, index), ...rest.slice(index + 1)]).map((tail) => [first, ...tail]),
          );
    const all = arrangements(verdicts);
    expect(all).toHaveLength(24);
    for (const arrangement of all) {
      const page = arrangement.map((verdict, index) => row(index + 1, verdict));
      expect(orderProposalRows(page).map((entry) => entry.current_verdict), arrangement.join(',')).toEqual(expected);
    }
  });

  it('keeps the number order inside one verdict', () => {
    const page = [row(5, 'accept'), row(2, 'pending'), row(3, 'accept'), row(1, 'pending'), row(4, 'reject'), row(6, 'reject')];
    expect(key(orderProposalRows(page))).toEqual(['1:pending', '2:pending', '3:accept', '5:accept', '4:reject', '6:reject']);
  });

  it('changes no number: the same rows come back, each as it was', () => {
    const page = [row(3, 'reject'), row(1, 'accept'), row(2, 'pending')];
    const ordered = orderProposalRows(page);
    expect(ordered).toHaveLength(page.length);
    for (const entry of page) expect(ordered).toContain(entry);
  });

  it('does not change the page it is given, and returns a new list', () => {
    const page = [row(2, 'reject'), row(1, 'pending')];
    const before = key(page);
    const ordered = orderProposalRows(page);
    expect(key(page)).toEqual(before);
    expect(ordered).not.toBe(page);
    expect(orderProposalRows([])).toEqual([]);
  });
});

describe('the rows as the table draws them', () => {
  const ids = {
    reject: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q9A',
    accept: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q9B',
    pending: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q9C',
    revise: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q9D',
  } as const;
  // The server's page is in number order: 1 is rejected, 2 accepted, 3 waiting, 4 sent back.
  const items = (['reject', 'accept', 'pending', 'revise'] as const).map((verdict, index) =>
    proposal({
      optimisation_proposal_id: ids[verdict],
      ordinal: index + 1,
      current_verdict: verdict,
      current_decision: verdict === 'pending' ? null : decision({ verdict }),
    }),
  );
  const markup = renderScreen(newClient(), createElement(ProposalTable, { items, canDecide: false }));
  const rows = [...markup.matchAll(/<tr data-proposal="([^"]+)" data-proposal-ordinal="(\d+)" data-decision="([^"]+)">/g)].map(
    (match) => ({ id: match[1], ordinal: match[2], verdict: match[3] }),
  );

  it('stand waiting, accepted, for revision, rejected', () => {
    expect(rows.map((entry) => entry.verdict)).toEqual(['pending', 'accept', 'revise', 'reject']);
    expect(rows.map((entry) => entry.id)).toEqual([ids.pending, ids.accept, ids.revise, ids.reject]);
  });

  it('keep the number each proposal has, and say it in the first column with the state word', () => {
    expect(rows.map((entry) => entry.ordinal)).toEqual(['3', '2', '4', '1']);
    expect(markup).toMatch(/data-proposal-ordinal="3" data-decision="pending"><td class="[^"]*numberCell[^"]*"><strong>3<\/strong><span class="[^"]*state[^"]*">не решено<\/span>/);
    expect(markup).toMatch(/data-proposal-ordinal="1" data-decision="reject"><td class="[^"]*numberCell[^"]*"><strong>1<\/strong><span class="[^"]*state[^"]*">отклонено<\/span>/);
  });
});
