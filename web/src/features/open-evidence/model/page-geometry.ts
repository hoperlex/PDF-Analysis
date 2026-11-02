/**
 * How sharp a page is drawn: the bitmap budget, and nothing about where the page sits.
 *
 * Where the page sits and how large it looks is `view-state.ts`. The browser's own viewer fitted
 * the WHOLE document to its widest sheet, so a volume that mixes A4 pages with a drawing sheet
 * three times as wide drew every A4 page at a third of the pane; here the single declared page
 * is fitted on its own and nothing else in the document is consulted.
 */

/**
 * Pixels of canvas backing store the viewer will allocate for one page. A page zoomed in on a
 * dense screen would otherwise ask for a bitmap larger than the browser allows and fail with a
 * blank canvas, which is the one outcome this viewer must not produce. Past the budget the
 * bitmap is drawn at a smaller scale and the browser stretches it: softer, never blank.
 */
export const MAX_CANVAS_PIXELS = 16_000_000;

/**
 * The pdf.js viewport scale to draw a page at, given what the screen needs.
 *
 * `wanted` is pixels per point on the screen (fit scale times zoom times the device pixel
 * ratio). The result never lets the bitmap exceed `MAX_CANVAS_PIXELS`. Null when any input is not
 * a positive finite number: the caller waits for a real measurement instead of drawing at
 * scale 0.
 */
export function bitmapScale(wanted: number, pageWidth: number, pageHeight: number): number | null {
  if (![wanted, pageWidth, pageHeight].every((value) => Number.isFinite(value) && value > 0)) {
    return null;
  }
  const budget = Math.sqrt(MAX_CANVAS_PIXELS / (pageWidth * pageHeight));
  return Math.min(wanted, budget);
}
