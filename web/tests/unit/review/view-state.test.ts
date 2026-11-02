/**
 * Where the page sits in its viewport: fit, zoom around a point, clamp, focus on a rectangle.
 *
 * These are the properties a reader feels and nothing else checks: the point under the cursor
 * stays under the cursor, the page cannot be thrown out of reach, a small target fills about half
 * the pane and not all of it, and a page that already fits stays whole. All pure, all numbers.
 */

import { describe, expect, it } from 'vitest';

import type { Rect } from '@/features/open-evidence/model/locate-quotation';
import type { Stage, View } from '@/features/open-evidence/model/view-state';
import {
  FIT_INSET,
  FOCUS_PADDING,
  FOCUS_SHARE,
  MAX_FOCUS_ZOOM,
  MAX_PIXELS_PER_POINT,
  MAX_ZOOM,
  PAN_STEP,
  clampView,
  contentSize,
  doubleClickView,
  fitView,
  focusView,
  grow,
  keyView,
  makeStage,
  maxZoom,
  openingView,
  panBy,
  pinchView,
  stepZoom,
  toScreen,
  viewportCentre,
  wheelFactor,
  zoomAt,
  zoomPercent,
} from '@/features/open-evidence/model/view-state';

const A4 = { width: 595, height: 842 };
const SHEET = { width: 2384, height: 1684 };
const PANE = { width: 900, height: 700 };

function stage(page = A4, viewport = PANE): Stage {
  const made = makeStage(page, viewport);
  if (made === null) throw new Error('no stage');
  return made;
}

/** The page point under a viewport pixel. */
function pageAt(view: View, at: Stage, x: number, y: number) {
  const scale = at.fit * view.zoom;
  return { x: (x - view.x) / scale, y: (y - view.y) / scale };
}

describe('the stage', () => {
  it('fits the whole page inside the viewport with the inset around it', () => {
    const at = stage();
    // A4 is the tall side in a 900x700 pane: the height decides.
    expect(at.fit).toBeCloseTo((700 - 2 * FIT_INSET) / 842);
    const size = contentSize(at, 1);
    expect(size.height).toBeCloseTo(700 - 2 * FIT_INSET);
    expect(size.width).toBeLessThan(900 - 2 * FIT_INSET);
  });

  it('fits a wide drawing sheet by its width, on its own, whatever else is in the volume', () => {
    const at = stage(SHEET);
    expect(contentSize(at, 1).width).toBeCloseTo(900 - 2 * FIT_INSET);
    expect(contentSize(at, 1).height).toBeLessThan(700 - 2 * FIT_INSET);
  });

  it('waits for a real measurement', () => {
    expect(makeStage(A4, { width: 0, height: 700 })).toBeNull();
    expect(makeStage(A4, { width: 900, height: Number.NaN })).toBeNull();
    expect(makeStage({ width: 0, height: 842 }, PANE)).toBeNull();
    expect(makeStage({ width: Number.POSITIVE_INFINITY, height: 842 }, PANE)).toBeNull();
  });

  it('opens the whole page centred', () => {
    const at = stage();
    const view = fitView(at);
    expect(view.zoom).toBe(1);
    const size = contentSize(at, 1);
    expect(view.x).toBeCloseTo((900 - size.width) / 2);
    expect(view.y).toBeCloseTo((700 - size.height) / 2);
  });

  it('never allows more zoom than the pixel cap or the relative cap', () => {
    const small = stage({ width: 100, height: 100 }, { width: 900, height: 900 });
    expect(maxZoom(small) * small.fit).toBeLessThanOrEqual(MAX_PIXELS_PER_POINT + 1e-9);
    expect(maxZoom(stage())).toBeLessThanOrEqual(MAX_ZOOM);
    expect(maxZoom(small)).toBeGreaterThanOrEqual(1);
  });
});

describe('zooming around a point', () => {
  it('keeps the page point under the cursor where it was', () => {
    const at = stage();
    const start: View = { zoom: 2, x: -120, y: -300 };
    for (const [x, y] of [[450, 350], [200, 120], [700, 600]] as const) {
      const before = pageAt(start, at, x, y);
      const next = zoomAt(start, 3.5, { x, y }, at);
      expect(next.zoom).toBeCloseTo(3.5);
      const after = pageAt(next, at, x, y);
      expect(after.x).toBeCloseTo(before.x, 6);
      expect(after.y).toBeCloseTo(before.y, 6);
    }
  });

  it('never goes below the whole page or above the cap', () => {
    const at = stage();
    expect(zoomAt(fitView(at), 0.2, viewportCentre(at), at).zoom).toBe(1);
    expect(zoomAt(fitView(at), 1e9, viewportCentre(at), at).zoom).toBe(maxZoom(at));
    expect(zoomAt(fitView(at), Number.NaN, viewportCentre(at), at).zoom).toBe(1);
  });

  it('steps in and out by a constant factor and returns', () => {
    const at = stage();
    const centre = viewportCentre(at);
    const there = stepZoom(fitView(at), 1, centre, at);
    expect(there.zoom).toBeCloseTo(1.25);
    expect(stepZoom(there, -1, centre, at).zoom).toBeCloseTo(1);
  });

  it('turns a wheel notch into a factor that reverses and stays bounded', () => {
    expect(wheelFactor(0, 0)).toBe(1);
    expect(wheelFactor(-100, 0)).toBeGreaterThan(1);
    expect(wheelFactor(100, 0)).toBeLessThan(1);
    expect(wheelFactor(-100, 0) * wheelFactor(100, 0)).toBeCloseTo(1);
    // A line-mode wheel and a runaway delta are bounded.
    expect(wheelFactor(-3, 1)).toBeGreaterThan(1);
    expect(wheelFactor(-1e9, 0)).toBeCloseTo(Math.exp(120 * 0.0025));
    expect(wheelFactor(1e9, 0)).toBeCloseTo(Math.exp(-120 * 0.0025));
  });

  it('shows the zoom as a percentage of the whole-page fit', () => {
    expect(zoomPercent({ zoom: 1, x: 0, y: 0 })).toBe(100);
    expect(zoomPercent({ zoom: 1.6, x: 0, y: 0 })).toBe(160);
  });
});

describe('the page cannot be thrown out of reach', () => {
  it('holds a page smaller than the viewport in the middle', () => {
    const at = stage();
    const view = clampView({ zoom: 1, x: 400, y: -50 }, at);
    expect(view).toEqual(fitView(at));
  });

  it('lets a zoomed page be dragged until its edge is the inset inside, and no further', () => {
    const at = stage();
    const size = contentSize(at, 3);
    const far = clampView({ zoom: 3, x: 5000, y: 5000 }, at);
    expect(far.x).toBe(FIT_INSET);
    expect(far.y).toBe(FIT_INSET);
    const away = clampView({ zoom: 3, x: -5000, y: -5000 }, at);
    expect(away.x).toBeCloseTo(PANE.width - size.width - FIT_INSET);
    expect(away.y).toBeCloseTo(PANE.height - size.height - FIT_INSET);
    // Some of the page is always in view.
    expect(far.x).toBeLessThan(PANE.width);
    expect(away.x + size.width).toBeGreaterThan(0);
  });

  it('is idempotent', () => {
    const at = stage();
    for (const raw of [{ zoom: 2, x: 10, y: -999 }, { zoom: 7, x: -4000, y: 12 }, { zoom: 1, x: 3, y: 3 }]) {
      const once = clampView(raw, at);
      expect(clampView(once, at)).toEqual(once);
    }
  });

  it('pans by a delta and clamps the result', () => {
    const at = stage();
    const view = clampView({ zoom: 3, x: -100, y: -100 }, at);
    expect(panBy(view, 30, -20, at)).toEqual({ zoom: 3, x: -70, y: -120 });
    expect(panBy(view, 1e6, 0, at).x).toBe(FIT_INSET);
  });
});

describe('focusing a rectangle', () => {
  /** The rectangle the way the viewport sees it. */
  const onScreen = (rect: Rect, view: View, at: Stage) => toScreen(rect, view, at);

  it('centres a small target and gives it about half the pane, never more than the share', () => {
    const at = stage();
    const line: Rect = { left: 120, top: 400, width: 260, height: 14 };
    const view = focusView(line, at);
    const box = onScreen(line, view, at);
    expect(box.left + box.width / 2).toBeCloseTo(PANE.width / 2, 4);
    expect(box.top + box.height / 2).toBeCloseTo(PANE.height / 2, 4);
    expect(box.width + 2 * FOCUS_PADDING).toBeLessThanOrEqual(FOCUS_SHARE * PANE.width + 1e-6);
    expect(box.height + 2 * FOCUS_PADDING).toBeLessThanOrEqual(FOCUS_SHARE * PANE.height + 1e-6);
  });

  it('is limited by the width when the target is wide and by the height when it is tall', () => {
    const at = stage();
    const wide: Rect = { left: 60, top: 300, width: 480, height: 10 };
    const tall: Rect = { left: 300, top: 100, width: 10, height: 200 };
    const wideBox = onScreen(wide, focusView(wide, at), at);
    const tallBox = onScreen(tall, focusView(tall, at), at);
    expect(wideBox.width + 2 * FOCUS_PADDING).toBeCloseTo(FOCUS_SHARE * PANE.width, 4);
    expect(tallBox.height + 2 * FOCUS_PADDING).toBeCloseTo(FOCUS_SHARE * PANE.height, 4);
  });

  it('leaves a target that is bigger than the share at the whole page, not smaller than it', () => {
    const at = stage();
    const tall: Rect = { left: 300, top: 100, width: 10, height: 600 };
    expect(focusView(tall, at).zoom).toBe(1);
  });

  it('never blows a tiny target up past four times the fit', () => {
    const at = stage();
    const view = focusView({ left: 200, top: 200, width: 6, height: 6 }, at);
    expect(view.zoom).toBeLessThanOrEqual(MAX_FOCUS_ZOOM);
    expect(view.zoom).toBeCloseTo(MAX_FOCUS_ZOOM);
  });

  it('never goes below the whole page, so a target as big as the page leaves it whole', () => {
    const at = stage();
    const view = focusView({ left: 0, top: 0, width: A4.width, height: A4.height }, at);
    expect(view).toEqual(fitView(at));
  });

  it('respects the pixel cap on a very small page', () => {
    const small = stage({ width: 80, height: 80 }, { width: 900, height: 900 });
    const view = focusView({ left: 30, top: 30, width: 1, height: 1 }, small);
    expect(view.zoom * small.fit).toBeLessThanOrEqual(MAX_PIXELS_PER_POINT + 1e-9);
  });

  it('keeps a target near the corner on the screen when the clamp refuses to centre it', () => {
    const at = stage();
    const corner: Rect = { left: 4, top: 4, width: 200, height: 12 };
    const box = onScreen(corner, focusView(corner, at), at);
    expect(box.left).toBeGreaterThanOrEqual(0);
    expect(box.top).toBeGreaterThanOrEqual(0);
    expect(box.left + box.width).toBeLessThanOrEqual(PANE.width);
  });
});

describe('opening a page with nothing to point at', () => {
  it('opens a portrait page as wide as the pane allows, at its top', () => {
    const at = stage(A4, { width: 900, height: 600 });
    const view = openingView(at);
    expect(view.zoom).toBeGreaterThan(1);
    expect(contentSize(at, view.zoom).width).toBeCloseTo(900 - 2 * FIT_INSET, 3);
    expect(view.y).toBe(FIT_INSET);
  });

  it('opens a landscape sheet whole', () => {
    const at = stage(SHEET);
    expect(openingView(at)).toEqual(fitView(at));
  });

  it('leaves a narrow pane whole when the width is already the fit', () => {
    const at = stage(A4, { width: 400, height: 900 });
    expect(openingView(at)).toEqual(fitView(at));
  });
});

describe('the double click', () => {
  it('doubles the zoom around the point and returns to the whole page from the closest', () => {
    const at = stage();
    const start = fitView(at);
    const point = { x: 430, y: 200 };
    const first = doubleClickView(start, point, at);
    expect(first.zoom).toBeCloseTo(2);
    const closest = zoomAt(start, 1e9, point, at);
    expect(doubleClickView(closest, point, at)).toEqual(fitView(at));
  });
});

describe('two fingers', () => {
  it('zooms with the distance and follows the midpoint', () => {
    const at = stage();
    const view: View = clampView({ zoom: 2, x: -100, y: -100 }, at);
    const a = { x: 400, y: 300 };
    const b = { x: 500, y: 300 };
    const spread = pinchView({ view, a, b }, { a: { x: 350, y: 300 }, b: { x: 550, y: 300 } }, at);
    expect(spread.zoom).toBeCloseTo(4);
    // The page point that was under the starting midpoint is under the new midpoint.
    const before = pageAt(view, at, 450, 300);
    const after = pageAt(spread, at, 450, 300);
    expect(after.x).toBeCloseTo(before.x, 6);
    expect(after.y).toBeCloseTo(before.y, 6);
  });

  it('ignores fingers that start on the same spot', () => {
    const at = stage();
    const view = fitView(at);
    const same = { x: 100, y: 100 };
    expect(pinchView({ view, a: same, b: same }, { a: same, b: { x: 300, y: 100 } }, at)).toEqual(view);
  });
});

describe('the keyboard', () => {
  const press = (key: string, extra: Partial<{ ctrlKey: boolean; metaKey: boolean; altKey: boolean }> = {}) => ({
    key,
    ctrlKey: false,
    metaKey: false,
    altKey: false,
    ...extra,
  });

  it('zooms in on + and =, out on -, and shows the whole page on 0', () => {
    const at = stage();
    const start = fitView(at);
    expect(keyView(start, press('+'), at)?.zoom).toBeCloseTo(1.25);
    expect(keyView(start, press('='), at)?.zoom).toBeCloseTo(1.25);
    const closer = keyView(start, press('+'), at) as View;
    expect(keyView(closer, press('-'), at)?.zoom).toBeCloseTo(1);
    expect(keyView(closer, press('0'), at)).toEqual(fitView(at));
  });

  it('pans like a scroll: the arrow names the way the view goes', () => {
    const at = stage();
    const view = clampView({ zoom: 3, x: -300, y: -300 }, at);
    expect(keyView(view, press('ArrowRight'), at)).toEqual({ ...view, x: view.x - PAN_STEP });
    expect(keyView(view, press('ArrowLeft'), at)).toEqual({ ...view, x: view.x + PAN_STEP });
    expect(keyView(view, press('ArrowDown'), at)).toEqual({ ...view, y: view.y - PAN_STEP });
    expect(keyView(view, press('ArrowUp'), at)).toEqual({ ...view, y: view.y + PAN_STEP });
  });

  it('leaves every other key, and the browser’s own ctrl, meta and alt chords, alone', () => {
    const at = stage();
    const view = fitView(at);
    expect(keyView(view, press('a'), at)).toBeNull();
    expect(keyView(view, press('Enter'), at)).toBeNull();
    expect(keyView(view, press('+', { ctrlKey: true }), at)).toBeNull();
    expect(keyView(view, press('0', { metaKey: true }), at)).toBeNull();
    expect(keyView(view, press('ArrowLeft', { altKey: true }), at)).toBeNull();
  });
});

describe('page rectangles on the screen', () => {
  it('maps points to pixels under the view and grows by a padding', () => {
    const at = stage();
    const view: View = { zoom: 2, x: 10, y: 20 };
    const box = toScreen({ left: 100, top: 50, width: 40, height: 10 }, view, at);
    expect(box.left).toBeCloseTo(10 + 100 * at.fit * 2);
    expect(box.width).toBeCloseTo(40 * at.fit * 2);
    expect(grow(box, 5)).toEqual({
      left: box.left - 5,
      top: box.top - 5,
      width: box.width + 10,
      height: box.height + 10,
    });
  });
});
