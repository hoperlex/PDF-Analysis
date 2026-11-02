/**
 * The matcher against a real pdf.js page.
 *
 * `locate-quotation.test.ts` proves the logic on text items written by hand. The risk it
 * cannot cover is that pdf.js hands back something other than what was assumed -- how it
 * splits a line into items, what it does with doubled spaces, what the viewport transform
 * of a rotated page is, which units `width` is in. So this builds a small PDF in code
 * (`mini-pdf.ts`), reads it with pdf.js's own `getTextContent()` and `getViewport()`, and
 * runs the shipped functions over the result.
 *
 * It uses pdf.js's LEGACY build because that is the one pdf.js supports in Node ("Please use
 * the `legacy` build in Node.js environments", printed by the modern one before it hangs
 * waiting for a worker). The browser ships the modern build; the two share the text and
 * viewport code this test exercises, and the browser check in the task report is the one
 * that draws with the shipped build.
 */

import { fileURLToPath } from 'node:url';
import type * as PdfJsModule from 'pdfjs-dist';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';

import type { QuotationLocation, TextRun } from '@/features/open-evidence/model/locate-quotation';
import { locateQuotations } from '@/features/open-evidence/model/locate-quotation';
import { makeStage } from '@/features/open-evidence/model/view-state';

import { buildPdf, text } from './mini-pdf';

type PdfJs = typeof PdfJsModule;

const PAGE = [
  text(40, 780, 24, 'TITLE SHEET 1'),
  // Two blocks on one baseline with a gap: pdf.js reads them as items with a space between.
  text(40, 700, 12, 'Customer:'),
  text(130, 700, 12, 'OOO Asterus'),
  // Doubled and tripled spaces, which the text layer collapses.
  text(40, 680, 12, 'Delivery  term   is 30 days.'),
  text(40, 660, 12, 'Total: 100 rubles'),
  text(40, 640, 12, 'Total: 100 rubles'),
  // One line shown as three runs.
  text(40, 620, 12, 'split ', 'across ', 'runs'),
].join('\n');

const STANDARD_FONTS = `${fileURLToPath(new URL('../../../node_modules/pdfjs-dist/standard_fonts/', import.meta.url))}`;

let pdfjs: PdfJs;
let document_: Awaited<ReturnType<PdfJs['getDocument']>['promise']>;
let destroy: () => Promise<void>;

async function locate(
  pageNumber: number,
  quotes: readonly string[],
): Promise<{
  readonly locations: readonly QuotationLocation[];
  readonly size: { readonly width: number; readonly height: number };
  readonly items: readonly TextRun[];
}> {
  const page = await document_.getPage(pageNumber);
  const viewport = page.getViewport({ scale: 1 });
  const content = await page.getTextContent();
  const items: TextRun[] = [];
  for (const item of content.items) if ('str' in item) items.push(item);
  const size = { width: viewport.width, height: viewport.height };
  return {
    locations: locateQuotations(
      items,
      quotes.map((quote, index) => ({ ordinal: index + 1, quote })),
      viewport.transform,
    ),
    size,
    items,
  };
}

beforeAll(async () => {
  pdfjs = (await import('pdfjs-dist/legacy/build/pdf.mjs')) as unknown as PdfJs;
  const task = pdfjs.getDocument({
    data: buildPdf([
      { width: 595, height: 842, content: PAGE },
      { width: 595, height: 842, rotate: 90, content: PAGE },
      { width: 2980, height: 842, content: text(40, 780, 24, 'WIDE DRAWING SHEET') },
    ]),
    standardFontDataUrl: STANDARD_FONTS,
    useSystemFonts: false,
  });
  document_ = await task.promise;
  destroy = () => task.destroy();
}, 60_000);

afterAll(async () => {
  await destroy();
});

describe('quotations on a real page', () => {
  it('finds a quotation pdf.js split into several items, and boxes where it is', async () => {
    const { locations } = await locate(1, ['Customer: OOO Asterus']);
    const [located] = locations;
    expect(located?.status).toBe('found');
    const [occurrence] = located?.occurrences ?? [];
    expect(occurrence?.highlights).toHaveLength(2);
    // "OOO Asterus": starts at x = 130 and is 72.02 units wide; baseline at user y = 700 is
    // device y = 142; a 12-unit font reaches 0.92 em above and 0.24 em below it.
    const [first, second] = occurrence?.highlights ?? [];
    expect(first?.left).toBeCloseTo(40, 0);
    expect(first?.width).toBeCloseTo(55.34, 0);
    expect(second?.left).toBeCloseTo(130, 0);
    expect(second?.width).toBeCloseTo(72.02, 0);
    expect(second?.top).toBeCloseTo(142 - 0.92 * 12, 0);
    expect((second?.top ?? 0) + (second?.height ?? 0)).toBeCloseTo(142 + 0.24 * 12, 0);
  });

  it('keeps every highlight inside the page', async () => {
    const { locations, size } = await locate(1, ['Customer: OOO Asterus']);
    const occurrence = locations[0]?.occurrences[0];
    expect(occurrence?.highlights.length).toBeGreaterThan(0);
    for (const box of occurrence?.highlights ?? []) {
      expect(box.left).toBeGreaterThanOrEqual(0);
      expect(box.top).toBeGreaterThanOrEqual(0);
      expect(box.left + box.width).toBeLessThanOrEqual(size.width);
      expect(box.top + box.height).toBeLessThanOrEqual(size.height);
    }
  });

  it('finds a quotation whose whitespace the page does not share', async () => {
    const { locations } = await locate(1, [
      'Delivery term is 30 days.',
      'Delivery   term\tis  30 days.',
      'split across runs',
      'splitacrossruns',
    ]);
    expect(locations.map((entry) => entry.status)).toEqual(['found', 'found', 'found', 'found']);
  });

  it('finds both occurrences of a repeated quotation, one under the other', async () => {
    const { locations } = await locate(1, ['Total: 100 rubles']);
    const occurrences = locations[0]?.occurrences ?? [];
    expect(occurrences).toHaveLength(2);
    // Baselines 20 units apart in the content stream.
    const [upper, lower] = occurrences.map((occurrence) => occurrence.highlights[0]);
    expect((lower?.top ?? 0) - (upper?.top ?? 0)).toBeCloseTo(20, 0);
  });

  it('reports a quotation that is not on the page as not found', async () => {
    const { locations } = await locate(1, ['Executor: OOO Sotrudnik', 'TITLE SHEET 3']);
    expect(locations.map((entry) => entry.status)).toEqual(['not-found', 'not-found']);
  });

  it('puts the box where a page rotated a quarter turn shows the text', async () => {
    const upright = (await locate(1, ['OOO Asterus'])).locations[0]?.occurrences[0]?.highlights[0];
    const { locations, size } = await locate(2, ['OOO Asterus']);
    const turned = locations[0]?.occurrences[0]?.highlights[0];
    // /Rotate 90 swaps the page's width and height...
    expect(size).toEqual({ width: 842, height: 595 });
    // ...and the run, which now reads downward, swaps its box's sides: device x is user y.
    expect(turned?.width).toBeCloseTo(upright?.height ?? 0, 0);
    expect(turned?.height).toBeCloseTo(upright?.width ?? 0, 0);
    expect(turned?.top).toBeCloseTo(upright?.left ?? 0, 0);
    // Baseline at user y = 700; 0.24 em below it, still to the left of the baseline.
    expect(turned?.left).toBeCloseTo(700 - 0.24 * 12, 0);
  });
});

describe('a volume that mixes page sizes', () => {
  it('fits each page to the same pane on its own', async () => {
    const pane = { width: 900, height: 700 };
    const fitted: { width: number; height: number }[] = [];
    for (const number of [1, 3]) {
      const viewport = (await document_.getPage(number)).getViewport({ scale: 1 });
      const stage = makeStage({ width: viewport.width, height: viewport.height }, pane);
      fitted.push({ width: viewport.width * (stage?.fit ?? 0), height: viewport.height * (stage?.fit ?? 0) });
    }
    // An A4 page is not drawn at a fifth of the pane because a drawing sheet is five times as
    // wide: each fills the pane on the side that limits it (the height for A4, the width for
    // the sheet) less the inset, and nothing else in the document is consulted.
    expect(fitted[0]?.height).toBeCloseTo(700 - 32);
    expect(fitted[1]?.width).toBeCloseTo(900 - 32);
  });
});
