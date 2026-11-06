/**
 * `UI-PARITY-P0O` (contract 1.30.0): a finding's pages with their drawing sheet, as the original's «Лист» beside the
 * PDF page. The sheet comes only from the portal geometry; a page it names no sheet for stays a bare page number.
 */

import { describe, expect, it } from 'vitest';

import type { VersionSheetLabelList, VersionUid } from '@/shared/api';
import { sheetOfPage } from '@/entities/block';
import { pagesLabel } from '@/widgets/finding-list';

const LABELS: VersionSheetLabelList = {
  version_uid: 'ver_01M5B0000000000000000000V1' as VersionUid,
  status: 'produced',
  items: [
    { page_number: 3, page_label: 7, block_count: 4 },
    { page_number: 4, block_count: 2 },
    { page_number: 5, page_label: 8, block_count: 1 },
  ],
};

describe('the sheet of a finding page', () => {
  it('reads the sheet the portal names, and nothing for a page it names none for', () => {
    expect(sheetOfPage(LABELS, 3)).toBe(7);
    expect(sheetOfPage(LABELS, 4)).toBeUndefined();
    expect(sheetOfPage(LABELS, 9)).toBeUndefined();
    expect(sheetOfPage(undefined, 3)).toBeUndefined();
  });

  it('puts the sheet first when every page has one, and never passes a page off as a sheet', () => {
    const sheetOf = (page: number) => sheetOfPage(LABELS, page);
    expect(pagesLabel([3], sheetOf)).toBe('Лист 7 · стр. 3');
    expect(pagesLabel([3, 5], sheetOf)).toBe('Листы 7, 8 · стр. 3, 5');
    expect(pagesLabel([3, 4], sheetOf)).toBe('стр. 3, 4');
    expect(pagesLabel([3])).toBe('стр. 3');
  });
});
