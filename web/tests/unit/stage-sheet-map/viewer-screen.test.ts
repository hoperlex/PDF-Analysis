import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { StageSheetPassport, StageTextFragment, VersionPageProfile } from '@/shared/api';
import { StagePairViewer } from '@/widgets/stage-sheet-map';
import { newClient, renderScreen } from '../screens/harness';

function screen(stale: boolean): string {
  const cache = newClient();
  const left: StageSheetPassport = { profile_id: 'left', version_uid: 'ver_left', page_number: 1, side: 'left' };
  const right: StageSheetPassport = { profile_id: 'right', version_uid: 'ver_right', page_number: 2, side: 'right' };
  for (const page of [left, right]) {
    const profile: VersionPageProfile = { page_profile_id: page.profile_id, version_uid: page.version_uid,
      page_number: page.page_number, algo_version: 'profile-1', status: 'ready', content_key: 'a'.repeat(64),
      annotation_count: 0, vector_line_count: 0, word_count: 1, has_text_layer: true,
      preview_available: true, thumbnail_available: true, width_pt: 400, height_pt: 300,
      raster_width_px: 800, raster_height_px: 600 };
    cache.setQueryData(['stage-view-profile', page.profile_id], profile);
  }
  const fragment = (id: string, page: StageSheetPassport): StageTextFragment => ({
    fragment_id: id, profile_id: page.profile_id, side: page.side, pair_id: 'stp_pair',
    content_key: 'a'.repeat(64), text: 'Кабель ВВГ', box_anchor: { x0: 10, top: 20, x1: 90, bottom: 30 },
  });
  return renderScreen(cache, createElement(StagePairViewer, { leftPage: left, rightPage: right, stale,
    evidence: { fragments: [fragment('f1', left), fragment('f2', right)], differences: [], hints: [],
      exclusions: [{ exclusion_id: 'e1', revision_id: 'r1', left_fragment_id: 'f1',
        right_fragment_id: 'f2', proof_kind: 'same' }] },
  }));
}

describe('stage profile viewer markup', () => {
  it('shows independent text search, synchronised view and exact masks on both profiles', () => {
    const html = screen(false);
    expect(html).toContain('Синхронный вид');
    expect(html).toContain('Найти текст на листе П');
    expect(html).toContain('Найти текст на листе Р');
    expect(html).toContain('1:1');
    expect(html).toContain('data-evidence="mask:f1"');
    expect(html).toContain('data-evidence="mask:f2"');
  });

  it('hides proof masks when the sheet map has an unsaved edit', () => {
    const html = screen(true);
    expect(html).not.toContain('data-evidence="mask:');
  });
});
