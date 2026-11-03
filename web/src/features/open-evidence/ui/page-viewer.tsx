'use client';

/** @jsxRuntime automatic */

/**
 * One page of a PDF, drawn by pdf.js as an image in a viewport the reader can move, with the
 * places a finding points to highlighted and framed.
 *
 * Why this replaced the browser's own PDF reader (`OD-09`, taken 2026-10-22, and the owner's
 * instruction of 2026-11-02): that reader brings a toolbar and a thumbnail pane, fits the WHOLE
 * document to its widest sheet, ignores `view=Fit`, shows a blank box when only the fragment of
 * a live `<object>` changes, and has no way to mark a quotation.
 *
 * What this guarantees, and how:
 *
 *   ONE PAGE      only the page asked for is read or drawn; the document is opened once per URL
 *                 and destroyed with the viewer (`use-pdf-document.ts`).
 *   OPENS ON IT   the page is read and its targets placed BEFORE it is drawn, so the first
 *                 picture is already zoomed on the target (`use-page-content.ts`, `targets.ts`).
 *   NEVER BLANK   the next page is drawn into an off-screen canvas and copied over the visible
 *                 one in a single step; while it is read, the old page stays, dimmed. Loading,
 *                 a failed document, a failed page and a page past the end each stand in the
 *                 viewport as a state with its own sentence.
 *   NO STALE WORK a page change, a new zoom or a resize cancels the render still in flight, and
 *                 a result for an older request is dropped.
 *   SHARP         the CSS transform gives instant zoom; once the zoom has settled the canvas is
 *                 drawn again at the size it is shown at, times the device pixel ratio, within
 *                 the bitmap budget (`page-geometry.ts`).
 *   NO GUESSING   a target nothing could place is drawn nowhere and reported as not found
 *                 through `onResolved`; the card beside the page says so.
 *
 * Wheel: only ctrl (or ⌘) + wheel is taken, which is also how a trackpad pinch arrives; a plain
 * wheel is left to scroll the screen. The wheel listener is attached by hand because React's is
 * passive and a passive listener cannot stop the browser zooming the whole page instead.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { KeyboardEvent, PointerEvent as ReactPointerEvent, MouseEvent as ReactMouseEvent } from 'react';
import type { RenderTask } from 'pdfjs-dist';

import { ErrorState, LoadingState } from '@/shared/ui';

import { bitmapScale } from '../model/page-geometry';
import type { Placement, TargetResolution, ViewerTarget } from '../model/targets';
import { resolutionsOf } from '../model/targets';
import type { PageContent } from '../model/use-page-content';
import { targetsKey, usePageContent } from '../model/use-page-content';
import { useElementSize } from '../model/use-element-size';
import { usePdfDocument } from '../model/use-pdf-document';
import type { Point, Size, Stage, View } from '../model/view-state';
import {
  clampView,
  doubleClickView,
  fitView,
  focusView,
  keyView,
  makeStage,
  openingView,
  panBy,
  pinchView,
  stepZoom,
  viewportCentre,
  wheelFactor,
  zoomAt,
} from '../model/view-state';
import type { ViewerState } from './page-viewer-view';
import { PageViewerView } from './page-viewer-view';

export interface PageViewerProps {
  /** `blob:` URL of the fetched PDF. */
  readonly documentUrl: string;
  /** The physical page, counted from 1. */
  readonly pageNumber: number;
  readonly targets: readonly ViewerTarget[];
  /** The target the viewer is on, or null for the first one that was placed. */
  readonly activeTargetId: string | null;
  readonly onTargetSelect?: ((id: string) => void) | undefined;
  /**
   * Called with how each target was placed. First with an EMPTY map whenever the page or the
   * targets change (nothing is known yet), then with the outcome once the page has been read.
   */
  readonly onResolved?: ((results: ReadonlyMap<string, TargetResolution>) => void) | undefined;
  /** What the page is, for assistive technology: «Страница 7 проверяемого документа». */
  readonly label: string;
}

/** The zoom is drawn again at its new size after it has been still this long. */
const SETTLE_MS = 240;
/** A press has to move this far before it is a drag, so a click on a frame stays a click. */
const DRAG_THRESHOLD = 4;
/** A bitmap is drawn again only when the wanted scale moved by more than this factor. */
const REDRAW_STEP = 1.1;

const NOTHING_YET: ReadonlyMap<string, TargetResolution> = new Map();

type Shown = { readonly url: string; readonly content: PageContent };

type Gesture =
  | { kind: 'pan'; id: number; from: Point; origin: View; captured: boolean }
  | { kind: 'pinch'; start: { view: View; a: Point; b: Point }; ids: [number, number] };

/** The target a move should go to: the one asked for, else the first that was placed. */
function chooseTarget(placements: readonly Placement[], id: string | null): Placement | null {
  const located = placements.filter((placed) => placed.groups.length > 0);
  if (id === null) return located[0] ?? null;
  return located.find((placed) => placed.target.id === id) ?? null;
}

/** Zoomed on the active target, else the first, else the page opened the way a reader starts it. */
function initialView(placements: readonly Placement[], stage: Stage, activeTargetId: string | null): View {
  const chosen = chooseTarget(placements, activeTargetId) ?? chooseTarget(placements, null);
  const group = chosen?.groups[0];
  return group === undefined ? openingView(stage) : focusView(group.hull, stage);
}

function problemOf(
  state: ViewerState,
  failure: {
    readonly kind: 'document' | 'page' | 'draw' | 'missing' | null;
    readonly retry: () => void;
  },
  pageNumber: number,
) {
  if (failure.kind === 'missing') {
    return (
      <ErrorState
        title="Страницу не удалось показать"
        detail={<p>В документе нет страницы {pageNumber}. Цитата рядом с панелью остаётся свидетельством.</p>}
      />
    );
  }
  if (failure.kind !== null) {
    return (
      <ErrorState
        title="Страницу не удалось показать"
        detail={
          <p>
            Браузер не смог открыть или нарисовать страницу. Цитата рядом с панелью остаётся
            свидетельством; сама страница нужна как контекст.
          </p>
        }
        onRetry={failure.retry}
      />
    );
  }
  return state === 'loading' ? <LoadingState what="страницу документа" /> : null;
}

export function PageViewer({
  documentUrl,
  pageNumber,
  targets,
  activeTargetId,
  onTargetSelect,
  onResolved,
  label,
}: PageViewerProps) {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const viewportSize = useElementSize(viewportRef);

  const document_ = usePdfDocument(documentUrl);
  const content = usePageContent(
    document_.state.status === 'ready' ? document_.state.document : null,
    pageNumber,
    targets,
  );

  const [shown, setShown] = useState<Shown | null>(null);
  const [view, setView] = useState<View | null>(null);
  const [settled, setSettled] = useState(1);
  const [animate, setAnimate] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [pulse, setPulse] = useState(0);
  const [drawFailed, setDrawFailed] = useState(false);
  const [drawAttempt, setDrawAttempt] = useState(0);

  // ------------------------------------------------------------- what is on the screen
  const current = shown !== null && shown.url === documentUrl ? shown.content : null;
  const ready = content.state.status === 'ready' ? content.state.content : null;
  const pending = ready !== null && ready !== current ? ready : null;
  const stage = useMemo(
    () => (current === null || viewportSize === null ? null : makeStage(current.size, viewportSize)),
    [current, viewportSize],
  );

  // The view a page opens with, worked out before it is drawn: the bitmap is drawn at the zoom
  // it will be SHOWN at, so the first picture is sharp and not a stretched thumbnail.
  const plan = useMemo(() => {
    if (pending === null || viewportSize === null) return null;
    const planned = makeStage(pending.size, viewportSize);
    if (planned === null) return null;
    return { stage: planned, view: initialView(pending.placements, planned, activeTargetId) };
  }, [pending, viewportSize, activeTargetId]);

  // Handlers read the latest of these without being rebuilt on every pointer move.
  const live = useRef({ stage, view, placements: current?.placements ?? [] as readonly Placement[], plan });
  live.current = { stage, view, placements: current?.placements ?? [], plan };

  // --------------------------------------------------------------- moving the view
  const settleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const apply = useCallback((next: View, animated: boolean) => {
    live.current = { ...live.current, view: next };
    setView(next);
    setAnimate(animated);
    if (settleTimer.current !== null) clearTimeout(settleTimer.current);
    settleTimer.current = setTimeout(() => {
      setSettled(next.zoom);
    }, SETTLE_MS);
  }, []);
  useEffect(
    () => () => {
      if (settleTimer.current !== null) clearTimeout(settleTimer.current);
    },
    [],
  );

  const focusOn = useCallback(
    (id: string | null) => {
      const { stage: at, placements } = live.current;
      const chosen = chooseTarget(placements, id);
      const group = chosen?.groups[0];
      if (at === null || group === undefined) return;
      apply(focusView(group.hull, at), true);
      setPulse((value) => value + 1);
    },
    [apply],
  );

  // A card was chosen (or the active target otherwise changed): go there. The first value is
  // not a change; the page opens on it by itself.
  const lastActive = useRef(activeTargetId);
  useEffect(() => {
    if (lastActive.current === activeTargetId) return;
    lastActive.current = activeTargetId;
    focusOn(activeTargetId);
  }, [activeTargetId, focusOn]);

  // The pane changed size, and the fit changed with it. A page the reader has not touched is
  // opened again for the new size; one they have moved keeps the spot of the page that is in the
  // middle of the pane.
  const fittedTo = useRef<Stage | null>(null);
  const touched = useRef(false);
  useEffect(() => {
    if (stage === null) return;
    const before = fittedTo.current;
    fittedTo.current = stage;
    const held = live.current.view;
    if (before === null || held === null) return;
    const same = (left: Size, right: Size) => left.width === right.width && left.height === right.height;
    if (same(before.viewport, stage.viewport) && same(before.page, stage.page)) return;
    if (!touched.current) {
      apply(initialView(live.current.placements, stage, activeTargetId), false);
      return;
    }
    const was = before.fit * held.zoom;
    const now = stage.fit * held.zoom;
    const middle = {
      x: (before.viewport.width / 2 - held.x) / was,
      y: (before.viewport.height / 2 - held.y) / was,
    };
    apply(
      clampView(
        {
          zoom: held.zoom,
          x: stage.viewport.width / 2 - middle.x * now,
          y: stage.viewport.height / 2 - middle.y * now,
        },
        stage,
      ),
      false,
    );
    // The pane's size is the only reason to come here; the rest is read from `live`.
  }, [stage, activeTargetId, apply]);

  // ------------------------------------------------------------------ drawing the page
  const dpr = typeof window === 'undefined' ? 1 : window.devicePixelRatio || 1;
  const drawn = pending ?? current;
  const wanted =
    pending !== null ? (plan === null ? null : plan.stage.fit * plan.view.zoom) : stage === null ? null : stage.fit * settled;
  const scale =
    drawn === null || wanted === null
      ? null
      : bitmapScale(wanted * dpr, drawn.size.width, drawn.size.height);
  const scaleStep = scale === null ? null : Math.round(Math.log(scale) / Math.log(REDRAW_STEP));

  useEffect(() => {
    if (drawn === null || scale === null) return;
    let cancelled = false;
    let task: RenderTask | null = null;
    setDrawFailed(false);

    void (async () => {
      const viewport = drawn.page.getViewport({ scale });
      const buffer = window.document.createElement('canvas');
      buffer.width = Math.max(1, Math.ceil(viewport.width));
      buffer.height = Math.max(1, Math.ceil(viewport.height));
      task = drawn.page.render({ canvas: buffer, viewport });
      await task.promise;
      if (cancelled) return;

      const visible = canvasRef.current;
      const context = visible?.getContext('2d') ?? null;
      if (visible === null || context === null) throw new Error('the page canvas is not available');
      // Resizing a canvas clears it, so the copy follows in the same task: no frame is painted
      // between the old bitmap and the new one.
      visible.width = buffer.width;
      visible.height = buffer.height;
      context.drawImage(buffer, 0, 0);
      buffer.width = 0;
      buffer.height = 0;

      const opening = live.current.plan;
      if (drawn !== current && opening !== null) {
        touched.current = false;
        fittedTo.current = opening.stage;
        live.current = { ...live.current, view: opening.view };
        setShown({ url: documentUrl, content: drawn });
        setView(opening.view);
        setSettled(opening.view.zoom);
        setAnimate(false);
      }
    })().catch((cause: unknown) => {
      if (cancelled) return;
      if ((cause as { name?: unknown } | null)?.name === 'RenderingCancelledException') return;
      console.error('page viewer: the page could not be drawn', cause);
      setDrawFailed(true);
    });

    return () => {
      cancelled = true;
      task?.cancel();
    };
    // The page, the bitmap size it is wanted at, and a retry are the only reasons to draw again.
  }, [drawn, scaleStep, drawAttempt]);

  // ----------------------------------------------------------- telling the owner
  const onResolvedRef = useRef(onResolved);
  onResolvedRef.current = onResolved;
  const requestKey = `${documentUrl}\u0000${pageNumber}\u0000${targetsKey(targets)}`;
  useEffect(() => {
    onResolvedRef.current?.(NOTHING_YET);
  }, [requestKey]);
  useEffect(() => {
    if (content.state.status === 'ready') {
      onResolvedRef.current?.(resolutionsOf(content.state.content.placements));
    }
  }, [content.state]);

  // ------------------------------------------------------------------ the pointer
  const local = useCallback((event: { clientX: number; clientY: number }): Point => {
    const element = viewportRef.current;
    if (element === null) return { x: 0, y: 0 };
    const box = element.getBoundingClientRect();
    return { x: event.clientX - box.left - element.clientLeft, y: event.clientY - box.top - element.clientTop };
  }, []);

  const pointers = useRef(new Map<number, Point>());
  const gesture = useRef<Gesture | null>(null);

  const beginPan = (id: number, from: Point, captured: boolean) => {
    const held = live.current.view;
    gesture.current = held === null ? null : { kind: 'pan', id, from, origin: held, captured };
  };

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (live.current.view === null || live.current.stage === null) return;
    const point = local(event);
    pointers.current.set(event.pointerId, point);
    if (pointers.current.size === 1) {
      beginPan(event.pointerId, point, false);
      return;
    }
    if (pointers.current.size === 2) {
      const [first, second] = [...pointers.current.entries()] as [[number, Point], [number, Point]];
      gesture.current = {
        kind: 'pinch',
        start: { view: live.current.view, a: first[1], b: second[1] },
        ids: [first[0], second[0]],
      };
      for (const [id] of [first, second]) event.currentTarget.setPointerCapture(id);
      setDragging(true);
    }
  };

  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!pointers.current.has(event.pointerId)) return;
    const point = local(event);
    pointers.current.set(event.pointerId, point);
    const active = gesture.current;
    const at = live.current.stage;
    if (active === null || at === null) return;
    if (active.kind === 'pan') {
      if (event.pointerId !== active.id) return;
      const dx = point.x - active.from.x;
      const dy = point.y - active.from.y;
      if (!active.captured) {
        if (Math.hypot(dx, dy) < DRAG_THRESHOLD) return;
        // Captured only once it is a drag: a captured press would send its click to the
        // viewport and a frame could never be clicked.
        event.currentTarget.setPointerCapture(event.pointerId);
        active.captured = true;
        setDragging(true);
      }
      touched.current = true;
      apply(panBy(active.origin, dx, dy, at), false);
      return;
    }
    const [first, second] = active.ids;
    const a = pointers.current.get(first);
    const b = pointers.current.get(second);
    if (a === undefined || b === undefined) return;
    touched.current = true;
    apply(pinchView(active.start, { a, b }, at), false);
  };

  const onPointerEnd = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!pointers.current.delete(event.pointerId)) return;
    const remaining = [...pointers.current.entries()];
    const first = remaining[0];
    if (first === undefined) {
      gesture.current = null;
      setDragging(false);
    } else if (gesture.current?.kind === 'pinch') {
      // One finger of two lifted: the other carries on as a drag from where it is.
      beginPan(first[0], first[1], true);
    }
  };

  const onDoubleClick = (event: ReactMouseEvent<HTMLDivElement>) => {
    const { stage: at, view: held } = live.current;
    if (at === null || held === null) return;
    touched.current = true;
    apply(doubleClickView(held, local(event), at), true);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const { stage: at, view: held } = live.current;
    if (at === null || held === null) return;
    const next = keyView(held, event, at);
    if (next === null) return;
    event.preventDefault();
    touched.current = true;
    apply(next, !event.key.startsWith('Arrow'));
  };

  // Ctrl (or ⌘) + wheel, and so a trackpad pinch. Attached by hand to be non-passive.
  useEffect(() => {
    const element = viewportRef.current;
    if (element === null) return;
    const onWheel = (event: WheelEvent) => {
      if (!event.ctrlKey && !event.metaKey) return;
      const { stage: at, view: held } = live.current;
      if (at === null || held === null) return;
      event.preventDefault();
      touched.current = true;
      apply(zoomAt(held, held.zoom * wheelFactor(event.deltaY, event.deltaMode), local(event), at), false);
    };
    element.addEventListener('wheel', onWheel, { passive: false });
    return () => {
      element.removeEventListener('wheel', onWheel);
    };
  }, [apply, local]);

  // ------------------------------------------------------------------- the controls
  const zoomBy = (direction: 1 | -1) => {
    const { stage: at, view: held } = live.current;
    if (at === null || held === null) return;
    touched.current = true;
    apply(stepZoom(held, direction, viewportCentre(at), at), true);
  };
  const fit = () => {
    const { stage: at } = live.current;
    if (at === null) return;
    touched.current = true;
    apply(fitView(at), true);
  };

  // --------------------------------------------------------------------- the state
  const failure: { kind: 'document' | 'page' | 'draw' | 'missing' | null; retry: () => void } =
    document_.state.status === 'failed'
      ? { kind: 'document', retry: document_.retry }
      : content.state.status === 'missing'
        ? { kind: 'missing', retry: content.retry }
        : content.state.status === 'failed'
          ? { kind: 'page', retry: content.retry }
          : drawFailed
            ? {
                kind: 'draw',
                retry: () => {
                  setDrawFailed(false);
                  setDrawAttempt((value) => value + 1);
                },
              }
            : { kind: null, retry: content.retry };

  const state: ViewerState =
    failure.kind !== null
      ? 'failed'
      : current === null
        ? 'loading'
        : pending !== null || content.state.status === 'loading'
          ? 'rendering'
          : 'ready';

  return (
    <PageViewerView
      label={label}
      state={state}
      documentUrl={documentUrl}
      pageNumber={pageNumber}
      pageCount={document_.state.status === 'ready' ? document_.state.pages : null}
      stage={stage}
      view={view}
      placements={current?.placements ?? []}
      activeTargetId={activeTargetId}
      pulse={pulse}
      animate={animate}
      dragging={dragging}
      overlay={problemOf(state, failure, pageNumber)}
      onTargetSelect={onTargetSelect}
      onZoomOut={() => {
        zoomBy(-1);
      }}
      onZoomIn={() => {
        zoomBy(1);
      }}
      onFit={fit}
      onFocus={() => {
        focusOn(activeTargetId ?? null);
      }}
      viewportRef={viewportRef}
      canvasRef={canvasRef}
      viewportHandlers={{
        onPointerDown,
        onPointerMove,
        onPointerUp: onPointerEnd,
        onPointerCancel: onPointerEnd,
        onDoubleClick,
        onKeyDown,
      }}
    />
  );
}
