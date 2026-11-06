/**
 * The knowledge base's «Предложения» half (`R-151h`): the expert's decisions on optimisation proposals.
 *
 * Each row says the decision, when and by whom, the specification row, the proposed vendor and where it belongs, and
 * links the document's optimisation tab. The loading and empty branches say what they are about.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { ProposalDecisionRecord } from '@/shared/api';
import { ProposalDecisions } from '@/widgets/proposal-journal';

const RECORD: ProposalDecisionRecord = {
  proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', optimisation_proposal_id: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', verdict: 'reject', comment: 'Аналог не подходит.',
  actor_label: 'Иванова А. С.', decided_at: '2026-11-06T09:00:00Z', project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  project_name: 'Мост через Неву', document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', document_name: 'Архитектурные решения',
  version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', section: 'AR', row_text: 'Дверь металлическая ДМ-1',
  proposed_vendor: 'ООО «Двери»', unit: 'шт',
};

const html = (props: Parameters<typeof ProposalDecisions>[0]) => renderToStaticMarkup(createElement(ProposalDecisions, props));

describe('the proposal decisions of the knowledge base', () => {
  it('say the decision, its author, the row, the vendor and link the document’s optimisation tab', () => {
    const markup = html({ records: [RECORD] });
    expect(markup).toContain('отклонено');
    expect(markup).toContain('Иванова А. С.');
    expect(markup).toContain('Дверь металлическая ДМ-1');
    expect(markup).toContain('ООО «Двери»');
    // `UI-B-02`: the link opens the document's optimisation tab on the pass the decision was made in (`&` is escaped in markup).
    expect(markup).toContain(
      'href="/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B?tab=optimisation&amp;pass=opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B"',
    );
    expect(markup).toContain('Аналог не подходит.');
  });

  it('say what is loading and that nothing was decided, never an empty box', () => {
    expect(html({ records: [], isLoading: true })).toContain('Загрузка: решения по предложениям');
    expect(html({ records: [] })).toContain('Решений по предложениям оптимизации нет.');
  });
});
