import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { looksLikeArV3GroupId } from '@/entities/audit-run';
import type { ArV3BetaGroupReview } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { ArV3BetaReview } from '@/widgets/ar-v3-beta-review';

import { newClient, renderScreen } from '../screens/harness';

const GROUP_ID = 'arg_01M2545JSD15ETSNNV904X991K';
const SCOPES = ['F1', 'F2', 'A1', 'A2', 'S1', 'S2'] as const;

function fixture(): ArV3BetaGroupReview {
  return {
    group_id: GROUP_ID,
    version_uid: 'ver_01M2545JSD15ETSNNV904X991J',
    members: SCOPES.map((scope, index): ArV3BetaGroupReview['members'][number] => ({
      scope_id: scope,
      run_id: `run_01M2545JSD15ETSNNV904X991${'KMNPQR'[index]}`,
      run_state: index === 0 ? 'published' : index === 1 ? 'failed' : index === 2 ? 'partial' : 'queued',
      review_state: index === 0 ? 'available' : index === 1 ? 'failed' : index === 2 ? 'verification_refused' : 'pending',
      terminal_reason: index === 1 ? 'dependency_unavailable' : null,
      refusal_code: index === 2 ? 'storage_integrity_error' : null,
      review: index === 0 ? {
        topics: [{
          item_id: 'C01', mode: 'provisional_citation', reason: 'edition check',
          source_ids: ['D1_LOCAL'], review_status: 'requires_expert_review',
          provisional_citation_count: 1,
        }],
        provisional_citations: [{
          proposal_ordinal: 0,
          evidence: [{ page_number: 3, quote: 'ширина двери' }],
          citations: [{
            item_id: 'C01', label: 'N1', document_id: 'ndoc_example',
            paragraph_id: 'npar_example', raw_quote: '<script>цитата</script>', state: 'grounded',
          }],
        }],
        withheld_proposal_count: 1,
        rejected_proposal_count: 0,
      } : null,
    })),
  };
}

describe('AR v3 beta group review panel', () => {
  it('sends no read without a valid opaque group ID', () => {
    expect(looksLikeArV3GroupId(GROUP_ID)).toBe(true);
    expect(looksLikeArV3GroupId('arg_bad')).toBe(false);
    const empty = renderScreen(newClient(), createElement(ArV3BetaReview, { groupId: null }));
    expect(empty).toContain('Показать разбор');
    expect(empty).not.toContain('Загрузка: разбора группы');
    const invalid = renderScreen(newClient(), createElement(ArV3BetaReview, { groupId: 'arg_bad' }));
    expect(invalid).toContain('Неверный идентификатор группы');
  });

  it('shows all six states and escaped provisional evidence without claiming a verdict', () => {
    const client = newClient();
    client.setQueryData(queryKeys.runs.arV3GroupReview(GROUP_ID), fixture());
    const markup = renderScreen(client, createElement(ArV3BetaReview, { groupId: GROUP_ID }));
    expect([...markup.matchAll(/data-ar-v3-review-scope="([A-Z][0-9])"/g)].map((match) => match[1]))
      .toEqual([...SCOPES]);
    expect(markup).toContain('Прогон завершился ошибкой');
    expect(markup).toContain('Проверка сохранённого разбора отказала');
    expect(markup).toContain('ширина двери');
    expect(markup).toContain('&lt;script&gt;цитата&lt;/script&gt;');
    expect(markup).not.toContain('<script>цитата</script>');
    expect(markup).toContain('Числовой или правовой вывод здесь не утверждён');
  });

  it('refuses a partial six-scope response instead of displaying its one available quote', () => {
    const client = newClient();
    const broken = fixture();
    client.setQueryData(queryKeys.runs.arV3GroupReview(GROUP_ID), {
      ...broken, members: broken.members.slice(0, 1),
    });
    const markup = renderScreen(client, createElement(ArV3BetaReview, { groupId: GROUP_ID }));
    expect(markup).toContain('Разбор группы не подтверждён');
    expect(markup).not.toContain('ширина двери');
  });
});
