/**
 * Which tiles each layer of the window asks for (`CMP-VIEWER-01`).
 *
 * A pane shows one *kind* of sheet: the overlay (both pages and the chosen layers), page A alone, or page B alone. For
 * each it asks for the tiles of one pyramid level that the window touches, and for the top level of the pyramid — a
 * single tile that holds the whole sheet — as an underlay: it is the first thing to arrive and it keeps the pane from
 * going blank while the right level is on its way.
 */

import type { ComparisonLayer } from '@/shared/api';

import { type PlacedTile, type PyramidLevel, type Viewport, levelForZoom, placeTile, visibleTiles } from './pyramid';
import type { TileRequest } from './tile-loader';
import { type ViewerContext, type ViewerState, layersQuery } from './viewer-state';

export type SheetKind = 'overlay' | 'a' | 'b';

export interface Placed {
  readonly request: TileRequest;
  readonly tile: PlacedTile;
}

export interface SheetTiles {
  readonly kind: SheetKind;
  /** The whole sheet at the top of the pyramid. */
  readonly underlay: Placed;
  /** The tiles of the level the zoom wants, that the window touches. */
  readonly tiles: readonly Placed[];
}

function requestFor(kind: SheetKind, level: number, column: number, row: number, state: ViewerState): TileRequest {
  if (kind === 'overlay') {
    const layers = layersQuery(state.layers as readonly ComparisonLayer[]);
    return {
      mode: 'overlay', level, column, row,
      ...(layers === undefined ? {} : { layers }),
      ...(state.alignBlocks ? { align: true } : {}),
    };
  }
  if (kind === 'b') return { mode: 'b', level, column, row, ...(state.alignBlocks ? { align: true } : {}) };
  return { mode: 'a', level, column, row };
}

export function sheetTiles(
  kind: SheetKind,
  state: ViewerState,
  levels: readonly PyramidLevel[],
  pane: Viewport,
): SheetTiles {
  const top = levels[levels.length - 1] as PyramidLevel;
  const underlay = { request: requestFor(kind, top.level, 0, 0, state), tile: placeTile(top, 0, 0) };
  const level = levelForZoom(state.view.zoom, levels);
  const tiles =
    level === top.level
      ? []
      : visibleTiles(levels, level, state.view, pane).map((tile) => ({
          request: requestFor(kind, tile.level, tile.column, tile.row, state),
          tile,
        }));
  return { kind, underlay, tiles };
}

/** Which sheets the window shows in this state, in the order they are drawn (bottom first). */
export function shownKinds(state: ViewerState, context: Pick<ViewerContext, 'hasA' | 'hasB'>): SheetKind[] {
  if (state.mode === 'side') return [...(context.hasA ? (['a'] as const) : []), ...(context.hasB ? (['b'] as const) : [])];
  return state.swipe ? [state.under, 'overlay'] : ['overlay'];
}

/** Every request the window wants, underlays first, so the loader serves the whole sheet before the detail. */
export function wantedRequests(sheets: readonly SheetTiles[]): TileRequest[] {
  return [...sheets.map((sheet) => sheet.underlay.request), ...sheets.flatMap((sheet) => sheet.tiles.map((placed) => placed.request))];
}
