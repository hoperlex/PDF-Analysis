/**
 * The tile pyramid of a sheet pair, as the viewer sees it (`CMP-VIEWER-01`).
 *
 * The server cuts the pyramid from page A's working raster (`comparison/tiles/grid.py`, `comparison/profile`): 512 px
 * tiles, level `n + 1` being level `n` reduced by two (`ceil` of each side), stopping at the first level whose long
 * side fits in one tile. This file is the same arithmetic on the client: the number of levels, columns and rows, and
 * which tiles a window of the sheet needs. A level, column or row the server does not have is `404`, so the client must
 * not guess a different pyramid: the size comes from the result (`canvas` in points, `how_compared.dpi`), or from the
 * page's own profile when the page passes it.
 *
 * **Coordinates.** The *sheet* is level 0's pixels: a point of the canvas is `points * dpi / 72` of them. A view maps
 * the sheet to the screen: `screen = offset + sheet * zoom`.
 */

export const TILE_PX = 512;
/** The original's limits (`version-comparison-zoom.js:67`): from a quarter of the fit to sixty-four times it. */
export const MIN_ZOOM_OF_FIT = 0.25;
export const MAX_ZOOM_OF_FIT = 64;
/** One step of the wheel and of the buttons (`version-comparison-zoom.js:107`). */
export const ZOOM_STEP = 1.15;
/** The fit leaves a margin of two per cent round the sheet (`version-comparison-zoom.js:37`). */
const FIT_MARGIN = 0.98;
const POINTS_PER_INCH = 72;

export interface RasterSize {
  readonly widthPx: number;
  readonly heightPx: number;
}

export interface PyramidLevel {
  readonly level: number;
  readonly widthPx: number;
  readonly heightPx: number;
  readonly columns: number;
  readonly rows: number;
}

export interface View {
  readonly zoom: number;
  readonly offsetX: number;
  readonly offsetY: number;
}

export interface Viewport {
  readonly width: number;
  readonly height: number;
}

/** One tile, placed on the sheet (level 0's pixels). */
export interface PlacedTile {
  readonly level: number;
  readonly column: number;
  readonly row: number;
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
}

/** The raster of a page of `widthPt` x `heightPt` points at `dpi`, as `PyramidLevel` 0 has it. */
export function rasterFromCanvas(widthPt: number, heightPt: number, dpi: number): RasterSize {
  const scale = dpi / POINTS_PER_INCH;
  return {
    widthPx: Math.max(1, Math.ceil(widthPt * scale - 1e-9)),
    heightPx: Math.max(1, Math.ceil(heightPt * scale - 1e-9)),
  };
}

export function pyramidLevels(raster: RasterSize): readonly PyramidLevel[] {
  const levels: PyramidLevel[] = [];
  let width = raster.widthPx;
  let height = raster.heightPx;
  for (let level = 0; ; level += 1) {
    levels.push({
      level,
      widthPx: width,
      heightPx: height,
      columns: Math.ceil(width / TILE_PX),
      rows: Math.ceil(height / TILE_PX),
    });
    if (Math.max(width, height) <= TILE_PX) return levels;
    width = Math.ceil(width / 2);
    height = Math.ceil(height / 2);
  }
}

/** The coarsest level that still looks right at `zoom` screen pixels per sheet pixel (never above the pyramid). */
export function levelForZoom(zoom: number, levels: readonly PyramidLevel[]): number {
  const wanted = Math.floor(Math.log2(1 / zoom) + 1e-9);
  return Math.max(0, Math.min(wanted, levels.length - 1));
}

/** The tiles of `level` that a window of the sheet touches, in reading order. */
export function visibleTiles(
  levels: readonly PyramidLevel[],
  level: number,
  view: View,
  viewport: Viewport,
): PlacedTile[] {
  const info = levels[level];
  if (info === undefined) return [];
  const span = 2 ** level;
  const tileOnSheet = TILE_PX * span;
  const left = (0 - view.offsetX) / view.zoom;
  const top = (0 - view.offsetY) / view.zoom;
  const right = (viewport.width - view.offsetX) / view.zoom;
  const bottom = (viewport.height - view.offsetY) / view.zoom;
  const firstColumn = Math.max(0, Math.floor(left / tileOnSheet));
  const lastColumn = Math.min(info.columns - 1, Math.floor(right / tileOnSheet));
  const firstRow = Math.max(0, Math.floor(top / tileOnSheet));
  const lastRow = Math.min(info.rows - 1, Math.floor(bottom / tileOnSheet));
  const tiles: PlacedTile[] = [];
  for (let row = firstRow; row <= lastRow; row += 1) {
    for (let column = firstColumn; column <= lastColumn; column += 1) {
      tiles.push(placeTile(info, column, row));
    }
  }
  return tiles;
}

/** Where tile `(column, row)` of `info` lies on the sheet. */
export function placeTile(info: PyramidLevel, column: number, row: number): PlacedTile {
  const span = 2 ** info.level;
  const widthPx = Math.min(TILE_PX, info.widthPx - column * TILE_PX);
  const heightPx = Math.min(TILE_PX, info.heightPx - row * TILE_PX);
  return {
    level: info.level,
    column,
    row,
    left: column * TILE_PX * span,
    top: row * TILE_PX * span,
    width: widthPx * span,
    height: heightPx * span,
  };
}

/** The zoom that shows the whole sheet in the window. */
export function fitZoom(raster: RasterSize, viewport: Viewport): number {
  if (raster.widthPx <= 0 || raster.heightPx <= 0 || viewport.width <= 0 || viewport.height <= 0) return 1;
  return Math.min(viewport.width / raster.widthPx, viewport.height / raster.heightPx) * FIT_MARGIN;
}

export function fitView(raster: RasterSize, viewport: Viewport): View {
  const zoom = fitZoom(raster, viewport);
  return {
    zoom,
    offsetX: (viewport.width - raster.widthPx * zoom) / 2,
    offsetY: (viewport.height - raster.heightPx * zoom) / 2,
  };
}

function clampZoom(zoom: number, raster: RasterSize, viewport: Viewport): number {
  const fit = fitZoom(raster, viewport);
  return Math.min(fit * MAX_ZOOM_OF_FIT, Math.max(fit * MIN_ZOOM_OF_FIT, zoom));
}

/** Zoom by `factor` keeping the sheet point under `anchor` (window coordinates) where it is. */
export function zoomAt(
  view: View,
  factor: number,
  anchor: { readonly x: number; readonly y: number },
  raster: RasterSize,
  viewport: Viewport,
): View {
  const zoom = clampZoom(view.zoom * factor, raster, viewport);
  const ratio = zoom / view.zoom;
  return {
    zoom,
    offsetX: anchor.x - (anchor.x - view.offsetX) * ratio,
    offsetY: anchor.y - (anchor.y - view.offsetY) * ratio,
  };
}

/** A view that shows `box` (in sheet pixels) centred, with room around it, and no closer than the zoom limit. */
export function focusBox(
  box: { readonly left: number; readonly top: number; readonly width: number; readonly height: number },
  raster: RasterSize,
  viewport: Viewport,
): View {
  const margin = 4;
  const wanted = Math.min(
    viewport.width / Math.max(1, box.width * margin),
    viewport.height / Math.max(1, box.height * margin),
  );
  const zoom = clampZoom(Math.max(wanted, fitZoom(raster, viewport)), raster, viewport);
  const centreX = box.left + box.width / 2;
  const centreY = box.top + box.height / 2;
  return { zoom, offsetX: viewport.width / 2 - centreX * zoom, offsetY: viewport.height / 2 - centreY * zoom };
}

/** `box` in points on the older page's canvas, in sheet pixels. */
export function boxToSheet(
  box: { readonly x: number; readonly y: number; readonly width: number; readonly height: number },
  dpi: number,
): { readonly left: number; readonly top: number; readonly width: number; readonly height: number } {
  const scale = dpi / POINTS_PER_INCH;
  return { left: box.x * scale, top: box.y * scale, width: box.width * scale, height: box.height * scale };
}
