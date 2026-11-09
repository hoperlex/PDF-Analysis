/**
 * `D-344`, `UI-A-73`: the knowledge base says where a carried decision came from.
 *
 * Since contract 1.39.0 a finding decision carried over from an earlier version names its source (`DecisionRecord.carried_from`,
 * served by `listDecisions` and by the finding half of `listKnowledgeBaseEntries`). «Разбор», the decision history and «Принято»
 * draw «↩ Перенесено из V#» from it; the knowledge base drew the decision as an ordinary one.
 *
 * What is held, in BOTH views the screen has (the table and the events) and on BOTH tabs that carry findings («Замечания» and
 * «Все»): the mark is drawn in the row of a carried decision and in no other; in the table it stands in the decision's own
 * cell; the ordinal in it is the source version's display order, and nothing of the source's identity is printed. The
 * «Предложения» half is covered at the end: since contract 1.43.0 (`D-335`) `ProposalDecisionRecord.carried_from` names the
 * source of a carried proposal decision, and its row (in «Все», the table and the events) draws the same mark.
 *
 * Every positive assertion below fails on the widget as it was before this change: it drew none of these marks.
 */

import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DecisionCarriedFrom, DecisionRecord, KnowledgeBaseEntry } from '@/shared/api';
import { KnowledgeBase } from '@/widgets/knowledge-base';

const ULID = '01M2545JSD15ETSNNV904X991F';
const OTHER = '01M2545JSD15ETSNNV904X992A';

function record(over: Partial<DecisionRecord> = {}): DecisionRecord {
  return {
    decision_id: `dec_${ULID}`,
    finding_uid: `fnd_${ULID}`,
    finding_observation_id: `fobs_${ULID}`,
    event_type: 'accept',
    verdict: 'accepted',
    comment: 'Согласовано с заказчиком.',
    author_label: 'Петрова А.',
    recorded_at: '2026-09-10T09:00:00.000Z',
    project_uid: `prj_${ULID}`,
    run_id: `run_${ULID}`,
    document_uid: `doc_${ULID}`,
    version_uid: `ver_${ULID}`,
    project_name: 'Школа',
    document_name: 'АР-1',
    section: 'AR',
    category: 'internal_contradiction',
    severity: 'critical',
    finding_text: 'Срок поставки указан как 30 дней в §4 и как 45 дней в §9.',
    current_verdict: 'accepted',
    decision_event_count: 1,
    ...over,
  };
}

/** The source the contract names: the decision, its finding and its version, and the version's display ordinal. */
function source(ordinal: number): DecisionCarriedFrom {
  return {
    decision_id: `dec_${OTHER.slice(0, -1)}${ordinal}`,
    finding_uid: `fnd_${OTHER.slice(0, -1)}${ordinal}`,
    version_uid: `ver_${OTHER.slice(0, -1)}${ordinal}`,
    version_ordinal: ordinal,
  };
}

const CARRIED_ID = `dec_${ULID}`;
const DIRECT_ID = `dec_${OTHER}`;
const CARRIED = record({ carried_from: source(2) });
const DIRECT = record({ decision_id: DIRECT_ID, finding_uid: `fnd_${OTHER}`, recorded_at: '2026-09-09T09:00:00.000Z' });

const MARK = '↩ Перенесено из V2';

/** One row of the rendered list, by the decision it belongs to: a `<tr>` of the table or an `<li>` of the events. */
function rowOf(markup: string, decisionId: string): string {
  const match = markup.match(new RegExp(`<(tr|li)\\b[^>]*data-decision-id="${decisionId}"[\\s\\S]*?</\\1>`));
  expect(match, `no row for ${decisionId}`).not.toBeNull();
  return match?.[0] ?? '';
}

/** The cells of the table row, as text. */
function cellsOf(row: string): string[] {
  return [...row.matchAll(/<td[^>]*>([\s\S]*?)<\/td>/g)].map((cell) =>
    (cell[1] ?? '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim(),
  );
}

/** «Замечания» in the table view. */
function tableOf(records: readonly DecisionRecord[]): string {
  return renderToStaticMarkup(createElement(KnowledgeBase, { view: 'table', records }));
}

const asEntries = (records: readonly DecisionRecord[]): readonly KnowledgeBaseEntry[] =>
  records.map((row) => ({ kind: 'finding' as const, occurred_at: row.recorded_at, finding: row }));

const PROPOSAL: KnowledgeBaseEntry = {
  kind: 'proposal',
  occurred_at: '2026-11-06T09:00:00Z',
  proposal: {
    proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', optimisation_proposal_id: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
    optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', verdict: 'accept', comment: 'Аналог подходит.',
    actor_label: 'Иванова А. С.', decided_at: '2026-11-06T09:00:00Z', project_uid: `prj_${ULID}`,
    project_name: 'Мост через Неву', document_uid: `doc_${ULID}`, document_name: 'Архитектурные решения',
    version_uid: `ver_${ULID}`, section: 'AR', row_text: 'Дверь металлическая ДМ-1', proposed_vendor: 'ООО «Двери»', unit: 'шт',
  },
};

type View = 'table' | 'events';

/** «Замечания»: the finding journal as `records`. «Все»: both journals merged as `entries`. */
const TABS: readonly { readonly name: string; readonly draw: (view: View, records: readonly DecisionRecord[]) => string }[] = [
  {
    name: '«Замечания»',
    draw: (view, records) => renderToStaticMarkup(createElement(KnowledgeBase, { view, records })),
  },
  {
    name: '«Все»',
    draw: (view, records) =>
      renderToStaticMarkup(createElement(KnowledgeBase, { view, records: [], entries: [...asEntries(records), PROPOSAL] })),
  },
];

for (const view of ['table', 'events'] as const) {
  for (const tab of TABS) {
    describe(`the ${view === 'table' ? 'table' : 'events'} view of ${tab.name}`, () => {
      const markup = tab.draw(view, [CARRIED, DIRECT]);

      it('draws «↩ Перенесено из V#» in the row of a carried decision', () => {
        const row = rowOf(markup, CARRIED_ID);
        expect(row).toContain(MARK);
        expect(row).toContain('data-carried-from="2"');
      });

      it('draws nothing in the row of a decision made directly', () => {
        const row = rowOf(markup, DIRECT_ID);
        expect(row).not.toContain('Перенесено');
        expect(row).not.toContain('data-carried-from');
      });

      it('draws exactly one mark for the one carried decision, and none for the proposal in «Все»', () => {
        expect(markup.match(/data-carried-from=/g) ?? []).toHaveLength(1);
        expect(markup.match(/↩/g) ?? []).toHaveLength(1);
      });

      it('names the source version by its display ordinal and prints nothing of the source’s identity', () => {
        const other = tab.draw(view, [record({ carried_from: source(3) }), DIRECT]);
        expect(rowOf(other, CARRIED_ID)).toContain('↩ Перенесено из V3');
        expect(rowOf(other, CARRIED_ID)).not.toContain(MARK);
        // The source's decision, finding and version stay in the data the record holds; the screen prints the ordinal only.
        const from = source(2);
        for (const identity of [from.decision_id, from.finding_uid, from.version_uid]) {
          expect(markup).not.toContain(identity);
        }
      });
    });
  }
}

describe('where the mark stands', () => {
  it('in the table, in the cell of the decision, after its verdict', () => {
    const cells = cellsOf(rowOf(tableOf([CARRIED, DIRECT]), CARRIED_ID));
    const decision = cells[4] ?? '';
    expect(decision).toContain('принято');
    expect(decision).toContain(MARK);
    expect(decision.indexOf('принято')).toBeLessThan(decision.indexOf(MARK));
    // No other cell of the row carries it.
    expect(cells.filter((cell) => cell.includes('Перенесено'))).toHaveLength(1);
  });

  it('in the table, a decision made directly has an unchanged decision cell', () => {
    const decision = cellsOf(rowOf(tableOf([CARRIED, DIRECT]), DIRECT_ID))[4] ?? '';
    expect(decision).toContain('принято');
    expect(decision).not.toContain('Перенесено');
  });

  it('in the events, in the heading of the row, beside the verdict', () => {
    const row = rowOf(renderToStaticMarkup(createElement(KnowledgeBase, { records: [CARRIED, DIRECT] })), CARRIED_ID);
    const heading = row.match(/<p class="am-kb__heading">[\s\S]*?<\/p>/)?.[0] ?? '';
    expect(heading).toContain('am-kb__verdict');
    expect(heading).toContain(MARK);
  });

  it('wraps nothing for a decision made directly (no empty, spaced wrapper in the table)', () => {
    const markup = tableOf([DIRECT]);
    expect(markup).not.toContain('data-carried-from');
    const decisionCell = rowOf(markup, DIRECT_ID).match(/<td>(<span class="am-kb__verdict"[\s\S]*?)<\/td>/)?.[1] ?? '';
    expect(decisionCell).not.toBe('');
    // The verdict and the event label are the only two spans of the cell.
    expect(decisionCell.match(/<span\b/g) ?? []).toHaveLength(2);
  });
});

describe('the proposals half (`D-335`, contract 1.43.0)', () => {
  /** The source the contract names for a proposal decision: the decision, its pass and version, and the version's display ordinal. */
  const proposalSource = (ordinal: number) => ({
    proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
    optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8C',
    version_uid: `ver_${OTHER}`,
    version_ordinal: ordinal,
  });
  const carriedProposal = (ordinal: number): KnowledgeBaseEntry => ({
    ...PROPOSAL,
    proposal: { ...PROPOSAL.proposal!, carried_from: proposalSource(ordinal) },
  });
  const draw = (view: View, entry: KnowledgeBaseEntry) =>
    renderToStaticMarkup(createElement(KnowledgeBase, { view: view === 'table' ? 'table' : 'events', records: [], entries: [entry] }));

  for (const view of ['table', 'events'] as const) {
    it(`draws «↩ Перенесено из V#» on the row of a carried proposal decision in the ${view}`, () => {
      const markup = draw(view, carriedProposal(2));
      expect(markup).toContain('data-proposal-decision-id=');
      expect(markup).toContain(MARK);
      expect(markup).toContain('data-carried-from="2"');
      expect(markup.match(/↩/g) ?? []).toHaveLength(1);
    });

    it(`draws nothing on a proposal decision made directly in the ${view}`, () => {
      const markup = draw(view, PROPOSAL);
      expect(markup).toContain('data-proposal-decision-id=');
      expect(markup).not.toContain('Перенесено');
      expect(markup).not.toContain('data-carried-from');
    });

    it(`names the source version by its display ordinal only and prints nothing of its identity in the ${view}`, () => {
      const markup = draw(view, carriedProposal(3));
      expect(markup).toContain('↩ Перенесено из V3');
      for (const identity of [proposalSource(3).proposal_decision_id, proposalSource(3).optimisation_pass_id, proposalSource(3).version_uid]) {
        expect(markup).not.toContain(identity);
      }
    });
  }

  it('stands in the verdict cell of the table, after the verdict, and wraps nothing for a direct decision', () => {
    const cell = (entry: KnowledgeBaseEntry) =>
      cellsOf(draw('table', entry).match(/<tr\b[^>]*data-proposal-decision-id=[\s\S]*?<\/tr>/)?.[0] ?? '')[4] ?? '';
    const carried = cell(carriedProposal(2));
    expect(carried).toContain(MARK);
    expect(carried.indexOf('принято')).toBeGreaterThanOrEqual(0);
    expect(carried.indexOf('принято')).toBeLessThan(carried.indexOf(MARK));
    expect(cell(PROPOSAL)).not.toContain('Перенесено');
  });

  it('keeps the finding rows of «Все» as they were: one mark for the one carried finding decision, one for the carried proposal', () => {
    const markup = renderToStaticMarkup(
      createElement(KnowledgeBase, { records: [], entries: [...asEntries([CARRIED, DIRECT]), carriedProposal(2)] }),
    );
    expect(markup.match(/data-carried-from=/g) ?? []).toHaveLength(2);
  });
});
