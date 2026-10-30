import type { VersionPageProfile } from '@/shared/api';
import type { TileStatus, ViewerGeometry, ViewerState } from '@/widgets/comparison-viewer';

export type StageTileRequest = Parameters<TileStatus['urlOf']>[0];

export function profileGeometry(profile: VersionPageProfile | undefined): ViewerGeometry | null {
  const width = profile?.raster_width_px;
  const height = profile?.raster_height_px;
  if (width === undefined || height === undefined || width <= 0 || height <= 0) return null;
  const levels = [];
  let currentWidth = width;
  let currentHeight = height;
  for (let level = 0; ; level += 1) {
    levels.push({ level, widthPx: currentWidth, heightPx: currentHeight,
      columns: Math.ceil(currentWidth / 512), rows: Math.ceil(currentHeight / 512) });
    if (Math.max(currentWidth, currentHeight) <= 512) break;
    currentWidth = Math.ceil(currentWidth / 2);
    currentHeight = Math.ceil(currentHeight / 2);
  }
  return { raster: { widthPx: width, heightPx: height }, levels,
    dpi: profile?.width_pt === undefined || profile.width_pt <= 0 ? 72 : width * 72 / profile.width_pt };
}

export function stageTileKey(request: Pick<StageTileRequest, 'level' | 'column' | 'row'>): string {
  return `${request.level}/${request.column}/${request.row}`;
}

export function stageTileRequests(geometry: ViewerGeometry | null, state: ViewerState): StageTileRequest[] {
  if (geometry === null) return [];
  const level = Math.max(0, Math.min(Math.floor(Math.log2(1 / state.view.zoom) + 1e-9), geometry.levels.length - 1));
  const top = geometry.levels.at(-1)!;
  const selected = geometry.levels[level]!;
  const requests: StageTileRequest[] = [{ mode: 'a', level: top.level, column: 0, row: 0 }];
  if (level === top.level) return requests;
  const span = 512 * 2 ** level;
  const firstColumn = Math.max(0, Math.floor(-state.view.offsetX / state.view.zoom / span));
  const lastColumn = Math.min(selected.columns - 1, Math.floor((state.viewport.width - state.view.offsetX) / state.view.zoom / span));
  const firstRow = Math.max(0, Math.floor(-state.view.offsetY / state.view.zoom / span));
  const lastRow = Math.min(selected.rows - 1, Math.floor((state.viewport.height - state.view.offsetY) / state.view.zoom / span));
  for (let row = firstRow; row <= lastRow; row += 1) {
    for (let column = firstColumn; column <= lastColumn; column += 1) requests.push({ mode: 'a', level, column, row });
  }
  return requests;
}

/** Preserve page-relative centre and zoom relative to fit across different paper sizes. */
export function synchroniseView(
  source: ViewerState, sourceGeometry: ViewerGeometry,
  target: ViewerState, targetGeometry: ViewerGeometry,
): ViewerState {
  const fit = (state: ViewerState, geometry: ViewerGeometry) => Math.min(
    state.viewport.width / geometry.raster.widthPx, state.viewport.height / geometry.raster.heightPx,
  ) * .98;
  const ratio = source.view.zoom / fit(source, sourceGeometry);
  const zoom = fit(target, targetGeometry) * ratio;
  const x = (source.viewport.width / 2 - source.view.offsetX) / (sourceGeometry.raster.widthPx * source.view.zoom);
  const y = (source.viewport.height / 2 - source.view.offsetY) / (sourceGeometry.raster.heightPx * source.view.zoom);
  return { ...target, view: { zoom,
    offsetX: target.viewport.width / 2 - x * targetGeometry.raster.widthPx * zoom,
    offsetY: target.viewport.height / 2 - y * targetGeometry.raster.heightPx * zoom } };
}
