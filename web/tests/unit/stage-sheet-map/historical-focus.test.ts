import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { StageSheetMap } from '@/widgets/stage-sheet-map';
import { STAGE_TEXT_KEYS } from '@/widgets/stage-text-evidence';
import { newClient, renderScreen } from '../screens/harness';
import { run } from '../stage-changes/fixtures';
import { PROJECT_UID } from '../version-compare/fixtures';

describe('historical map navigation', () => {
  it('shows the saved row read-only while retaining a different current revision', () => {
    const cache = newClient();
    const value = run({ stale: true });
    const saved = { revision_id: value.link_revision_id, pair_id: value.pair_id, revision_no: 1,
      created_at: value.created_at, input_sha256: value.input_sha256, source: 'expert', items: [
        { item_id: 'sli_old', row_no: 1, relation: 'paired', confidence: 'manual', left_profile_id: 'old-left', right_profile_id: 'old-right' },
      ] };
    cache.setQueryData(['stage-evidence-revision', saved.revision_id], saved);
    cache.setQueryData(['stage-sheet-map', value.pair_id, 'current'], { ...saved, revision_id: 'new-revision', revision_no: 2,
      items: [{ ...saved.items[0], left_profile_id: 'new-left', right_profile_id: 'new-right' }] });
    cache.setQueryData(['stage-sheet-map', value.pair_id, 'passports'], []);
    cache.setQueryData(['stage-sheet-map', value.pair_id, 'suggestions'], { items: [], page: { next_cursor: null } });
    cache.setQueryData(['stage-sheet-map', value.pair_id, 'history'], { items: [saved], page: { next_cursor: null } });
    cache.setQueryData(['stage-full-run', value.run_id], value);
    cache.setQueryData(STAGE_TEXT_KEYS.evidence(value.pair_id, saved.revision_id), { fragments: [], exclusions: [], differences: [], hints: [] });
    const html = renderScreen(cache, createElement(StageSheetMap, { projectUid: PROJECT_UID, mayAct: true,
      pairId: value.pair_id, runId: value.run_id, focus: { token: 1, pairId: value.pair_id,
        runId: value.run_id, revisionId: saved.revision_id, leftProfileId: 'old-left', rightProfileId: 'old-right' }, onClearFocus: () => {} }));
    expect(html).toContain('Показана сохранённая карта выбранного запуска');
    expect(html).toContain('data-stage-focused-row="true"');
    expect(html).toContain('old-left');
    expect(html).not.toContain('new-left');
    expect(html).not.toContain('Сохранить решение эксперта');
    expect(html).not.toContain('Принять видимые точные подсказки');
  });
});
