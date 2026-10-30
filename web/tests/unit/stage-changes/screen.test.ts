import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { StageCardView, StageChanges, StageJournal } from '@/widgets/stage-changes';
import { STAGE_REVIEW_KEYS } from '@/widgets/stage-changes/api/reads';
import { journalGroups } from '@/widgets/stage-changes/model/journal';
import { StageHighLevelChanges } from '@/widgets/stage-changes/ui/stage-high-level-changes';

import { newClient, renderScreen } from '../screens/harness';
import { NOW, uid } from '../version-compare/fixtures';
import { card, journal, run } from './fixtures';

describe('stage review UI', () => {
  it('renders evidence and absence uncertainty, while stale cards have no expert radio', () => {
    const cache = newClient();
    const html = renderScreen(cache, createElement(StageCardView, { card: card({ before: '', stale: true }),
      mayAct: true, draft: undefined, onDraft: () => {}, onOpenEvidence: () => {} }));
    expect(html).toContain('Отсутствие объекта не доказано');
    expect(html).toContain('Открыть в PDF');
    expect(html).toContain('TEXT');
    expect(html).not.toContain('type="radio"');
  });

  it('shows an accepted expert verdict with its carryover state', () => {
    const value = card({ carryover: 'full', verdict: { verdict_id: uid('cdv', 1), card_id: card().card_id,
      revision_no: 1, decision: 'accepted', reason: '', evidence_digest: card().evidence_digest, created_at: NOW } });
    const html = renderScreen(newClient(), createElement(StageCardView, { card: value, mayAct: false,
      draft: undefined, onDraft: () => {}, onOpenEvidence: () => {} }));
    expect(html).toContain('Принято экспертом');
    expect(html).toContain('Решение перенесено по тем же свидетельствам');
  });

  it('does not use right-side absence proof to claim absence on the left', () => {
    const html = renderScreen(newClient(), createElement(StageCardView, { card: card({ before: '',
      evidence: [{ evidence_id: uid('std', 1), source_id: uid('std', 1), kind: 'TEXT', side: 'right', absence_proven: true }] }),
      mayAct: false, draft: undefined, onDraft: () => {}, onOpenEvidence: () => {} }));
    expect(html).toContain('Отсутствие объекта не доказано');
  });

  it('uses server counts without making up missing high importance counts', () => {
    const cache = newClient();
    cache.setQueryData(['stage-review-run', run().run_id], run({ stale: true }));
    cache.setQueryData(STAGE_REVIEW_KEYS.cards(run().run_id), { cards: [card()], counts: { total: 7, review: 2, conflicts: 1 } });
    const html = renderScreen(cache, createElement(StageChanges, { runId: run().run_id, mayAct: false, onOpenEvidence: () => {} }));
    expect(html).toContain('<dd>7</dd>');
    expect(html).toContain('<dd>—</dd>');
    expect(html).toContain('Есть новые документы или изменены связи');
    expect(html).toContain('Показать исходные текстовые различия');
  });

  it('renders real journal groups and all three export actions', () => {
    const cache = newClient();
    const result = journal({ stale: true });
    cache.setQueryData(['stage-review-run', run().run_id], run());
    cache.setQueryData([...STAGE_REVIEW_KEYS.journal(run().run_id), 'designation'], { result, groups: journalGroups(result) });
    const html = renderScreen(cache, createElement(StageJournal, { runId: run().run_id, mayAct: false, onOpenEvidence: () => {} }));
    for (const text of ['Итоговый журнал изменений', 'АР', '900 мм', '1000 мм', 'Excel', 'PDF', 'HTML', 'Сравнение устарело']) expect(html).toContain(text);
  });

  it('offers immutable service promotion independently of verdict editing and uses actual importance', () => {
    const value = card({ class_name: 'SERVICE_STRUCTURE', importance: 'high', materiality: 'non_material' });
    const html = renderScreen(newClient(), createElement(StageCardView, { card: value, mayAct: false, mayRequestReview: true,
      draft: undefined, onDraft: () => {}, onOpenEvidence: () => {} }));
    expect(html).toContain('Отправить на проверку');
    expect(html).toContain('data-stage-card-importance="high"');
    expect(html).toContain('Несущественное изменение');
    expect(html).not.toContain('type="radio"');
  });

  it('opens synthesis sources by raw source identity rather than UI anchor identity', () => {
    const cache = newClient();
    const rawId = uid('std', 1);
    const value = card({ evidence_ids: [rawId], evidence: [{ evidence_id: uid('sce', 1), source_id: rawId,
      kind: 'TEXT', side: 'left', profile_id: uid('cpr', 1) }] });
    cache.setQueryData(['stage-high-level', value.run_id], [{ synthesis_id: uid('sasyn', 1), run_id: value.run_id,
      result: { decision: 'REAL_CHANGE', change_type: 'PARAMETER_SET_CHANGED', title: 'Изменён размер', reason: 'Размер изменён', evidence_ids: [rawId] } }]);
    const html = renderScreen(cache, createElement(StageHighLevelChanges, { runId: value.run_id, cards: [value],
      running: false, completed: true, onOpenEvidence: () => {} }));
    expect(html).toContain('Открыть в PDF');
  });
});
