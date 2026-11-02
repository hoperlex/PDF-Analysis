/**
 * Where the page sits inside its viewport: pan, zoom and the maths of moving them. Pure.
 *
 * One page is shown at a time. It is laid out once at the FIT size (the largest size at which
 * the whole page fits the viewport with a small inset), and a `View` is a CSS transform of
 * that box: `translate(x, y) scale(zoom)`. So a zoom of 1 is "the whole page", and the number
 * the reader sees in the control is a multiple of that, not of the sheet's printed size.
 *
 * Every function takes the `Stage` it works on and returns a new `View`, already clamped, so a
 * caller never holds a view that has the page dragged out of reach. Nothing here touches the
 * DOM, pdf.js or a clock, which is why the behaviour a reader feels (the point under the cursor
 * stays under the cursor, a small target fills about half the pane, the page cannot be thrown
 * away) is asserted in `tests/unit/review/view-state.test.ts` rather than only looked at.
 */

import type { Rect } from './locate-quotation';

export interface Size {
  readonly width: number;
  readonly height: number;
}

export interface Point {
  readonly x: number;
  readonly y: number;
}

/** `x` and `y` are where the page's top-left corner lies in the viewport, in CSS pixels. */
export interface View {
  readonly zoom: number;
  readonly x: number;
  readonly y: number;
}

/** What a view is a view of: the page, the viewport and the scale at which the page fits. */
export interface Stage {
  /** The page in PDF points, rotation applied (pdf.js viewport at scale 1). */
  readonly page: Size;
  /** The viewport in CSS pixels. */
  readonly viewport: Size;
  /** CSS pixels per point when the whole page fits (zoom 1). */
  readonly fit: number;
}

/** Room left around the page when it is fitted, and how far a zoomed page may be dragged past it. */
export const FIT_INSET = 16;

/** Never smaller than the whole page. */
export const MIN_ZOOM = 1;
/** The most a reader can zoom in, as a multiple of the fit. */
export const MAX_ZOOM = 10;
/** And the most in absolute terms: CSS pixels per point. A 10 pt letter is then 120 px tall. */
export const MAX_PIXELS_PER_POINT = 12;

/** A focus never goes beyond this multiple of the fit. */
export const MAX_FOCUS_ZOOM = 4;
/**
 * Nor beyond this many CSS pixels per PDF point, so a short target is not blown up until the page
 * around it is lost: at 2 px per point a 10 pt line is 20 px tall and a reader still sees its
 * neighbours. Only the AUTOMATIC focus is held to it; the reader can zoom on to the maximum.
 */
export const FOCUS_SCALE = 2;
/**
 * The least the automatic focus draws a point at, in CSS pixels, when the pane is too narrow to
 * show the target at the share below. A 370 pt line in a 340 px pane fitted at the share is 5 px
 * tall and cannot be read; at this scale a 10 pt line is 12 px tall, the target is wider than the
 * pane and is read by panning along it, and it starts at the left edge.
 */
export const READABLE_SCALE = 1.2;
/** A focused target takes at most this share of the viewport's width and of its height. */
export const FOCUS_SHARE = 0.6;
/** Screen pixels left around the target inside that share, for its frame and badge. */
export const FOCUS_PADDING = 10;
/** Room kept to the left of a target wider than the pane: its frame, and its badge in the margin. */
export const FOCUS_EDGE = FOCUS_PADDING + 28;

/** One press of `+` or `-`, one click on a control. */
export const ZOOM_STEP = 1.25;
/** One press of an arrow key, in CSS pixels. */
export const PAN_STEP = 72;

function positive(value: number): boolean {
  return Number.isFinite(value) && value > 0;
}

/** The stage for a page in a viewport, or null until both have a real size. */
export function makeStage(page: Size, viewport: Size): Stage | null {
  if (![page.width, page.height, viewport.width, viewport.height].every(positive)) return null;
  const room = {
    width: Math.max(1, viewport.width - 2 * FIT_INSET),
    height: Math.max(1, viewport.height - 2 * FIT_INSET),
  };
  return { page, viewport, fit: Math.min(room.width / page.width, room.height / page.height) };
}

/** The largest zoom this stage allows. */
export function maxZoom(stage: Stage): number {
  return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, MAX_PIXELS_PER_POINT / stage.fit));
}

export function clampZoom(zoom: number, stage: Stage): number {
  if (!Number.isFinite(zoom)) return MIN_ZOOM;
  return Math.min(maxZoom(stage), Math.max(MIN_ZOOM, zoom));
}

/** The page's size on the screen at a zoom, in CSS pixels. */
export function contentSize(stage: Stage, zoom: number): Size {
  return { width: stage.page.width * stage.fit * zoom, height: stage.page.height * stage.fit * zoom };
}

/**
 * One axis of the clamp. A page smaller than the viewport (less the inset) is held in the
 * middle; a larger one may be dragged until its edge is `FIT_INSET` inside the viewport, and
 * no further, so it can never be pushed out of reach.
 */
function clampAxis(offset: number, content: number, viewport: number): number {
  if (content <= viewport - 2 * FIT_INSET) return (viewport - content) / 2;
  return Math.min(FIT_INSET, Math.max(viewport - content - FIT_INSET, offset));
}

export function clampView(view: View, stage: Stage): View {
  const zoom = clampZoom(view.zoom, stage);
  const content = contentSize(stage, zoom);
  return {
    zoom,
    x: clampAxis(view.x, content.width, stage.viewport.width),
    y: clampAxis(view.y, content.height, stage.viewport.height),
  };
}

/** The whole page, centred. */
export function fitView(stage: Stage): View {
  return clampView({ zoom: MIN_ZOOM, x: 0, y: 0 }, stage);
}

/**
 * The view to open a page with nothing to point at.
 *
 * A portrait page fitted whole in a landscape pane is a narrow strip of text too small to
 * read, so such a page opens as wide as the pane allows and at its top, which is where a
 * reader starts. `0` and the percentage control still return to the whole page.
 */
export function openingView(stage: Stage): View {
  const room = stage.viewport.width - 2 * FIT_INSET;
  const wide = room / (stage.page.width * stage.fit);
  if (!(stage.page.height > stage.page.width) || !(wide > 1)) return fitView(stage);
  return clampView({ zoom: wide, x: 0, y: FIT_INSET }, stage);
}

/** Zoom to `next` keeping the viewport point `anchor` over the same spot of the page. */
export function zoomAt(view: View, next: number, anchor: Point, stage: Stage): View {
  const zoom = clampZoom(next, stage);
  const ratio = zoom / view.zoom;
  return clampView(
    {
      zoom,
      x: anchor.x - (anchor.x - view.x) * ratio,
      y: anchor.y - (anchor.y - view.y) * ratio,
    },
    stage,
  );
}

export function viewportCentre(stage: Stage): Point {
  return { x: stage.viewport.width / 2, y: stage.viewport.height / 2 };
}

/** One step in (`direction` 1) or out (-1) around `anchor`. */
export function stepZoom(view: View, direction: 1 | -1, anchor: Point, stage: Stage): View {
  return zoomAt(view, direction === 1 ? view.zoom * ZOOM_STEP : view.zoom / ZOOM_STEP, anchor, stage);
}

export function panBy(view: View, dx: number, dy: number, stage: Stage): View {
  return clampView({ zoom: view.zoom, x: view.x + dx, y: view.y + dy }, stage);
}

/**
 * The view that brings `target` (page points) into the viewport, as large as is comfortable.
 *
 * Its width and height each take at most `FOCUS_SHARE` of the viewport once `FOCUS_PADDING` is
 * allowed around it, but the zoom is never more than `FOCUS_SCALE` pixels per point or
 * `MAX_FOCUS_ZOOM` times the fit, and never less than the whole page. The width alone yields to
 * `READABLE_SCALE`: a pane too narrow to show a line at the share draws it readable and wider
 * than the pane rather than whole and too small to read. A target that fits across is centred; one
 * that does not starts at the left edge, where a reader starts a line. The height has no such
 * exception, so a target never overflows the pane vertically. The clamp still refuses to push the
 * page off, so a page that already fits simply stays whole.
 */
export function focusView(target: Rect, stage: Stage): View {
  const room = (viewport: number) => Math.max(1, FOCUS_SHARE * viewport - 2 * FOCUS_PADDING);
  const byWidth =
    target.width > 0 ? room(stage.viewport.width) / (target.width * stage.fit) : Number.POSITIVE_INFINITY;
  const byHeight =
    target.height > 0 ? room(stage.viewport.height) / (target.height * stage.fit) : Number.POSITIVE_INFINITY;
  const ceiling = Math.min(MAX_FOCUS_ZOOM, FOCUS_SCALE / stage.fit, maxZoom(stage));
  const readable = READABLE_SCALE / stage.fit;
  const zoom = clampZoom(Math.min(ceiling, byHeight, Math.max(byWidth, readable)), stage);
  const scale = stage.fit * zoom;
  const wide = target.width * scale + 2 * FOCUS_EDGE > stage.viewport.width;
  return clampView(
    {
      zoom,
      x: wide
        ? FOCUS_EDGE - target.left * scale
        : stage.viewport.width / 2 - (target.left + target.width / 2) * scale,
      y: stage.viewport.height / 2 - (target.top + target.height / 2) * scale,
    },
    stage,
  );
}

/** A double click: twice as close around the point, or back to the whole page from the closest. */
export function doubleClickView(view: View, point: Point, stage: Stage): View {
  const closest = maxZoom(stage);
  if (view.zoom >= closest * 0.999) return fitView(stage);
  return zoomAt(view, view.zoom * 2, point, stage);
}

/** The zoom change of one wheel event, as a factor. A trackpad pinch arrives as ctrl + wheel. */
export function wheelFactor(deltaY: number, deltaMode: number): number {
  const pixels = deltaMode === 1 ? deltaY * 33 : deltaMode === 2 ? deltaY * 400 : deltaY;
  const bounded = Math.max(-120, Math.min(120, pixels));
  return Math.exp(-bounded * 0.0025);
}

/** Two fingers: the zoom follows their distance and the page follows their midpoint. */
export function pinchView(
  start: { readonly view: View; readonly a: Point; readonly b: Point },
  now: { readonly a: Point; readonly b: Point },
  stage: Stage,
): View {
  const before = Math.hypot(start.a.x - start.b.x, start.a.y - start.b.y);
  const after = Math.hypot(now.a.x - now.b.x, now.a.y - now.b.y);
  if (!(before >= 1)) return start.view;
  const zoom = clampZoom(start.view.zoom * (after / before), stage);
  const ratio = zoom / start.view.zoom;
  const from = { x: (start.a.x + start.b.x) / 2, y: (start.a.y + start.b.y) / 2 };
  const to = { x: (now.a.x + now.b.x) / 2, y: (now.a.y + now.b.y) / 2 };
  return clampView(
    {
      zoom,
      x: to.x - (from.x - start.view.x) * ratio,
      y: to.y - (from.y - start.view.y) * ratio,
    },
    stage,
  );
}

/** The part of a keyboard event the viewer reads. */
export interface KeyPress {
  readonly key: string;
  readonly ctrlKey: boolean;
  readonly metaKey: boolean;
  readonly altKey: boolean;
}

/**
 * What a key does, or null when it is not the viewer's. Keys with ctrl, meta or alt belong to
 * the browser (ctrl and plus is ITS zoom) and are left alone.
 */
export function keyView(view: View, press: KeyPress, stage: Stage): View | null {
  if (press.ctrlKey || press.metaKey || press.altKey) return null;
  switch (press.key) {
    case '+':
    case '=':
      return stepZoom(view, 1, viewportCentre(stage), stage);
    case '-':
    case '_':
      return stepZoom(view, -1, viewportCentre(stage), stage);
    case '0':
      return fitView(stage);
    case 'ArrowLeft':
      return panBy(view, PAN_STEP, 0, stage);
    case 'ArrowRight':
      return panBy(view, -PAN_STEP, 0, stage);
    case 'ArrowUp':
      return panBy(view, 0, PAN_STEP, stage);
    case 'ArrowDown':
      return panBy(view, 0, -PAN_STEP, stage);
    default:
      return null;
  }
}

/** A rectangle given in page points, as it lies in the viewport under `view`. */
export function toScreen(rect: Rect, view: View, stage: Stage): Rect {
  const scale = stage.fit * view.zoom;
  return {
    left: view.x + rect.left * scale,
    top: view.y + rect.top * scale,
    width: rect.width * scale,
    height: rect.height * scale,
  };
}

/** `rect` grown by `padding` on every side. */
export function grow(rect: Rect, padding: number): Rect {
  return {
    left: rect.left - padding,
    top: rect.top - padding,
    width: rect.width + 2 * padding,
    height: rect.height + 2 * padding,
  };
}

export function sameView(a: View, b: View): boolean {
  return a.zoom === b.zoom && a.x === b.x && a.y === b.y;
}

/** The label of the zoom control: a multiple of the whole-page fit, as a percentage. */
export function zoomPercent(view: View): number {
  return Math.round(view.zoom * 100);
}
