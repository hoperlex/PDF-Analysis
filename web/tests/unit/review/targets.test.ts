/**
 * Where a finding points on a page: the authority order, and the refusals.
 *
 * The order is lines (the server's own geometry) then region (a normalised box the source
 * carries) then a search of the page text, then nothing. Each step is tested to prefer the one
 * before it, to give way when the one before it cannot answer, and to refuse what it cannot
 * trust: a rectangle off the page, a box that is not a box, a region that is the whole page.
 */

import { describe, expect, it } from 'vitest';

import type { BlockGeometry, VersionBlockIndex } from '@/shared/api';
import type { TextRun } from '@/features/open-evidence/model/locate-quotation';
import type { TextSnapshot, ViewerTarget } from '@/features/open-evidence/model/targets';
import {
  OUT_OF_BOUNDS_TOLERANCE,
  insidePage,
  lineRects,
  placeByGeometry,
  placeTargets,
  regionOf,
  resolutionSentence,
  resolutionsOf,
} from '@/features/open-evidence/model/targets';

const PAGE = { width: 595, height: 842 };

function block(overrides: Partial<BlockGeometry> & Pick<BlockGeometry, 'char_start' | 'char_end'>): BlockGeometry {
  return {
    bbox: { x0: 50, y0: 100, x1: 300, y1: 112 },
    bbox_origin: 'top_left',
    bbox_unit: 'pt',
    block_id: 'b_000001',
    block_ordinal: 0,
    page_number: 3,
    ...overrides,
  };
}

function index(blocks: BlockGeometry[], status: VersionBlockIndex['status'] = 'produced'): VersionBlockIndex {
  return {
    block_count: blocks.length,
    blocks,
    produced_by_run_id: status === 'produced' ? 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8B' : null,
    status,
    text_layer_sha256: status === 'produced' ? 'a'.repeat(64) : null,
    version_uid: 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
  };
}

/** Three lines of page 3: [1000, 1040), [1041, 1090), [1091, 1120). The `\n` belongs to none. */
const LINES = index([
  block({ block_ordinal: 0, char_start: 1000, char_end: 1040, bbox: { x0: 50, y0: 100, x1: 300, y1: 112 } }),
  block({ block_ordinal: 1, char_start: 1041, char_end: 1090, bbox: { x0: 50, y0: 114, x1: 520, y1: 126 } }),
  block({ block_ordinal: 2, char_start: 1091, char_end: 1120, bbox: { x0: 50, y0: 128, x1: 240, y1: 140 } }),
  block({ block_ordinal: 0, page_number: 4, char_start: 1121, char_end: 1160, bbox: { x0: 50, y0: 60, x1: 200, y1: 72 } }),
]);

const evidence = (overrides: { page_number?: number; char_start: number; char_end: number }) => ({
  page_number: 3,
  ...overrides,
});

describe('authority 1: the server’s line geometry', () => {
  it('returns the line a quotation sits inside, as a rectangle in points', () => {
    expect(lineRects(LINES, evidence({ char_start: 1005, char_end: 1030 }))).toEqual([
      { left: 50, top: 100, width: 250, height: 12 },
    ]);
  });

  it('frames the whole line for a quotation that starts or ends partway through it', () => {
    const rects = lineRects(LINES, evidence({ char_start: 1030, char_end: 1095 }));
    expect(rects).toEqual([
      { left: 50, top: 100, width: 250, height: 12 },
      { left: 50, top: 114, width: 470, height: 12 },
      { left: 50, top: 128, width: 190, height: 12 },
    ]);
  });

  it('treats the range as half-open: a range ending where a line starts does not include it', () => {
    expect(lineRects(LINES, evidence({ char_start: 1000, char_end: 1041 }))?.length).toBe(1);
    expect(lineRects(LINES, evidence({ char_start: 1040, char_end: 1041 }))).toBeNull();
    expect(lineRects(LINES, evidence({ char_start: 1090, char_end: 1091 }))).toBeNull();
  });

  it('takes only the declared page: the same range on another page is another page’s text', () => {
    expect(lineRects(LINES, evidence({ page_number: 4, char_start: 1121, char_end: 1130 }))).toEqual([
      { left: 50, top: 60, width: 150, height: 12 },
    ]);
    expect(lineRects(LINES, evidence({ page_number: 5, char_start: 1000, char_end: 1100 }))).toBeNull();
    expect(lineRects(LINES, evidence({ page_number: 4, char_start: 1000, char_end: 1100 }))).toBeNull();
  });

  it('orders the lines by their place on the page, whatever order the index lists them in', () => {
    const shuffled = index([...LINES.blocks].reverse());
    expect(lineRects(shuffled, evidence({ char_start: 1000, char_end: 1100 }))?.map((r) => r.top)).toEqual([100, 114, 128]);
  });

  it('answers null when the index cannot say anything', () => {
    expect(lineRects(null, evidence({ char_start: 1000, char_end: 1010 }))).toBeNull();
    expect(lineRects(undefined, evidence({ char_start: 1000, char_end: 1010 }))).toBeNull();
    // `not_produced` is absent geometry, not an empty page: nothing may be drawn from it.
    expect(lineRects(index([], 'not_produced'), evidence({ char_start: 1000, char_end: 1010 }))).toBeNull();
    expect(lineRects(index([], 'produced'), evidence({ char_start: 1000, char_end: 1010 }))).toBeNull();
  });

  it('answers null for an anchor with no extent', () => {
    expect(lineRects(LINES, evidence({ char_start: 1010, char_end: 1010 }))).toBeNull();
    expect(lineRects(LINES, evidence({ char_start: 1020, char_end: 1010 }))).toBeNull();
  });

  it('refuses the whole quotation when one of its lines has no real box', () => {
    const broken = (bbox: BlockGeometry['bbox']) =>
      index([
        block({ block_ordinal: 0, char_start: 1000, char_end: 1040 }),
        block({ block_ordinal: 1, char_start: 1041, char_end: 1090, bbox }),
      ]);
    const range = evidence({ char_start: 1000, char_end: 1090 });
    // A frame round one of two lines is a statement about the text, so it is not drawn.
    expect(lineRects(broken({ x0: 50, y0: 114, x1: 50, y1: 126 }), range)).toBeNull();
    expect(lineRects(broken({ x0: 50, y0: 126, x1: 520, y1: 114 }), range)).toBeNull();
    expect(lineRects(broken({ x0: Number.NaN, y0: 114, x1: 520, y1: 126 }), range)).toBeNull();
  });

  it('refuses geometry that does not say it is in points from the top left', () => {
    const odd = index([block({ char_start: 1000, char_end: 1040 })]);
    const first = odd.blocks[0] as BlockGeometry;
    const range = evidence({ char_start: 1000, char_end: 1040 });
    expect(lineRects(index([{ ...first, bbox_origin: 'bottom_left' as never }]), range)).toBeNull();
    expect(lineRects(index([{ ...first, bbox_unit: 'px' as never }]), range)).toBeNull();
  });
});

describe('rectangles must lie on the page', () => {
  const rect = (left: number, top: number, width: number, height: number) => ({ left, top, width, height });

  it('accepts rectangles on the page and an overhang within the tolerance', () => {
    expect(insidePage([rect(0, 0, 595, 842)], PAGE)).toBe(true);
    expect(insidePage([rect(-OUT_OF_BOUNDS_TOLERANCE, 10, 50, 10)], PAGE)).toBe(true);
    expect(insidePage([rect(550, 10, 45 + OUT_OF_BOUNDS_TOLERANCE, 10)], PAGE)).toBe(true);
  });

  it('refuses a rectangle past the page edge by more than the tolerance, instead of clipping it', () => {
    expect(insidePage([rect(-3, 10, 50, 10)], PAGE)).toBe(false);
    expect(insidePage([rect(560, 10, 40, 10)], PAGE)).toBe(false);
    expect(insidePage([rect(10, 840, 50, 10)], PAGE)).toBe(false);
    expect(insidePage([rect(10, -4, 50, 10)], PAGE)).toBe(false);
    // One bad rectangle spoils the set.
    expect(insidePage([rect(10, 10, 50, 10), rect(10, 900, 50, 10)], PAGE)).toBe(false);
  });

  it('refuses a rectangle that is not a box', () => {
    expect(insidePage([rect(10, 10, 0, 10)], PAGE)).toBe(false);
    expect(insidePage([rect(10, 10, -5, 10)], PAGE)).toBe(false);
    expect(insidePage([rect(Number.NaN, 10, 5, 10)], PAGE)).toBe(false);
  });
});

describe('authority 2: a normalised region', () => {
  it('accepts exactly four finite numbers in order inside the unit square', () => {
    expect(regionOf([0.1, 0.2, 0.6, 0.4])).toEqual([0.1, 0.2, 0.6, 0.4]);
    expect(regionOf([0, 0.5, 0.5, 1])).toEqual([0, 0.5, 0.5, 1]);
  });

  it.each([
    ['too few', [0.1, 0.2, 0.6]],
    ['too many', [0.1, 0.2, 0.6, 0.4, 0.9]],
    ['not numbers', ['0.1', 0.2, 0.6, 0.4]],
    ['NaN', [0.1, Number.NaN, 0.6, 0.4]],
    ['infinite', [0.1, 0.2, Number.POSITIVE_INFINITY, 0.4]],
    ['below zero', [-0.1, 0.2, 0.6, 0.4]],
    ['above one', [0.1, 0.2, 1.2, 0.4]],
    ['an empty width', [0.3, 0.2, 0.3, 0.4]],
    ['an inverted height', [0.1, 0.6, 0.5, 0.4]],
    ['null', null],
    ['an object', { x0: 0.1 }],
    ['undefined', undefined],
  ])('refuses %s', (_name, value) => {
    expect(regionOf(value)).toBeNull();
  });

  it('refuses the whole page: a native page carries it and it points at nothing', () => {
    expect(regionOf([0, 0, 1, 1])).toBeNull();
    expect(regionOf([0.0005, 0, 1, 0.9995])).toBeNull();
    // Nearly the whole page is still a region somebody drew.
    expect(regionOf([0.02, 0.02, 0.98, 0.98])).not.toBeNull();
    expect(regionOf([0, 0, 1, 0.5])).not.toBeNull();
  });
});

describe('resolution order', () => {
  const target = (overrides: Partial<ViewerTarget> = {}): ViewerTarget => ({ id: 't1', badge: '1', ...overrides });
  const lines = [{ left: 50, top: 100, width: 250, height: 12 }];

  it('prefers lines to a region to nothing', () => {
    const both = placeByGeometry(target({ rects: lines, region: [0.1, 0.1, 0.5, 0.5] }), PAGE);
    expect(both?.resolution).toEqual({ status: 'found', method: 'lines', occurrences: 1 });
    expect(both?.groups[0]?.hull).toEqual(lines[0]);

    const region = placeByGeometry(target({ region: [0.1, 0.2, 0.5, 0.4] }), PAGE);
    expect(region?.resolution).toEqual({ status: 'found', method: 'region', occurrences: 1 });
    expect(region?.groups[0]?.hull).toEqual({ left: 59.5, top: 168.4, width: 238, height: 168.4 });

    expect(placeByGeometry(target(), PAGE)).toBeNull();
    expect(placeByGeometry(target({ rects: [] }), PAGE)).toBeNull();
  });

  it('gives way to the region when the lines are off the page', () => {
    const off = [{ left: 580, top: 100, width: 60, height: 12 }];
    const placed = placeByGeometry(target({ rects: off, region: [0.1, 0.1, 0.5, 0.5] }), PAGE);
    expect(placed?.resolution.method).toBe('region');
    // And to nothing when there is no region: the text search takes over in `placeTargets`.
    expect(placeByGeometry(target({ rects: off }), PAGE)).toBeNull();
  });

  it('uses the page text only for a target the geometry could not place', async () => {
    let reads = 0;
    const text: TextSnapshot = { items: [item('Срок поставки 30 дней', 40, 700)], transform: FLIP };
    const readText = async () => {
      reads += 1;
      return text;
    };

    const placed = await placeTargets([target({ rects: lines, quote: 'Срок поставки' })], PAGE, readText);
    expect(placed[0]?.resolution.method).toBe('lines');
    expect(reads).toBe(0);

    const searched = await placeTargets(
      [target({ rects: lines, quote: 'Срок поставки' }), target({ id: 't2', badge: '2', quote: '30 дней' })],
      PAGE,
      readText,
    );
    expect(searched.map((p) => p.resolution.method)).toEqual(['lines', 'text']);
    expect(reads).toBe(1);
  });
});

/** A y-up page of the test height seen through the viewport at scale 1: `[1, 0, 0, -1, 0, h]`. */
const FLIP = [1, 0, 0, -1, 0, 842];

function item(str: string, x: number, y: number, size = 12): TextRun {
  return { str, transform: [size, 0, 0, size, x, y], width: str.length * size * 0.5, height: size };
}

describe('authority 3: the page text', () => {
  const target = (quote: string, id = 't1'): ViewerTarget => ({ id, badge: '1', quote });
  const readOf = (items: TextRun[]) => async (): Promise<TextSnapshot> => ({ items, transform: FLIP });

  it('frames every exact occurrence and counts them', async () => {
    const items = [item('Итого: 100 рублей', 40, 700), item('Итого: 100 рублей', 40, 660)];
    const [placed] = await placeTargets([target('Итого: 100 рублей')], PAGE, readOf(items));
    expect(placed?.resolution).toEqual({ status: 'found', method: 'text', occurrences: 2 });
    expect(placed?.groups).toHaveLength(2);
    // Page points, top-left origin: the lower line on the page has the larger top.
    const [first, second] = placed?.groups ?? [];
    expect((second?.hull.top ?? 0)).toBeGreaterThan(first?.hull.top ?? 0);
  });

  it('reports a quotation the text does not contain as not found, and draws nothing for it', async () => {
    const [placed] = await placeTargets([target('нет такой строки')], PAGE, readOf([item('Итого: 100 рублей', 40, 700)]));
    expect(placed?.resolution).toEqual({ status: 'not-found', method: null, occurrences: 0 });
    expect(placed?.groups).toEqual([]);
  });

  it('says a page with no characters at all has no text layer, rather than that nothing matched', async () => {
    const [placed] = await placeTargets([target('любая строка')], PAGE, readOf([]));
    expect(placed?.resolution).toEqual({ status: 'no-text-layer', method: null, occurrences: 0 });
  });

  it('places nothing for a target with neither geometry nor a quotation', async () => {
    let reads = 0;
    const [placed] = await placeTargets([{ id: 't1', badge: '1' }], PAGE, async () => {
      reads += 1;
      return { items: [], transform: FLIP };
    });
    expect(placed?.resolution.status).toBe('not-found');
    expect(reads).toBe(0);
  });

  it('keeps several quotations of one page apart', async () => {
    const items = [item('первая строка', 40, 700), item('вторая строка', 40, 650)];
    const placed = await placeTargets([target('вторая строка', 'a'), target('первая строка', 'b'), target('третья', 'c')], PAGE, readOf(items));
    expect(placed.map((p) => [p.target.id, p.resolution.status])).toEqual([
      ['a', 'found'],
      ['b', 'found'],
      ['c', 'not-found'],
    ]);
    expect([...resolutionsOf(placed).keys()]).toEqual(['a', 'b', 'c']);
  });
});

describe('the sentence a card says about its frame', () => {
  it('has one for every outcome, and none claims more than the authority that placed it', () => {
    expect(resolutionSentence({ status: 'found', method: 'lines', occurrences: 1 })).toBe('Отмечено по разметке строк.');
    expect(resolutionSentence({ status: 'found', method: 'region', occurrences: 1 })).toBe('Отмечено по области, которую передал источник.');
    expect(resolutionSentence({ status: 'found', method: 'text', occurrences: 1 })).toBe('Найдено в тексте страницы.');
    expect(resolutionSentence({ status: 'found', method: 'text', occurrences: 3 })).toBe('Найдено в тексте страницы, совпадений: 3.');
    expect(resolutionSentence({ status: 'not-found', method: null, occurrences: 0 })).toBe('На странице фрагмент не найден — сверяйте по цитате.');
    expect(resolutionSentence({ status: 'no-text-layer', method: null, occurrences: 0 })).toContain('нет текстового слоя');
  });
});
