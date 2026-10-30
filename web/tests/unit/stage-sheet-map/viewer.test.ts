import { describe, expect, it } from 'vitest';

import type { VersionPageProfile } from '@/shared/api';
import { initialState } from '@/widgets/comparison-viewer';
import { profileGeometry, stageTileRequests, synchroniseView } from '@/widgets/stage-sheet-map/model/viewer';

function profile(width: number, height: number): VersionPageProfile {
  return { page_profile_id: 'cpr_page', version_uid: 'ver_document', page_number: 1,
    algo_version: 'profile-1', status: 'ready', content_key: 'a'.repeat(64),
    annotation_count: 0, vector_line_count: 0, word_count: 1, has_text_layer: true,
    preview_available: true, thumbnail_available: true, width_pt: width / 2,
    height_pt: height / 2, raster_width_px: width, raster_height_px: height };
}

describe('stage profile viewer geometry', () => {
  it('uses the stored raster and point size without a synthetic pair identity', () => {
    const geometry = profileGeometry(profile(1600, 1000));
    expect(geometry?.dpi).toBe(144);
    expect(geometry?.levels.at(-1)).toMatchObject({ columns: 1, rows: 1 });
    expect(profileGeometry(undefined)).toBeNull();
  });

  it('requests the whole-sheet underlay and the visible detail level', () => {
    const geometry = profileGeometry(profile(1600, 1000))!;
    const context = { raster: geometry.raster, dpi: geometry.dpi, differences: [], canOverlay: false, hasA: true, hasB: false };
    const state = { ...initialState(context), view: { zoom: 1, offsetX: 0, offsetY: 0 } };
    const requests = stageTileRequests(geometry, state);
    expect(requests[0]).toMatchObject({ level: geometry.levels.at(-1)!.level, column: 0, row: 0 });
    expect(requests.slice(1).every((request) => request.level === 0)).toBe(true);
  });

  it('synchronises relative view between different sheet formats', () => {
    const a = profileGeometry(profile(1600, 1000))!;
    const b = profileGeometry(profile(800, 1200))!;
    const state = (geometry: typeof a) => initialState({ raster: geometry.raster, dpi: geometry.dpi,
      differences: [], canOverlay: false, hasA: true, hasB: false });
    const source = { ...state(a), view: { zoom: 1, offsetX: -100, offsetY: -60 } };
    const target = synchroniseView(source, a, state(b), b);
    const center = (held: typeof source, geometry: typeof a) => [
      (held.viewport.width / 2 - held.view.offsetX) / (geometry.raster.widthPx * held.view.zoom),
      (held.viewport.height / 2 - held.view.offsetY) / (geometry.raster.heightPx * held.view.zoom),
    ];
    expect(center(target, b)[0]).toBeCloseTo(center(source, a)[0]!);
    expect(center(target, b)[1]).toBeCloseTo(center(source, a)[1]!);
  });
});
