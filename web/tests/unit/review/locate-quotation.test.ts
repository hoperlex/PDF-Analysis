/**
 * Where a quotation sits on a page: the matcher and the geometry, on hand-written text items.
 *
 * The matcher exists because the server's extractor and pdf.js do not read a page the same
 * way: they split the same line into different items and space the words differently. The
 * cases here are the ways that goes wrong, plus the two answers that must stay distinct from
 * "found": the text is not on the page, and the page has no text at all. The same functions
 * run against a real pdf.js page in `locate-quotation-pdf.test.ts`.
 *
 * Items are written as `run(str)`: a width proportional to the character count (one unit per
 * character) so character offsets and rectangle fractions can be checked by arithmetic.
 */

import { describe, expect, it } from 'vitest';

import type { TextRun } from '@/features/open-evidence/model/locate-quotation';
import {
  CUT_BLEED,
  foldPageText,
  foldQuotation,
  locateQuotation,
  locateQuotations,
  spanRectangle,
  unionRectangle,
} from '@/features/open-evidence/model/locate-quotation';

/** A run on a baseline at user-space `(x, y)`, 10 units tall, one unit of advance per UTF-16 unit. */
function run(str: string, x = 0, y = 0): TextRun {
  return { str, transform: [10, 0, 0, 10, x, y], width: str.length, height: 10 };
}

/** pdf.js's viewport for an unrotated page `height` tall at scale 1: flips the y axis. */
const upright = (height: number) => [1, 0, 0, -1, 0, height] as const;

function spansOf(items: readonly TextRun[], quote: string) {
  return locateQuotation(foldPageText(items), quote).map((match) => match.spans);
}

describe('a quotation is found across the ways two extractors split a line', () => {
  it('finds a quotation inside one item and reports its character offsets', () => {
    expect(spansOf([run('Срок поставки составляет 30 дней.')], 'составляет 30')).toEqual([
      [{ item: 0, start: 14, end: 27 }],
    ]);
  });

  it('finds a quotation that spans several items, with the partial first and last item cut', () => {
    const items = [run('Заказчик:'), run(' '), run('ООО Астерус'), run(', г. Москва')];
    // The space-only item between the two has no character of its own to cover, so it is not
    // a span: the highlight is two boxes with the gap the space occupies between them.
    expect(spansOf(items, 'Заказчик: ООО Астерус')).toEqual([
      [
        { item: 0, start: 0, end: 9 },
        { item: 2, start: 0, end: 11 },
      ],
    ]);
    // Ends inside the last item it touches, not at its end.
    expect(spansOf(items, 'Астерус, г.')).toEqual([
      [
        { item: 2, start: 4, end: 11 },
        { item: 3, start: 0, end: 4 },
      ],
    ]);
  });

  it('does not care how much whitespace either side has, or whether an item boundary has any', () => {
    const items = [run('Срок  поставки'), run('составляет'), run('   30   дней.')];
    expect(spansOf(items, 'Срок поставки составляет 30 дней.')).toHaveLength(1);
    // And the other way round: the quotation carries the odd spacing, the page does not.
    expect(spansOf([run('Срок поставки составляет 30 дней.')], 'Срок \u00A0поставки\n составляет\t30 дней.')).toHaveLength(1);
    expect(foldQuotation(' a \u00A0b\n\tc ')).toBe('abc');
  });

  it('ignores invisible separators an extractor may or may not have emitted', () => {
    expect(spansOf([run('до\u00ADговор'), run('\u200Bна\uFEFF поставку')], 'договор на поставку')).toHaveLength(1);
  });

  it('meets ligatures and compatibility forms on both sides, as pdf.js itself normalises', () => {
    expect(spansOf([run('o\uFB03ce №5')], 'office No5')).toHaveLength(1);
    expect(spansOf([run('office No5')], 'o\uFB03ce №5')).toHaveLength(1);
  });

  it('meets a decomposed letter and its precomposed form', () => {
    // "й" as и + COMBINING BREVE, against the single code point.
    expect(spansOf([run('Крайний срок')], 'Краи\u0306ний срок')).toHaveLength(1);
    expect(spansOf([run('Краи\u0306ний срок')], 'Крайний срок')).toHaveLength(1);
  });

  it('keeps case, digits and punctuation exact: only whitespace is forgiven', () => {
    const page = [run('Срок поставки составляет 30 дней.')];
    expect(spansOf(page, 'срок поставки')).toEqual([]);
    expect(spansOf(page, 'составляет 31 дней')).toEqual([]);
    expect(spansOf(page, 'составляет 30 дней')).toHaveLength(1);
    expect(spansOf(page, 'составляет 30 дней!')).toEqual([]);
  });
});

describe('a quotation that is not there is reported as not there', () => {
  it('returns no match for text absent from the page, with no nearest-line guess', () => {
    const page = [run('Срок поставки составляет 30 дней.')];
    expect(spansOf(page, 'Срок оплаты составляет 30 дней.')).toEqual([]);
  });

  it('returns no match for a quotation with no characters of its own', () => {
    expect(spansOf([run('любой текст')], '')).toEqual([]);
    expect(spansOf([run('любой текст')], ' \u00A0\n\t ')).toEqual([]);
  });

  it('does not match across the page when only the tail of the quotation is present', () => {
    expect(spansOf([run('Срок поставки')], 'Срок поставки составляет')).toEqual([]);
  });
});

describe('a quotation that occurs twice is found twice', () => {
  it('reports every occurrence, in text-layer order, without overlap', () => {
    const items = [run('Итого: 100 руб.'), run('Итого: 100 руб.'), run('Итого: 200 руб.')];
    expect(spansOf(items, 'Итого: 100 руб.')).toEqual([
      [{ item: 0, start: 0, end: 15 }],
      [{ item: 1, start: 0, end: 15 }],
    ]);
  });

  it('finds two occurrences inside one item', () => {
    expect(spansOf([run('да, да')], 'да')).toEqual([
      [{ item: 0, start: 0, end: 2 }],
      [{ item: 0, start: 4, end: 6 }],
    ]);
  });

  it('does not count overlapping readings of a self-overlapping quotation', () => {
    expect(spansOf([run('aaaa')], 'aa')).toHaveLength(2);
    expect(spansOf([run('aaa')], 'aa')).toHaveLength(1);
  });
});

describe('rectangles follow the page transform', () => {
  const page = upright(100);

  it('puts an upright run on its baseline, with room for ascenders and descenders', () => {
    // Baseline at user y = 80 is device y = 20; the run is 12 units wide at x = 5.
    const rect = spanRectangle(run('abcdefghijkl', 5, 80), 0, 12, page);
    expect(rect).not.toBeNull();
    expect(rect?.left).toBeCloseTo(5);
    expect(rect?.width).toBeCloseTo(12);
    // 10-unit font: 0.92 em above the baseline, 0.24 em below it.
    expect(rect?.top).toBeCloseTo(20 - 9.2);
    expect((rect?.top ?? 0) + (rect?.height ?? 0)).toBeCloseTo(20 + 2.4);
  });

  it('cuts a partly covered run at the character fraction of its advance, with a bleed on each cut side', () => {
    const rect = spanRectangle(run('abcdefghij', 0, 80), 2, 5, page);
    // The bleed is real (a box cut at the exact fraction clipped the last glyph of a quotation)
    // and less than a character (a whole neighbouring glyph would be a claim nobody made).
    expect(CUT_BLEED).toBeGreaterThan(0);
    expect(CUT_BLEED).toBeLessThan(1);
    expect(rect?.left).toBeLessThan(2);
    expect((rect?.left ?? 0) + (rect?.width ?? 0)).toBeGreaterThan(5);
    // Characters 2..5 of ten, one unit each, and `CUT_BLEED` of a character on both cut sides.
    expect(rect?.left).toBeCloseTo(2 - CUT_BLEED);
    expect(rect?.width).toBeCloseTo(3 + 2 * CUT_BLEED);
  });

  it('bleeds only the side that is cut, and never past the item', () => {
    const fromStart = spanRectangle(run('abcdefghij', 0, 80), 0, 5, page);
    expect(fromStart?.left).toBeCloseTo(0);
    expect(fromStart?.width).toBeCloseTo(5 + CUT_BLEED);
    const toEnd = spanRectangle(run('abcdefghij', 0, 80), 6, 10, page);
    expect(toEnd?.left).toBeCloseTo(6 - CUT_BLEED);
    expect(toEnd?.width).toBeCloseTo(4 + CUT_BLEED);
    // Cut one character in from either end: the bleed would cross the item's own edge.
    const nearStart = spanRectangle(run('abcdefghij', 0, 80), 1, 9, page);
    expect(nearStart?.left).toBeCloseTo(1 - CUT_BLEED);
    expect(spanRectangle(run('abcdefghij', 0, 80), 0, 10, page)?.width).toBeCloseTo(10);
  });

  it('scales with the viewport', () => {
    const doubled = [2, 0, 0, -2, 0, 200] as const;
    const rect = spanRectangle(run('abcdefghij', 5, 80), 0, 10, doubled);
    expect(rect?.left).toBeCloseTo(10);
    expect(rect?.width).toBeCloseTo(20);
    expect(rect?.top).toBeCloseTo(2 * (20 - 9.2));
  });

  it('boxes a page rotated a quarter turn by its four corners', () => {
    // pdf.js's viewport for /Rotate 90 on a 100 x 50 page: device x is user y, device y is user x.
    const rotated = [0, 1, 1, 0, 0, 0] as const;
    const rect = spanRectangle(run('abcdefghij', 5, 30), 0, 10, rotated);
    // The run now reads downward: 10 tall in device y, one font-height wide in device x.
    expect(rect?.top).toBeCloseTo(5);
    expect(rect?.height).toBeCloseTo(10);
    expect(rect?.left).toBeCloseTo(30 - 2.4);
    expect(rect?.width).toBeCloseTo(9.2 + 2.4);
  });

  it('declines an item with no extent instead of inventing one', () => {
    expect(spanRectangle(run('', 0, 0), 0, 0, page)).toBeNull();
    expect(spanRectangle({ ...run('abc'), width: 0 }, 0, 3, page)).toBeNull();
    expect(spanRectangle(run('abc'), 2, 2, page)).toBeNull();
    expect(spanRectangle({ ...run('abc'), transform: [0, 0, 0, 0, 0, 0] }, 0, 3, page)).toBeNull();
  });

  it('joins rectangles into the smallest box that holds them', () => {
    const hull = unionRectangle([
      { left: 10, top: 10, width: 5, height: 5 },
      { left: 30, top: 20, width: 5, height: 5 },
    ]);
    expect(hull).toEqual({ left: 10, top: 10, width: 25, height: 15 });
    expect(unionRectangle([])).toBeNull();
  });
});

describe('a whole page, located', () => {
  const items = [
    run('Заказчик:', 10, 80),
    run(' ', 55, 80),
    run('ООО Астерус', 60, 80),
    run('Итого: 100 руб.', 10, 60),
    run('Итого: 100 руб.', 10, 40),
  ];
  const view = upright(100);

  it('gives a highlight per covered run of one occurrence', () => {
    const [located] = locateQuotations(items, [{ ordinal: 1, quote: 'Заказчик: ООО Астерус' }], view);
    expect(located?.status).toBe('found');
    expect(located?.occurrences).toHaveLength(1);
    const occurrence = located?.occurrences[0];
    expect(occurrence?.highlights).toHaveLength(2);
  });

  it('reports each occurrence of a repeated quotation on its own', () => {
    const [located] = locateQuotations(items, [{ ordinal: 2, quote: 'Итого: 100 руб.' }], view);
    expect(located?.status).toBe('found');
    expect(located?.occurrences).toHaveLength(2);
    const tops = located?.occurrences.map((occurrence) => occurrence.highlights[0]?.top ?? 0) ?? [];
    expect(tops[0]).toBeLessThan(tops[1] ?? 0);
  });

  it('says not-found for text that is not on the page and keeps the others', () => {
    const located = locateQuotations(
      items,
      [
        { ordinal: 1, quote: 'Заказчик: ООО Астерус' },
        { ordinal: 2, quote: 'Исполнитель: ООО Сотрудник' },
      ],
      view,
    );
    expect(located.map((entry) => [entry.ordinal, entry.status])).toEqual([
      [1, 'found'],
      [2, 'not-found'],
    ]);
    expect(located[1]?.occurrences).toEqual([]);
  });

  it('says no-text-layer for a page with no characters, which is what a scan looks like', () => {
    const located = locateQuotations([], [{ ordinal: 1, quote: 'что угодно' }], view);
    expect(located).toEqual([{ ordinal: 1, status: 'no-text-layer', occurrences: [] }]);
    // Whitespace-only items are no text layer either.
    expect(
      locateQuotations([run(' '), run('\u00A0')], [{ ordinal: 1, quote: 'x' }], view)[0]?.status,
    ).toBe('no-text-layer');
  });
});
