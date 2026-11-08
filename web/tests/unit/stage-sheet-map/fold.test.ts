/**
 * `UI-B-93`: the fold of the sheet map is the page's to keep in the address.
 *
 * What is held: with no choice handed in the map folds itself, as it always did; with `rowsOpen` and `onRowsOpenChange` it
 * shows exactly what the page says and reports the reader's press instead of changing itself, so the address is the only
 * source; a place opened from the changes unfolds a folded map, as the original unfolds it, and a map that is already open
 * is not written again.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, describe, expect, it } from 'vitest';

import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';
import { StageSheetMap } from '@/widgets/stage-sheet-map';

import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { newClient } from '../screens/harness';
import { PROJECT_UID, uid } from '../version-compare/fixtures';

const PAIR = uid('stp', 32);
const LEFT = uid('cpr', 33);
const RIGHT = uid('cpr', 34);

function seeded() {
  const cache = newClient();
  cache.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID), {
    items: [{ pair_id: PAIR, project_uid: PROJECT_UID, left_document_uid: uid('doc', 35), right_document_uid: uid('doc', 36),
      completeness: 'unknown', state: 'confirmed', created_at: '2026-10-29T00:00:00Z' }],
    page: { next_cursor: null },
  });
  cache.setQueryData(['stage-sheet-map', PAIR, 'passports'], [
    { profile_id: LEFT, version_uid: uid('ver', 37), page_number: 1, side: 'left', sheet_type: 'план', building: '4', floor: '2' },
    { profile_id: RIGHT, version_uid: uid('ver', 38), page_number: 1, side: 'right', sheet_type: 'план', building: '4', floor: '2' },
  ]);
  cache.setQueryData(['stage-sheet-map', PAIR, 'suggestions'], {
    items: [{ left_profile_id: LEFT, right_profile_id: RIGHT, score: 11, confidence: 'high', reasons: ['building', 'floor', 'sheet_type'] }],
    page: { next_cursor: null },
  });
  cache.setQueryData(['stage-sheet-map', PAIR, 'current'], null);
  cache.setQueryData(['stage-sheet-map', PAIR, 'history'], { items: [], page: { next_cursor: null } });
  return cache;
}

describe('the fold of the map', () => {
  let live: LiveRender | null = null;
  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  const client = seeded();
  const mount = async (props: Record<string, unknown>) => {
    live = await mountLive(createElement(QueryClientProvider, { client },
      createElement(StageSheetMap, { projectUid: PROJECT_UID, mayAct: false, pairId: PAIR, ...props })));
    return live;
  };

  it('folds and unfolds itself when no choice is handed in', async () => {
    const view = await mount({});
    expect(view.markup()).toMatch(/aria-expanded="true"[^>]*>Свернуть</);
    expect(await view.press('Свернуть')).toBe(true);
    expect(view.markup()).toMatch(/aria-expanded="false"[^>]*>Развернуть</);
    expect(await view.press('Развернуть')).toBe(true);
    expect(view.markup()).toMatch(/aria-expanded="true"[^>]*>Свернуть</);
  });

  it('shows what the page says and reports the press, without changing itself', async () => {
    const told: boolean[] = [];
    const view = await mount({ rowsOpen: false, onRowsOpenChange: (open: boolean) => told.push(open) });
    expect(view.markup()).toMatch(/aria-expanded="false"[^>]*>Развернуть</);
    expect(view.markup()).not.toContain('<ol class');
    expect(await view.press('Развернуть')).toBe(true);
    expect(told).toEqual([true]);
    // The page did not move the address, so the map still shows the fold: the address is the only source.
    expect(view.markup()).toMatch(/aria-expanded="false"[^>]*>Развернуть</);
    await view.update(createElement(QueryClientProvider, { client },
      createElement(StageSheetMap, { projectUid: PROJECT_UID, mayAct: false, pairId: PAIR, rowsOpen: true, onRowsOpenChange: () => {} })));
    expect(view.markup()).toMatch(/aria-expanded="true"[^>]*>Свернуть</);
  });
});
