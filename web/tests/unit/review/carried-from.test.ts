/**
 * `UI-A-73`: «↩ Перенесено из V#» on a finding whose verdict an expert carried over from an earlier version.
 *
 * The mark is drawn from the server's structured link and from nothing else: `Finding.current_verdict_carried_from` on
 * the list and the table, `DecisionEvent.carried_from` in the history, the same object on the decision panel (a prop the
 * review page passes), and `AcceptedOptimisationProposal.carried_from` (`D-335`) on «Принято». A decision made directly
 * -- and every event written before migration 0058, which has no link -- draws nothing.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { DecisionCarriedFrom } from '@/shared/api';
import { carriedFromMark } from '@/entities/expert-decision';
import { groupByCategory } from '@/entities/finding';
import { DecisionHistory } from '@/widgets/decision-history';
import { DecisionPanel } from '@/widgets/decision-panel';
import { FindingList } from '@/widgets/finding-list';
import { SectionAcceptedList } from '@/widgets/section-accepted-optimisations';

import { acceptedRow, acceptedTape } from '../section-optimisation/fixtures';
import { decisionEvent, decisionId, findingDetail, observation, OBSERVATION_ID, render } from './fixtures';

const CARRIED: DecisionCarriedFrom = {
  decision_id: 'dec_01J9ZQ8K7NHVXW3T2R5M6P4Q9A',
  finding_uid: 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4Q9B',
  version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q9C',
  version_ordinal: 2,
};

const A = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA1';
const B = 'fnd_01J9ZQ8K7NHVXW3T2R5M6P4QA2';
const MARK = '↩ Перенесено из V2';

const GROUPS = groupByCategory([
  findingDetail({
    finding_uid: A,
    current_verdict: 'accepted',
    current_verdict_carried_from: CARRIED,
    observation: observation({ finding_text: 'Перенесённое замечание' }),
  }),
  findingDetail({
    finding_uid: B,
    current_verdict: 'accepted',
    observation: observation({ finding_text: 'Прямое замечание' }),
  }),
]);

function list(view: 'list' | 'table'): string {
  return render(createElement(FindingList, { groups: GROUPS, selectedFindingUid: null, onSelect: () => {}, view }));
}

describe('the mark', () => {
  it('names the source version by its display ordinal, and is nothing for a decision made directly', () => {
    expect(carriedFromMark(CARRIED)).toBe(MARK);
    expect(carriedFromMark({ ...CARRIED, version_ordinal: 11 })).toBe('↩ Перенесено из V11');
    expect(carriedFromMark(undefined)).toBeNull();
    expect(carriedFromMark(null)).toBeNull();
  });
});

describe.each(['list', 'table'] as const)('the findings %s', (view) => {
  it('marks the finding whose verdict was carried, and only that one', () => {
    const markup = list(view);
    expect(markup).toContain(MARK);
    expect((markup.match(/data-carried-from=/g) ?? []).length).toBe(1);
    expect(markup).toContain('data-carried-from="2"');
    // The mark stands in the row of the carried finding, not in the other one.
    const carriedRow = markup.indexOf('Перенесённое замечание');
    const directRow = markup.indexOf('Прямое замечание');
    expect(markup.indexOf(MARK)).toBeGreaterThan(Math.min(carriedRow, directRow));
    expect(carriedRow).toBeLessThan(directRow);
    expect(markup.indexOf(MARK)).toBeLessThan(directRow);
  });
});

describe('the decision history', () => {
  it('marks the event that was carried over and leaves every other event as it was', () => {
    const markup = render(
      createElement(DecisionHistory, {
        events: [
          decisionEvent({ decision_id: decisionId('A'), recorded_at: '2026-09-10T09:00:00.000Z', carried_from: CARRIED }),
          decisionEvent({
            decision_id: decisionId('B'), event_type: 'comment', verdict: null, comment: 'Согласовано.',
            recorded_at: '2026-09-10T10:00:00.000Z',
          }),
        ],
      }),
    );
    expect((markup.match(/data-carried-from=/g) ?? []).length).toBe(1);
    expect(markup).toContain(MARK);
    expect(markup.indexOf(MARK)).toBeLessThan(markup.indexOf('Согласовано.'));
  });

  it('draws nothing for a history of direct events', () => {
    expect(render(createElement(DecisionHistory, { events: [decisionEvent({})] }))).not.toContain('Перенесено');
  });
});

describe('the decision panel', () => {
  const base = {
    currentVerdict: 'accepted' as const,
    observationId: OBSERVATION_ID,
    onAccept: () => {},
    onReject: () => {},
    onComment: () => {},
  };

  it('says beside the current verdict that it was carried over', () => {
    const markup = render(createElement(DecisionPanel, { ...base, carriedFrom: CARRIED }));
    expect(markup).toContain(MARK);
    expect(markup.indexOf('текущий вердикт')).toBeLessThan(markup.indexOf(MARK));
  });

  it('says nothing when the verdict was decided directly', () => {
    expect(render(createElement(DecisionPanel, base))).not.toContain('Перенесено');
  });
});

describe('«Принято»', () => {
  function accepted(rows: Parameters<typeof SectionAcceptedList>[0]['page']['items']): string {
    return render(
      createElement(SectionAcceptedList, {
        page: { items: rows, page: { next_cursor: null }, total: rows.length },
        hasPrevious: false,
        onPrevious: () => {},
        onNext: () => {},
      }),
    );
  }

  it('marks an acceptance carried over from an earlier version’s pass (D-335)', () => {
    const markup = accepted([
      acceptedRow({
        carried_from: {
          proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q9D',
          optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q9E',
          version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q9F',
          version_ordinal: 2,
        },
      }),
      acceptedTape(),
    ]);
    expect((markup.match(/data-carried-from=/g) ?? []).length).toBe(1);
    expect(markup).toContain(MARK);
  });

  it('draws nothing for acceptances made directly', () => {
    expect(accepted([acceptedRow(), acceptedTape()])).not.toContain('Перенесено');
  });
});
