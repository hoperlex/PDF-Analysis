import { describe, expect, it } from 'vitest';

import type { StageTextFragment } from '@/shared/api';
import { fragmentBox, pageText, provenFragments, searchPageText } from '@/widgets/stage-text-evidence';

function fragment(id: string, profile: string, text: string, side: 'left' | 'right' = 'left'): StageTextFragment {
  return { fragment_id: id, profile_id: profile, pair_id: 'stp_pair', text, side,
    content_key: 'a'.repeat(64), box_anchor: { x0: 10, top: 20, x1: 90, bottom: 30 } };
}

describe('stage text evidence projection', () => {
  it('keeps point anchors and searches Cyrillic text without changing evidence', () => {
    const saved = fragment('f1', 'p1', 'Ёмкость 10 м³');
    expect(fragmentBox(saved)).toEqual({ x: 10, y: 20, width: 80, height: 10 });
    expect(searchPageText(pageText([saved], 'p1'), 'емкость')).toHaveLength(1);
    expect(saved.text).toBe('Ёмкость 10 м³');
  });

  it('only masks fragments named by proven exact exclusions on that page and side', () => {
    const left = fragment('f1', 'p1', 'Кабель ВВГ');
    const right = fragment('f2', 'p2', 'Кабель ВВГ', 'right');
    const unproven = fragment('f3', 'p1', 'Нагрузка 10 кВт');
    const data = { fragments: [left, right, unproven], differences: [], hints: [],
      exclusions: [{ exclusion_id: 'e1', revision_id: 'r1', left_fragment_id: 'f1',
        right_fragment_id: 'f2', proof_kind: 'same' as const }] };
    expect(provenFragments(data, 'p1', 'left').map((item) => item.id)).toEqual(['f1']);
    expect(provenFragments(data, 'p1', 'right')).toEqual([]);
    expect(fragmentBox({ ...left, box_anchor: { x0: 20, x1: 10, top: 1, bottom: 2 } })).toBeNull();
  });
});
