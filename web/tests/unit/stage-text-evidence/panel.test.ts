import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { StageTextEvidence } from '@/widgets/stage-text-evidence';
import type { StageTextEvidenceProps } from '@/widgets/stage-text-evidence';
import { newClient, renderScreen } from '../screens/harness';

function screen(overrides: Partial<StageTextEvidenceProps> = {}): string {
  return renderScreen(newClient(), createElement(StageTextEvidence, {
    revisionId: 'slk_current', mayAct: true, dirty: false, evidence: undefined,
    loading: false, needsRecompute: true, error: null, names: new Map(),
    onCompleted: () => {}, onFocus: () => {}, onHint: () => {}, ...overrides,
  }));
}

describe('stage text evidence panel', () => {
  it('offers explicit recomputation instead of claiming empty evidence', () => {
    const html = screen();
    expect(html).toContain('Нужно пересчитать сравнение');
    expect(html).toContain('Пересчитать текст');
    expect(html).not.toContain('Исходных текстовых различий не найдено');
  });

  it('shows stale drafts and raw before/after values without making a model decision', () => {
    const fragment = (id: string, profile: string, text: string, side: 'left' | 'right') => ({
      fragment_id: id, profile_id: profile, pair_id: 'stp_pair', text, side,
      content_key: 'a'.repeat(64), box_anchor: { x0: 1, top: 2, x1: 3, bottom: 4 },
    });
    const html = screen({ dirty: true, needsRecompute: false, evidence: {
      fragments: [fragment('f1', 'p1', 'Нагрузка 10 кВт', 'left'), fragment('f2', 'p2', 'Нагрузка 20 кВт', 'right')],
      exclusions: [], hints: [], differences: [{ difference_id: 'd1', revision_id: 'r1',
        left_fragment_id: 'f1', right_fragment_id: 'f2', status: 'changed' }],
    } });
    expect(html).toContain('Связи листов изменились');
    expect(html).toContain('Нагрузка 10 кВт → Нагрузка 20 кВт');
    expect(html).toContain('Исходные текстовые различия');
  });
});
