/**
 * `D-317`: the knowledge base's «Все» -- the decisions on findings and on optimisation proposals as one list, in the
 * order the server merged them, each in the row form of a finding's decision and saying its kind.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { DecisionRecord, KnowledgeBaseEntry, ProposalDecisionRecord } from '@/shared/api';
import { KnowledgeBase } from '@/widgets/knowledge-base';

const ULID = '01M2545JSD15ETSNNV904X991F';

const FINDING: DecisionRecord = {
  decision_id: `dec_${ULID}`, finding_uid: `fnd_${ULID}`, finding_observation_id: `fobs_${ULID}`, event_type: 'accept',
  verdict: 'accepted', comment: null, author_label: 'Петрова А.', recorded_at: '2026-11-06T10:00:00Z',
  project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', run_id: `run_${ULID}`, document_uid: `doc_${ULID}`, version_uid: `ver_${ULID}`,
  project_name: 'Мост через Неву', document_name: 'АР-1', section: 'AR', category: 'internal_contradiction',
  finding_text: 'Отметка пола не совпадает с разрезом', current_verdict: 'accepted', decision_event_count: 1,
};

const PROPOSAL: ProposalDecisionRecord = {
  proposal_decision_id: 'opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', optimisation_proposal_id: 'opr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  optimisation_pass_id: 'opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', verdict: 'reject', comment: 'Аналог не подходит.',
  actor_label: 'Иванова А. С.', decided_at: '2026-11-06T09:00:00Z', project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  project_name: 'Мост через Неву', document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', document_name: 'Архитектурные решения',
  version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B', section: 'AR', row_text: 'Дверь металлическая ДМ-1',
  proposed_vendor: 'ООО «Двери»', unit: 'шт',
};

const ENTRIES: readonly KnowledgeBaseEntry[] = [
  { kind: 'finding', occurred_at: FINDING.recorded_at, finding: FINDING },
  { kind: 'proposal', occurred_at: PROPOSAL.decided_at, proposal: PROPOSAL },
];

const html = (entries: readonly KnowledgeBaseEntry[]) =>
  renderToStaticMarkup(createElement(KnowledgeBase, { records: [], entries }));

describe('«Все» in the knowledge base', () => {
  it('lists both kinds in the order the server merged them, each saying its kind', () => {
    const markup = html(ENTRIES);
    expect(markup).toContain('data-knowledge-base-kind="all"');
    expect(markup).toContain('data-record-count="2"');
    const finding = markup.indexOf(`data-decision-id="dec_${ULID}"`);
    const proposal = markup.indexOf('data-proposal-decision-id="opd_01J9ZQ8K7NHVXW3T2R5M6P4Q8B"');
    expect(finding).toBeGreaterThan(-1);
    expect(proposal).toBeGreaterThan(finding);
    expect(markup).toContain('Замечание · ');
    expect(markup).toContain('>Предложение<');
  });

  it('draws a proposal decision with its verdict, place, row, vendor, comment and the way to the optimisation', () => {
    const markup = html([ENTRIES[1] as KnowledgeBaseEntry]);
    expect(markup).toContain('отклонено');
    expect(markup).toContain('Дверь металлическая ДМ-1 · поставщик ООО «Двери» · ед. шт');
    expect(markup).toContain('Аналог не подходит.');
    expect(markup).toContain('Иванова А. С.');
    expect(markup).toContain(
      'href="/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8B?tab=optimisation&amp;pass=opp_01J9ZQ8K7NHVXW3T2R5M6P4Q8B"',
    );
    // The section by its title, as a finding's place names it, never the bare code.
    expect(markup).not.toMatch(/Архитектурные решения · AR</);
  });

  it('keeps «Замечания» as it was: no kind words without «Все»', () => {
    const markup = renderToStaticMarkup(createElement(KnowledgeBase, { records: [FINDING] }));
    expect(markup).not.toContain('Замечание · ');
    expect(markup).not.toContain('data-knowledge-base-kind');
  });
});
