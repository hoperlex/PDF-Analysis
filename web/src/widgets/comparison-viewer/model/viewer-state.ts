/**
 * The state of the sheet viewer and what changes it (`CMP-VIEWER-01`): a pure reducer, so that every control has a
 * test that does not need a browser.
 *
 * The modes are «Наложение» and «Рядом»; «шторка» is a checkbox over the overlay and is off in «Рядом»; A and B are the
 * panes of «Рядом» and the under-layer of «шторка», not modes (plan §1.1). A second click on the mode that is already
 * chosen returns to the previous one (`setMode`, `version-comparison-viewer.js:261-267`).
 */

import type { ComparisonLayer } from '@/shared/api';

import { DEFAULT_LAYERS, LAYER_ORDER } from './labels';
import {
  type RasterSize,
  type View,
  type Viewport,
  boxToSheet,
  fitView,
  focusBox,
  zoomAt,
} from './pyramid';
import { type DifferenceFilter, differenceAt, stepDifference } from './differences';
import type { ComparisonDifference } from '@/shared/api';

export type ViewMode = 'overlay' | 'side';
export type UnderLayer = 'a' | 'b';

export interface ViewerState {
  readonly mode: ViewMode;
  readonly previousMode: ViewMode;
  readonly swipe: boolean;
  /**
   * Where the swipe divider stands, 0 to 100 (per cent of the window's width). The overlay is shown to the right of it and
   * the lower sheet to the left, so the divider starts at the left edge and dragging it right opens the lower sheet
   * (`version-comparison-viewer.js:120`: «Тяните вправо — лист B (сверху) скрывается, открывается A»).
   */
  readonly swipePosition: number;
  readonly under: UnderLayer;
  /** Layers drawn, always in the order of `LAYER_ORDER`. */
  readonly layers: readonly ComparisonLayer[];
  readonly showBoxes: boolean;
  readonly alignBlocks: boolean;
  readonly showShifts: boolean;
  readonly showStyleOnly: boolean;
  /** Index into the result's own list of differences, or `null`. */
  readonly selected: number | null;
  readonly view: View;
  readonly viewport: Viewport;
  /** Whether the window has been measured: until it has, `viewport` is a stand-in size. */
  readonly measured: boolean;
}

export type ViewerAction =
  | { readonly type: 'mode'; readonly mode: ViewMode }
  | { readonly type: 'swipe'; readonly on: boolean }
  | { readonly type: 'swipe-position'; readonly position: number }
  | { readonly type: 'under'; readonly under: UnderLayer }
  | { readonly type: 'layer'; readonly layer: ComparisonLayer; readonly on: boolean }
  | { readonly type: 'boxes'; readonly on: boolean }
  | { readonly type: 'align'; readonly on: boolean }
  | { readonly type: 'shifts'; readonly on: boolean }
  | { readonly type: 'style-only'; readonly on: boolean }
  | { readonly type: 'viewport'; readonly viewport: Viewport }
  | { readonly type: 'fit' }
  | { readonly type: 'pan'; readonly dx: number; readonly dy: number }
  | { readonly type: 'zoom'; readonly factor: number; readonly anchor?: { readonly x: number; readonly y: number } }
  | { readonly type: 'select'; readonly index: number | null }
  | { readonly type: 'pick'; readonly point: { readonly x: number; readonly y: number } }
  | { readonly type: 'focus-box'; readonly box: { readonly x: number; readonly y: number; readonly width: number; readonly height: number } }
  | { readonly type: 'step'; readonly direction: -1 | 1 };

/** What the reducer needs to know about the sheet and does not change. */
export interface ViewerContext {
  readonly raster: RasterSize;
  readonly dpi: number;
  readonly differences: readonly ComparisonDifference[];
  /** The overlay exists: both pages, a result and its registration. Without it only the pages are shown. */
  readonly canOverlay: boolean;
  readonly hasA: boolean;
  readonly hasB: boolean;
}

/** Used until the window is measured (a server render, a test). */
export const DEFAULT_VIEWPORT: Viewport = { width: 960, height: 640 };

export function initialState(context: ViewerContext, viewport: Viewport = DEFAULT_VIEWPORT): ViewerState {
  const mode: ViewMode = context.canOverlay ? 'overlay' : 'side';
  return {
    mode,
    previousMode: mode,
    swipe: false,
    swipePosition: 0,
    under: 'a',
    layers: LAYER_ORDER.filter((layer) => DEFAULT_LAYERS.includes(layer)),
    showBoxes: false,
    alignBlocks: false,
    showShifts: false,
    showStyleOnly: false,
    selected: null,
    view: fitView(context.raster, mode === 'side' ? { width: Math.floor(viewport.width / paneCount(context)), height: viewport.height } : viewport),
    viewport,
    measured: false,
  };
}

export function filterOf(state: ViewerState): DifferenceFilter {
  return { showShifts: state.showShifts, showStyleOnly: state.showStyleOnly };
}

/** The `layers` query value: the chosen layers, comma-separated, in the contract's order; `undefined` for none. */
export function layersQuery(layers: readonly ComparisonLayer[]): string | undefined {
  const ordered = LAYER_ORDER.filter((layer) => layers.includes(layer));
  return ordered.length === 0 ? undefined : ordered.join(',');
}

function focusOn(state: ViewerState, context: ViewerContext, index: number | null): ViewerState {
  if (index === null) return { ...state, selected: null };
  const difference = context.differences[index];
  if (difference === undefined) return { ...state, selected: null };
  const viewport = paneOf(state, context);
  return {
    ...state,
    selected: index,
    view: focusBox(boxToSheet(difference.box, context.dpi), context.raster, viewport),
  };
}

export function reduce(state: ViewerState, action: ViewerAction, context: ViewerContext): ViewerState {
  switch (action.type) {
    case 'mode': {
      if (action.mode === 'overlay' && !context.canOverlay) return state;
      const mode = action.mode === state.mode ? state.previousMode : action.mode;
      const next: ViewerState = { ...state, mode, previousMode: state.mode, swipe: mode === 'side' ? false : state.swipe };
      // The panes change width with the mode: the sheet is fitted again so that none of it is left outside.
      return { ...next, view: fitView(context.raster, paneOf(next, context)) };
    }
    case 'swipe':
      return state.mode === 'side' ? state : { ...state, swipe: action.on };
    case 'swipe-position':
      return { ...state, swipePosition: Math.min(100, Math.max(0, action.position)) };
    case 'under':
      return { ...state, under: action.under };
    case 'layer': {
      const without = state.layers.filter((layer) => layer !== action.layer);
      const next = action.on ? [...without, action.layer] : without;
      return { ...state, layers: LAYER_ORDER.filter((layer) => next.includes(layer)) };
    }
    case 'boxes':
      return { ...state, showBoxes: action.on };
    case 'align':
      return { ...state, alignBlocks: action.on };
    case 'shifts':
      return { ...state, showShifts: action.on };
    case 'style-only':
      return { ...state, showStyleOnly: action.on };
    case 'viewport': {
      const next = { ...state, viewport: action.viewport, measured: true };
      // The first real measurement of the window fits the sheet; later ones keep what the reader has done.
      return state.measured ? next : { ...next, view: fitView(context.raster, paneOf(next, context)) };
    }
    case 'fit':
      return { ...state, view: fitView(context.raster, paneOf(state, context)) };
    case 'pan':
      return { ...state, view: { ...state.view, offsetX: state.view.offsetX + action.dx, offsetY: state.view.offsetY + action.dy } };
    case 'zoom': {
      const pane = paneOf(state, context);
      const anchor = action.anchor ?? { x: pane.width / 2, y: pane.height / 2 };
      return { ...state, view: zoomAt(state.view, action.factor, anchor, context.raster, pane) };
    }
    case 'select':
      return focusOn(state, context, action.index);
    case 'pick':
      return { ...state, selected: differenceAt(context.differences, filterOf(state), context.dpi, action.point) };
    case 'focus-box':
      return { ...state, selected: null, view: focusBox(boxToSheet(action.box, context.dpi), context.raster, paneOf(state, context)) };
    case 'step':
      return focusOn(state, context, stepDifference(context.differences, filterOf(state), state.selected, action.direction));
  }
}

/** The window of one pane: the whole viewport, or half of it in «Рядом». */
export function paneOf(state: ViewerState, context: ViewerContext): Viewport {
  return state.mode === 'side'
    ? { width: Math.floor(state.viewport.width / paneCount(context)), height: state.viewport.height }
    : state.viewport;
}

/** How many panes «Рядом» shows: a sheet that exists in one version only has one. */
export function paneCount(context: ViewerContext): number {
  return Math.max(1, Number(context.hasA) + Number(context.hasB));
}
