/**
 * How sharp the page is drawn: the bitmap budget.
 *
 * Where the page sits and how large it looks is `view-state.test.ts`. This is only the limit on
 * the backing store, which is what stops a deep zoom on a dense screen from asking the browser
 * for a canvas it will refuse and answering with a blank page.
 */

import { describe, expect, it } from 'vitest';

import { MAX_CANVAS_PIXELS, bitmapScale } from '@/features/open-evidence/model/page-geometry';

describe('bitmapScale', () => {
  it('draws at the wanted scale while the bitmap is within the budget', () => {
    expect(bitmapScale(1.5, 595, 842)).toBe(1.5);
    expect(bitmapScale(2, 595, 842)).toBe(2);
  });

  it('reduces the scale just enough to keep the bitmap within the budget', () => {
    const scale = bitmapScale(20, 595, 842) as number;
    expect(scale).toBeLessThan(20);
    expect(595 * scale * (842 * scale)).toBeCloseTo(MAX_CANVAS_PIXELS, -3);
  });

  it('holds a wide drawing sheet to the same budget as an A4 page', () => {
    for (const [width, height] of [[595, 842], [2384, 1684], [5000, 3500]] as const) {
      const scale = bitmapScale(50, width, height) as number;
      expect(width * scale * (height * scale)).toBeLessThanOrEqual(MAX_CANVAS_PIXELS * 1.0001);
    }
  });

  it('waits for a real measurement instead of drawing at scale zero', () => {
    expect(bitmapScale(0, 595, 842)).toBeNull();
    expect(bitmapScale(-1, 595, 842)).toBeNull();
    expect(bitmapScale(Number.NaN, 595, 842)).toBeNull();
    expect(bitmapScale(1, 0, 842)).toBeNull();
    expect(bitmapScale(1, 595, Number.POSITIVE_INFINITY)).toBeNull();
  });
});
