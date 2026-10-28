/**
 * A sheet pair as `getComparisonSheetPair` answers it, for the viewer's tests and the contrast census
 * (`CMP-VIEWER-01`). The numbers are an A1 sheet at 200 dpi (6623 x 4678 px), the size the server's tests use.
 */

import type { ComparisonSheetPair } from '@/shared/api';

export const PAIR_ID = 'ctp_01ARZ3NDEKTSV4RRFFQ69G5FAV';
export const TRANSITION_ID = 'ctn_01ARZ3NDEKTSV4RRFFQ69G5FAV';
export const A1 = { widthPx: 6623, heightPx: 4678 } as const;

export function comparedPair(overrides: Partial<ComparisonSheetPair> = {}): ComparisonSheetPair {
  return {
    sheet_pair_id: PAIR_ID,
    transition_id: TRANSITION_ID,
    state: 'done',
    status: 'different',
    result_id: 'csp_01ARZ3NDEKTSV4RRFFQ69G5FAV',
    page_a: {
      page: { version_uid: 'ver_01ARZ3NDEKTSV4RRFFQ69G5FAV', page_number: 5, page_profile_id: 'cpr_01ARZ3NDEKTSV4RRFFQ69G5FAV' },
      sheet_number: '5',
      title: 'План освещения. Корпус 1, этаж 1',
    },
    page_b: {
      page: { version_uid: 'ver_01ARZ3NDEKTSV4RRFFQ69G5FAW', page_number: 5, page_profile_id: 'cpr_01ARZ3NDEKTSV4RRFFQ69G5FAW' },
      sheet_number: '5',
      title: 'План освещения. Корпус 1, этаж 1',
    },
    confidence: 'high',
    canvas: { width_pt: 2383.94, height_pt: 1683.78 },
    channels: {
      geometry: { state: 'checked', diffs: 4 },
      color: { state: 'checked', diffs: 1 },
      text: { state: 'checked', diffs: 2 },
      text_coverage: { state: 'unchecked', reason: 'нет текстового слоя: надписи сравнены только графически' },
      zones: { state: 'checked', diffs: 1 },
      annotations: { state: 'not_applicable' },
      warnings: { state: 'checked', diffs: 1 },
      spec_positions: { state: 'not_applicable' },
    },
    reasons: ['NO_TEXT_LAYER'],
    differences: [
      { region_class: 'text', layer: 'main', box: { x: 100, y: 120, width: 80, height: 12 }, before_text: 'Щит ЩО-1', after_text: 'Щит ЩО-2' },
      { region_class: 'graphic_added', layer: 'main', box: { x: 400, y: 500, width: 30, height: 30 } },
      { region_class: 'color_change', layer: 'color_change', box: { x: 900, y: 700, width: 60, height: 20 } },
      { region_class: 'text_moved', layer: 'moved', box: { x: 300, y: 300, width: 50, height: 10 }, before_text: 'Прим.', after_text: 'Прим.' },
      { region_class: 'line_style', layer: 'line_style', box: { x: 1200, y: 900, width: 200, height: 4 } },
      { region_class: 'something_new', layer: 'main', box: { x: 10, y: 10, width: 5, height: 5 } },
    ],
    text_changes: [
      { kind: 'replaced', before: 'Кабель ВВГнг 3x2,5 длиной 120 м', after: 'Кабель ВВГнг 3x4 длиной 150 м',
        numbers: [{ before: '120', after: '150' }, { before: '2,5', after: '4' }], box: { x: 100, y: 120, width: 80, height: 12 } },
      { kind: 'added', after: 'Установить датчик движения' },
    ],
    service_notes: [
      { kind: 'warning', change: 'removed', zone: 'stamp', before: 'Не для строительства' },
      { kind: 'stamp', change: 'changed', zone: 'stamp', field: 'revision', before: '0', after: '1' },
    ],
    how_compared: {
      algo_version: 'vc1.13', dpi: 200, tolerance_pt: 0.5, transform: [1, 0, 0, 1, -3.7, 2.1],
      within_tolerance_count: 12, noise_count: 340, separated_objects: 3, aligned_blocks: 2,
    },
    ...overrides,
  };
}

export function addedPair(): ComparisonSheetPair {
  const compared = comparedPair();
  return {
    sheet_pair_id: PAIR_ID,
    transition_id: TRANSITION_ID,
    state: 'done',
    status: 'added',
    page_b: compared.page_b as NonNullable<ComparisonSheetPair['page_b']>,
  };
}
