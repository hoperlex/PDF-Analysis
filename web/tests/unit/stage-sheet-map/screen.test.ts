import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';
import { StageSheetMap } from '@/widgets/stage-sheet-map';

import { newClient, renderScreen } from '../screens/harness';
import { PROJECT_UID, uid } from '../version-compare/fixtures';

const PAIR = uid('stp', 32);
const LEFT = uid('cpr', 33);
const RIGHT = uid('cpr', 34);

function screen(mayAct: boolean): string {
  const cache = newClient();
  cache.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID), {
    items: [{ pair_id: PAIR, project_uid: PROJECT_UID,
      left_document_uid: uid('doc', 35), right_document_uid: uid('doc', 36),
      completeness: 'unknown', state: 'confirmed', created_at: '2026-10-29T00:00:00Z' }],
    page: { next_cursor: null },
  });
  cache.setQueryData(['stage-sheet-map', PAIR, 'passports'], [
    { profile_id: LEFT, version_uid: uid('ver', 37), page_number: 1,
      side: 'left', sheet_type: 'план', building: '4', floor: '2' },
    { profile_id: RIGHT, version_uid: uid('ver', 38), page_number: 1,
      side: 'right', sheet_type: 'план', building: '4', floor: '2' },
  ]);
  cache.setQueryData(['stage-sheet-map', PAIR, 'suggestions'], {
    items: [{ left_profile_id: LEFT, right_profile_id: RIGHT,
      score: 11, confidence: 'high', reasons: ['building', 'floor', 'sheet_type'] }],
    page: { next_cursor: null },
  });
  cache.setQueryData(['stage-sheet-map', PAIR, 'current'], null);
  cache.setQueryData(['stage-sheet-map', PAIR, 'history'], { items: [], page: { next_cursor: null } });
  return renderScreen(cache, createElement(StageSheetMap, { projectUid: PROJECT_UID, mayAct }));
}

describe('stage sheet map screen', () => {
  it('shows two searchable sheet panels and expert decisions', () => {
    const html = screen(true);
    expect(html).toContain('Сопоставление листов');
    expect(html).toContain('Найти лист по штампу');
    expect(html).toContain('корпус 4');
    expect(html).toContain('Добавить связь');
    expect(html).toContain('Принять видимые точные подсказки');
    expect(html).toContain('Высокая уверенность: 1');
  });

  it('keeps the map readable without expert controls', () => {
    const html = screen(false);
    expect(html).toContain('Сопоставление листов');
    expect(html).toContain('Лист П');
    expect(html).toContain('Лист Р');
    expect(html).not.toContain('Добавить связь');
    expect(html).not.toContain('Сохранить решение эксперта');
  });
});
