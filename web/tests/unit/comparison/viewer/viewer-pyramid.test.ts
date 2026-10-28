/**
 * The viewer's pyramid is the server's (`comparison/tiles/grid.py`, `comparison/profile/child/geometry.py`):
 * a level, a column or a row the server does not have is `404`, so the arithmetic is held against figures the server's
 * own tests print (`CMP-VIEWER-01`).
 */

import { describe, expect, it } from 'vitest';

import {
  MAX_ZOOM, boxToSheet, fitView, fitZoom, focusBox, levelForZoom, placeTile, pyramidLevels, rasterFromCanvas,
  visibleTiles, zoomAt,
} from '@/widgets/comparison-viewer/model/pyramid';

import { A1 } from './viewer-fixtures';

describe('the pyramid', () => {
  it('has the levels, columns and rows of the A1 plan the server tests build', () => {
    expect(rasterFromCanvas(2383.94, 1683.78, 200)).toEqual(A1);
    const levels = pyramidLevels(A1);
    expect(levels.map((l) => [l.widthPx, l.heightPx, l.columns, l.rows])).toEqual([
      [6623, 4678, 13, 10], [3312, 2339, 7, 5], [1656, 1170, 4, 3], [828, 585, 2, 2], [414, 293, 1, 1],
    ]);
  });

  it('has the five levels of a 2A0 sheet at 113 dpi and stops at the first level that fits one tile', () => {
    const levels = pyramidLevels({ widthPx: 7483, heightPx: 5290 });
    expect(levels).toHaveLength(5);
    expect(levels[4]).toMatchObject({ widthPx: 468, heightPx: 331, columns: 1, rows: 1 });
    expect(pyramidLevels({ widthPx: 400, heightPx: 300 })).toHaveLength(1);
    expect(pyramidLevels({ widthPx: 512, heightPx: 512 })).toHaveLength(1);
    expect(pyramidLevels({ widthPx: 513, heightPx: 10 })).toHaveLength(2);
  });

  it('places the partial tile at the corner with its real size', () => {
    const levels = pyramidLevels(A1);
    expect(placeTile(levels[0]!, 12, 9)).toEqual({ level: 0, column: 12, row: 9, left: 6144, top: 4608, width: 479, height: 70 });
    expect(placeTile(levels[2]!, 3, 2)).toEqual({ level: 2, column: 3, row: 2, left: 6144, top: 4096, width: 120 * 4, height: 146 * 4 });
  });
});

describe('the view', () => {
  const viewport = { width: 1000, height: 600 };

  it('fits the whole sheet, centred', () => {
    const view = fitView(A1, viewport);
    expect(view.zoom).toBeCloseTo(Math.min(1000 / 6623, 600 / 4678), 9);
    expect(view.offsetX + (A1.widthPx * view.zoom) / 2).toBeCloseTo(500, 6);
    expect(view.offsetY + (A1.heightPx * view.zoom) / 2).toBeCloseTo(300, 6);
    expect(fitZoom(A1, { width: 0, height: 0 })).toBe(1);
  });

  it('chooses the coarsest level that is not blurrier than the screen', () => {
    const levels = pyramidLevels(A1);
    expect(levelForZoom(1, levels)).toBe(0);
    expect(levelForZoom(2, levels)).toBe(0);
    expect(levelForZoom(0.5, levels)).toBe(1);
    expect(levelForZoom(0.26, levels)).toBe(1);
    expect(levelForZoom(0.25, levels)).toBe(2);
    expect(levelForZoom(0.001, levels)).toBe(4);
  });

  it('asks for the tiles the window touches and no others', () => {
    const levels = pyramidLevels(A1);
    const atTopLeft = visibleTiles(levels, 0, { zoom: 1, offsetX: 0, offsetY: 0 }, viewport);
    expect(atTopLeft.map((t) => [t.column, t.row])).toEqual([[0, 0], [1, 0], [0, 1], [1, 1]]);
    const scrolled = visibleTiles(levels, 0, { zoom: 1, offsetX: -3000, offsetY: -2000 }, viewport);
    expect(scrolled.map((t) => t.column)).toEqual([5, 6, 7, 5, 6, 7, 5, 6, 7]);
    expect([Math.min(...scrolled.map((t) => t.row)), Math.max(...scrolled.map((t) => t.row))]).toEqual([3, 5]);
    // a window past the sheet touches nothing
    expect(visibleTiles(levels, 0, { zoom: 1, offsetX: -90000, offsetY: 0 }, viewport)).toEqual([]);
    expect(visibleTiles(levels, 9, { zoom: 1, offsetX: 0, offsetY: 0 }, viewport)).toEqual([]);
    // the whole sheet at the top level is one tile
    expect(visibleTiles(levels, 4, fitView(A1, viewport), viewport)).toHaveLength(1);
  });

  it('zooms about a point and keeps the sheet point under it where it was', () => {
    const view = fitView(A1, viewport);
    const anchor = { x: 321, y: 123 };
    const sheetPoint = { x: (anchor.x - view.offsetX) / view.zoom, y: (anchor.y - view.offsetY) / view.zoom };
    const zoomed = zoomAt(view, 3, anchor, A1, viewport);
    expect(zoomed.zoom).toBeCloseTo(view.zoom * 3, 9);
    expect((anchor.x - zoomed.offsetX) / zoomed.zoom).toBeCloseTo(sheetPoint.x, 6);
    expect((anchor.y - zoomed.offsetY) / zoomed.zoom).toBeCloseTo(sheetPoint.y, 6);
  });

  it('never zooms in past 400 % nor out past half the fit', () => {
    const view = fitView(A1, viewport);
    expect(zoomAt(view, 1e6, { x: 0, y: 0 }, A1, viewport).zoom).toBe(MAX_ZOOM);
    expect(zoomAt(view, 1e-6, { x: 0, y: 0 }, A1, viewport).zoom).toBeCloseTo(view.zoom / 2, 9);
  });

  it('shows a box centred, close, and no closer than the limit', () => {
    const box = boxToSheet({ x: 1000, y: 700, width: 80, height: 12 }, 200);
    expect(box).toEqual({ left: 2777.7777777777778, top: 1944.4444444444443, width: 222.22222222222223, height: 33.33333333333333 });
    const view = focusBox(box, A1, viewport);
    expect(view.zoom).toBeGreaterThan(fitZoom(A1, viewport));
    expect(view.zoom).toBeLessThanOrEqual(MAX_ZOOM);
    expect(view.offsetX + (box.left + box.width / 2) * view.zoom).toBeCloseTo(500, 6);
    expect(view.offsetY + (box.top + box.height / 2) * view.zoom).toBeCloseTo(300, 6);
    const huge = focusBox({ left: 0, top: 0, width: A1.widthPx, height: A1.heightPx }, A1, viewport);
    expect(huge.zoom).toBeCloseTo(fitZoom(A1, viewport), 9);
  });
});
