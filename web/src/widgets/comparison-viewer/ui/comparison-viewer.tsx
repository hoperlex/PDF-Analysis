'use client';

/**
 * The sheet viewer of a compared pair (`CMP-VIEWER-01`, plan §1.1): «Наложение» and «Рядом», the «шторка», zoom and pan
 * over the pair's tiles, the layers, the change boxes, «Совмещать блоки», «Отличия: N», the channel strip.
 *
 * The widget takes a **`ComparisonSheetPair` as `getComparisonSheetPair` answers it** (the raw evidence is on that read
 * only) and fetches the tiles itself, through the generated client (`useTileImages`). It is not mounted on a route in this
 * lane; the page that mounts it (`CMP-VC-UI-01`) reads the pair, chooses the neighbouring sheets and passes `navigation`.
 *
 * This file is the island: it keeps the state (`ViewerState`, a reducer with a test), measures the window, and turns the
 * reader's hands into actions -- a drag pans, Ctrl and the wheel zoom about the pointer, a double click fits the sheet,
 * ← and → walk the differences (`onKey`, `version-comparison-viewer.js:575`). Everything it draws is
 * {@link ComparisonViewerView}.
 */

import { useEffect, useMemo, useReducer, useRef, useState } from 'react';
import type { HTMLAttributes, PointerEvent as ReactPointerEvent } from 'react';

import type { ComparisonSheetPair } from '@/shared/api';

import { canShowOverlay, viewerGeometry } from '../model/geometry';
import type { RasterSize } from '../model/pyramid';
import { ZOOM_STEP } from '../model/pyramid';
import { shownKinds, sheetTiles, wantedRequests } from '../model/requests';
import { useTileImages } from '../model/use-tile-images';
import { type ViewerContext, initialState, paneOf, reduce } from '../model/viewer-state';

import { ComparisonViewerView, type ViewerNavigation } from './comparison-viewer-view';

export interface ComparisonViewerProps {
  readonly pair: ComparisonSheetPair;
  /**
   * The raster of the page's pyramid (`raster_width_px`, `raster_height_px` of `getVersionPageProfile`), for a pair that
   * has no canvas of its own: an added or removed sheet, or a pair that was never registered.
   */
  readonly rasterSize?: RasterSize;
  readonly navigation?: ViewerNavigation;
}

const EMPTY_RASTER: RasterSize = { widthPx: 1, heightPx: 1 };

export function ComparisonViewer({ pair, rasterSize, navigation }: ComparisonViewerProps) {
  const geometry = useMemo(() => viewerGeometry(pair, rasterSize), [pair, rasterSize]);
  const context: ViewerContext = useMemo(
    () => ({
      raster: geometry?.raster ?? EMPTY_RASTER,
      dpi: geometry?.dpi ?? 72,
      differences: pair.differences ?? [],
      canOverlay: canShowOverlay(pair),
      hasA: pair.page_a !== undefined,
      hasB: pair.page_b !== undefined,
    }),
    [geometry, pair],
  );
  const [state, dispatch] = useReducer(
    (current: ReturnType<typeof initialState>, action: Parameters<typeof reduce>[1]) => reduce(current, action, context),
    context,
    (initial: ViewerContext) => initialState(initial),
  );

  const stage = useRef<HTMLDivElement | null>(null);
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{ x: number; y: number; startX: number; startY: number; moved: boolean } | null>(null);
  const latest = useRef({ view: null as null | { zoom: number; offsetX: number; offsetY: number } });

  // The window's size: measured once it exists and whenever it changes.
  useEffect(() => {
    const element = stage.current;
    if (element === null || typeof ResizeObserver === 'undefined') return;
    const measure = (): void => {
      const width = element.clientWidth;
      const height = element.clientHeight;
      if (width > 0 && height > 0) dispatch({ type: 'viewport', viewport: { width, height } });
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [geometry]);

  // Ctrl or Cmd with the wheel zoom about the pointer; the wheel alone moves the sheet (Shift: sideways) -- the original's
  // `onWheel` (`version-comparison-zoom.js:103-113`). The listener is not passive because it must stop the page scrolling
  // and the browser zooming.
  useEffect(() => {
    const element = stage.current;
    if (element === null) return;
    const onWheel = (event: WheelEvent): void => {
      event.preventDefault();
      if (event.ctrlKey || event.metaKey) {
        const pane = (element.firstElementChild ?? element).getBoundingClientRect();
        dispatch({
          type: 'zoom',
          factor: event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP,
          anchor: { x: event.clientX - pane.left, y: event.clientY - pane.top },
        });
      } else {
        dispatch({ type: 'pan', dx: -(event.shiftKey ? event.deltaY : event.deltaX), dy: event.shiftKey ? 0 : -event.deltaY });
      }
    };
    element.addEventListener('wheel', onWheel, { passive: false });
    return () => element.removeEventListener('wheel', onWheel);
  }, [geometry]);

  const paneHandlers: HTMLAttributes<HTMLDivElement> = {
    onPointerDown: (event: ReactPointerEvent<HTMLDivElement>) => {
      if (event.button !== 0) return;
      event.currentTarget.setPointerCapture?.(event.pointerId);
      drag.current = { x: event.clientX, y: event.clientY, startX: event.clientX, startY: event.clientY, moved: false };
      setDragging(true);
    },
    onPointerMove: (event: ReactPointerEvent<HTMLDivElement>) => {
      const last = drag.current;
      if (last === null) return;
      if (Math.hypot(event.clientX - last.startX, event.clientY - last.startY) > 4) last.moved = true;
      dispatch({ type: 'pan', dx: event.clientX - last.x, dy: event.clientY - last.y });
      last.x = event.clientX;
      last.y = event.clientY;
    },
    // A press that did not move is a click: it picks the change at that place (`pickChangeAt`).
    onPointerUp: (event: ReactPointerEvent<HTMLDivElement>) => {
      const last = drag.current;
      drag.current = null;
      setDragging(false);
      if (last === null || last.moved) return;
      const rect = event.currentTarget.getBoundingClientRect();
      const view = latest.current.view;
      if (view === null) return;
      dispatch({ type: 'pick', point: { x: (event.clientX - rect.left - view.offsetX) / view.zoom, y: (event.clientY - rect.top - view.offsetY) / view.zoom } });
    },
    onPointerCancel: () => {
      drag.current = null;
      setDragging(false);
    },
    onDoubleClick: () => dispatch({ type: 'fit' }),
    onKeyDown: (event) => {
      if (event.key === 'ArrowLeft') dispatch({ type: 'step', direction: -1 });
      if (event.key === 'ArrowRight') dispatch({ type: 'step', direction: 1 });
    },
  };

  latest.current.view = state.view;
  const pane = paneOf(state, context);
  const sheets = useMemo(
    () => (geometry === null ? [] : shownKinds(state, context).map((kind) => sheetTiles(kind, state, geometry.levels, pane))),
    [geometry, state, context, pane],
  );
  const wanted = useMemo(() => wantedRequests(sheets), [sheets]);
  const tiles = useTileImages(pair.sheet_pair_id, wanted);

  return (
    <ComparisonViewerView
      pair={pair}
      geometry={geometry}
      context={context}
      state={state}
      tiles={tiles}
      dispatch={dispatch}
      stageRef={stage}
      paneHandlers={paneHandlers}
      dragging={dragging}
      {...(navigation === undefined ? {} : { navigation })}
    />
  );
}
