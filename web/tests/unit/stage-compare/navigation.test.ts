import { describe, expect, it } from 'vitest';

import { anchorBox, assertRunRevision, evidenceFocus, rawFocus } from '@/_pages/stage-compare/model/navigation';
import { profileTextItems } from '@/_pages/stage-compare/api/workspace';
import { searchPageText } from '@/widgets/stage-text-evidence';
import type { StageLinkRevision } from '@/shared/api';

import { card, run } from '../stage-changes/fixtures';

const value = run();
const revision: StageLinkRevision = { revision_id: value.link_revision_id, pair_id: value.pair_id,
  created_at: value.created_at, revision_no: 1, source: 'expert', input_sha256: value.input_sha256,
  items: [{ item_id: 'sli_row', row_no: 1, relation: 'paired', left_profile_id: 'left', right_profile_id: 'right', confidence: 'manual' }] };

describe('stage evidence navigation', () => {
  it('keeps the actual source profiles and boxes with their saved run/revision', () => {
    const left = { evidence_id: 'sce_left', source_id: 'std_raw', kind: 'TEXT' as const, side: 'left' as const,
      profile_id: 'left', box_anchor: { x0: 10, top: 20, x1: 70, bottom: 40 } };
    const right = { ...left, evidence_id: 'sce_right', side: 'right' as const, profile_id: 'right' };
    const target = evidenceFocus(value, revision, left, card({ run_id: value.run_id, evidence: [left, right] }), 7);
    expect(target).toMatchObject({ token: 7, pairId: value.pair_id, runId: value.run_id,
      revisionId: revision.revision_id, leftProfileId: 'left', rightProfileId: 'right',
      leftBox: { x: 10, y: 20, width: 60, height: 20 }, rightBox: { x: 10, y: 20, width: 60, height: 20 } });
  });
  it('refuses cross-pair, cross-run and missing-source navigation', () => {
    expect(() => assertRunRevision(value, { ...revision, pair_id: 'other' }, value.pair_id)).toThrow();
    expect(() => evidenceFocus(value, revision, { evidence_id: 'sce_x', source_id: 'std_x', kind: 'TEXT', side: 'left', profile_id: 'right' }, card(), 1)).toThrow();
    expect(() => rawFocus(value, revision, undefined, undefined, 1)).toThrow();
    expect(anchorBox({ x0: 5, x1: 3, top: 1, bottom: 2 })).toBeUndefined();
  });
  it('joins original stored words into searchable lines with original point geometry', () => {
    const items = profileTextItems({ profile_id: 'p', version_uid: 'v', page_number: 1, scan: false,
      has_text_layer: true, width_pt: 500, height_pt: 300,
      words: [{ text: 'ВВГ', x0: 50, x1: 75, top: 10, bottom: 20 },
        { text: 'Кабель', x0: 10, x1: 45, top: 10, bottom: 20 },
        { text: 'Ошибка', x0: 4, x1: 1, top: 10, bottom: 20 }] });
    expect(items).toHaveLength(1);
    expect(searchPageText(items, 'кабель ввг')).toHaveLength(1);
    expect(items[0]?.box).toEqual({ x: 10, y: 10, width: 65, height: 10 });
  });
});
