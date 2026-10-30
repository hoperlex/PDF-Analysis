import { describe, expect, it } from 'vitest';

import type { StageAiReview, StageReviewDecision, StageTextFragment } from '@/shared/api';
import { acceptedSameFragments } from '@/widgets/stage-sheet-map/model/ai-masks';
import { focusedRow } from '@/widgets/stage-sheet-map/model/navigation';
import { provenFragments } from '@/widgets/stage-text-evidence';

const fragment = (id: string, side: 'left' | 'right'): StageTextFragment => ({ fragment_id: id, profile_id: `${side}-page`,
  pair_id: 'pair', side, text: 'Неизменный текст', content_key: 'a'.repeat(64), box_anchor: { x: 1, y: 2, width: 3, height: 4 } });
const fragments = [fragment('l', 'left'), fragment('r', 'right')];
const decision: StageReviewDecision = { status: 'SAME', confidence: 'high', left_fragment_ids: ['l'], right_fragment_ids: ['r'], reason: 'Совпадает', summary: 'Совпадает' };
function review(decisions: StageReviewDecision[]): StageAiReview {
  return { review_id: 'review', unit_id: 'unit', run_id: 'run', content_key: 'b'.repeat(64), source_sha256: 'c'.repeat(64),
    group_id: 'group', model_identity: {}, created_at: '2026-10-30T00:00:00Z', decisions };
}

describe('persisted AI overlay policy', () => {
  it('adds SAME/MOVED masks without modifying raw differences or exclusions', () => {
    const raw = { fragments, differences: [{ difference_id: 'std', revision_id: 'rev', status: 'changed' as const, left_fragment_id: 'l', right_fragment_id: 'r' }], exclusions: [], hints: [] };
    const before = JSON.stringify(raw);
    const ids = acceptedSameFragments(fragments, [review([decision])]);
    expect(ids).toEqual(['l', 'r']);
    expect(provenFragments({ ...raw, aiSameFragmentIds: ids }, 'left-page', 'left').map((item) => item.id)).toEqual(['l']);
    expect(JSON.stringify(raw)).toBe(before);
    expect(acceptedSameFragments(fragments, [review([{ ...decision, status: 'MOVED', actual_right_profile_ids: ['right-page'] }])])).toEqual(ids);
  });
  it('masks no partial/low-confidence/contradictory or foreign-side decision', () => {
    for (const refused of [{ ...decision, confidence: 'low' as const }, { ...decision, right_fragment_ids: ['missing'] },
      { ...decision, left_fragment_ids: ['r'] }, { ...decision, status: 'MOVED' as const, actual_right_profile_ids: ['other-page'] }]) {
      expect(acceptedSameFragments(fragments, [review([refused])])).toEqual([]);
    }
    expect(acceptedSameFragments(fragments, [review([decision, { ...decision, status: 'UNCERTAIN' }])])).toEqual([]);
  });
  it('focuses an actual row and never picks the first row for an empty target', () => {
    const rows = [{ relation: 'paired' as const, left_profile_id: 'one', right_profile_id: 'two' },
      { relation: 'paired' as const, left_profile_id: 'three', right_profile_id: 'four' }];
    const target = { token: 1, pairId: 'pair', runId: 'run', revisionId: 'rev' };
    expect(focusedRow(rows, target)).toBeUndefined();
    expect(focusedRow(rows, { ...target, leftProfileId: 'three', rightProfileId: 'four' })).toBe(1);
    expect(focusedRow(rows, { ...target, rightProfileId: 'two' })).toBe(0);
  });
});
