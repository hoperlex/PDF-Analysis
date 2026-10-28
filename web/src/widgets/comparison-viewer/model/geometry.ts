/**
 * The sheet the viewer draws, from what the pair knows about it (`CMP-VIEWER-01`).
 *
 * A compared pair carries the canvas of the older page in points and the resolution it was compared at, which is the
 * resolution of the page profile's pyramid (both are the registration dpi of one rule), so the size of level 0 is
 * `ceil(points * dpi / 72)`. A pair that has no result (a queued pair, an added or removed sheet, a page that was never
 * registered) has neither, and the page that is shown then has a size only its own profile knows: the page passes it as
 * `rasterSize` (`raster_width_px` and `raster_height_px` of `getVersionPageProfile`). With neither, the viewer says it
 * cannot draw the sheet rather than draw a guess.
 */

import type { ComparisonSheetPair } from '@/shared/api';

import { type PyramidLevel, type RasterSize, pyramidLevels, rasterFromCanvas } from './pyramid';

export interface ViewerGeometry {
  readonly raster: RasterSize;
  readonly dpi: number;
  readonly levels: readonly PyramidLevel[];
}

/** The resolution used to place a box when the pair does not say (there are no boxes then). */
export const FALLBACK_DPI = 72;

export function viewerGeometry(pair: ComparisonSheetPair, rasterSize?: RasterSize): ViewerGeometry | null {
  const dpi = pair.how_compared?.dpi;
  let raster: RasterSize | null = null;
  if (rasterSize !== undefined && rasterSize.widthPx > 0 && rasterSize.heightPx > 0) raster = rasterSize;
  else if (pair.canvas !== undefined && dpi !== undefined) raster = rasterFromCanvas(pair.canvas.width_pt, pair.canvas.height_pt, dpi);
  if (raster === null) return null;
  return { raster, dpi: dpi ?? FALLBACK_DPI, levels: pyramidLevels(raster) };
}

/** Whether the overlay exists for the pair: both pages, a result, and the registration that lays B on A. */
export function canShowOverlay(pair: ComparisonSheetPair): boolean {
  return (
    pair.page_a !== undefined &&
    pair.page_b !== undefined &&
    pair.result_id !== undefined &&
    pair.how_compared?.transform !== undefined
  );
}
