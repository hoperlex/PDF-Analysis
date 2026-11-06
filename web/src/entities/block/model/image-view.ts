/**
 * Where a block's image sits inside its stage: zoom and pan, and the arithmetic of moving them. Pure.
 *
 * The original's block view zooms its picture with the wheel from 1 to 12 times, a step of 1.15 in
 * and 0.87 out, around the pointer; drags it once it is larger than the stage; and a double click
 * puts it back. This is that, as functions a test calls: the static render this suite has cannot
 * fire a wheel event, so the behaviour a reader feels (the point under the pointer stays under the
 * pointer, the image cannot be dragged out of reach, a stage that is not zoomed does not pan) is
 * asserted on these, not looked at.
 *
 * The image is laid out once at the size of the stage (contained, so a crop of any proportion
 * fits whole), and a `View` is a CSS transform of that box: `translate(x, y) scale(zoom)` from its
 * top-left corner. A zoom of 1 is "the whole image", and the number a reader sees is a multiple of
 * that, not of the crop's pixel size.
 *
 * The same shape as the page viewer's model (`features/open-evidence`), which is another slice's
 * internals and so is not imported; this is the small part a still image needs.
 */

export interface Size {
  readonly width: number;
  readonly height: number;
}

export interface Point {
  readonly x: number;
  readonly y: number;
}

/** `x` and `y` are where the image's top-left corner lies in the stage, in CSS pixels. */
export interface View {
  readonly zoom: number;
  readonly x: number;
  readonly y: number;
}

/** Never smaller than the whole image. */
export const MIN_ZOOM = 1;
/** The most a reader can zoom in, as a multiple of the whole image. */
export const MAX_ZOOM = 12;
/** One notch of the wheel away from the reader (zoom in), and towards (zoom out). */
export const WHEEL_IN = 1.15;
export const WHEEL_OUT = 0.87;

/** The whole image, centred in its stage. */
export const WHOLE_IMAGE: View = { zoom: MIN_ZOOM, x: 0, y: 0 };

function usable(stage: Size): boolean {
  return Number.isFinite(stage.width) && Number.isFinite(stage.height) && stage.width > 0 && stage.height > 0;
}

export function clampZoom(zoom: number): number {
  if (!Number.isFinite(zoom)) return MIN_ZOOM;
  return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, zoom));
}

/**
 * Hold a view inside its stage: the image's edges may reach the stage's edges and no further, so a
 * zoomed image can never be pushed out of reach. A stage with no size yet leaves the whole image.
 */
export function clampView(view: View, stage: Size): View {
  const zoom = clampZoom(view.zoom);
  if (!usable(stage)) return WHOLE_IMAGE;
  const axis = (offset: number, extent: number): number => {
    const least = extent * (1 - zoom);
    if (!Number.isFinite(offset)) return 0;
    return Math.min(0, Math.max(least, offset));
  };
  return { zoom, x: axis(view.x, stage.width), y: axis(view.y, stage.height) };
}

/** Zoom by `factor` keeping the stage point `anchor` over the same spot of the image. */
export function zoomAround(view: View, factor: number, anchor: Point, stage: Size): View {
  if (!(Number.isFinite(factor) && factor > 0)) return clampView(view, stage);
  const zoom = clampZoom(view.zoom * factor);
  const ratio = zoom / view.zoom;
  return clampView(
    { zoom, x: anchor.x - (anchor.x - view.x) * ratio, y: anchor.y - (anchor.y - view.y) * ratio },
    stage,
  );
}

/** One wheel event: away from the reader (`deltaY` below zero) zooms in, towards zooms out. */
export function wheelZoom(view: View, deltaY: number, anchor: Point, stage: Size): View {
  if (!Number.isFinite(deltaY) || deltaY === 0) return view;
  return zoomAround(view, deltaY < 0 ? WHEEL_IN : WHEEL_OUT, anchor, stage);
}

/** Whether the image is larger than its stage, which is the only time a drag moves it. */
export function isZoomed(view: View): boolean {
  return view.zoom > MIN_ZOOM;
}

/** A drag of `dx`, `dy` from `origin`; a view that is not zoomed does not move. */
export function panBy(origin: View, dx: number, dy: number, stage: Size): View {
  if (!isZoomed(origin)) return clampView(origin, stage);
  return clampView({ zoom: origin.zoom, x: origin.x + dx, y: origin.y + dy }, stage);
}

/** The CSS transform that draws a view. */
export function viewTransform(view: View): string {
  return `translate(${view.x}px, ${view.y}px) scale(${view.zoom})`;
}

/** «×2,3»: how many times larger than the whole image, one decimal. */
export function zoomLabel(view: View): string {
  return `×${view.zoom.toFixed(1).replace('.', ',')}`;
}
