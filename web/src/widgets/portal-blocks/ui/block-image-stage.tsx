'use client';

/**
 * The block's crop in the block view: the wheel zooms it from the whole image to twelve times around
 * the pointer, a drag moves it once it is larger than the stage, a double click puts it back.
 *
 * The arithmetic is `entities/block`'s pure model (`image-view.ts`); this component only reads the
 * events and the stage's size. The stage's size is read when an event arrives, not tracked: a window
 * resized while the image is zoomed leaves the view where it was until the next gesture, which holds
 * it inside the new stage.
 *
 * The wheel listener is attached by hand because React's is passive and a passive listener cannot
 * stop the page behind the dialog from scrolling. The view is kept in a ref beside the state so that
 * several wheel events in one frame compose instead of each starting from the same render.
 *
 * A failed image says so in words, as everywhere on this screen; nothing retries behind the reader.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';

import {
  WHOLE_IMAGE,
  isZoomed,
  panBy,
  viewTransform,
  wheelZoom,
  zoomLabel,
} from '@/entities/block';
import type { View } from '@/entities/block';

import styles from './portal-block-viewer.module.css';

/**
 * What stands where the image failed to load. Exported so the instruments that render one static pass
 * (the contrast census) can draw it: only a browser's `error` event selects it.
 */
export function BlockImageFailure() {
  return (
    <p className={styles.stageFailed} role="status" data-block-image="failed">
      Изображение не удалось загрузить.
    </p>
  );
}

export interface BlockImageStageProps {
  readonly src: string;
  readonly alt: string;
}

interface Drag {
  readonly pointerId: number;
  readonly fromX: number;
  readonly fromY: number;
  readonly origin: View;
}

export function BlockImageStage({ src, alt }: BlockImageStageProps) {
  const stage = useRef<HTMLDivElement | null>(null);
  const live = useRef<View>(WHOLE_IMAGE);
  const drag = useRef<Drag | null>(null);
  const [view, setViewState] = useState<View>(WHOLE_IMAGE);
  const [dragging, setDragging] = useState(false);
  const [failed, setFailed] = useState(false);

  const setView = useCallback((next: View) => {
    live.current = next;
    setViewState(next);
  }, []);

  const size = useCallback(() => {
    const box = stage.current?.getBoundingClientRect();
    return { width: box?.width ?? 0, height: box?.height ?? 0 };
  }, []);

  useEffect(() => {
    const element = stage.current;
    if (element === null) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const box = element.getBoundingClientRect();
      const anchor = { x: event.clientX - box.left, y: event.clientY - box.top };
      setView(wheelZoom(live.current, event.deltaY, anchor, { width: box.width, height: box.height }));
    };
    element.addEventListener('wheel', onWheel, { passive: false });
    return () => {
      element.removeEventListener('wheel', onWheel);
    };
  }, [setView, failed]);

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.pointerType === 'mouse' && event.button !== 0) return;
    if (!isZoomed(live.current)) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    drag.current = { pointerId: event.pointerId, fromX: event.clientX, fromY: event.clientY, origin: live.current };
    setDragging(true);
  };
  const onPointerMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    const held = drag.current;
    if (held === null || held.pointerId !== event.pointerId) return;
    setView(panBy(held.origin, event.clientX - held.fromX, event.clientY - held.fromY, size()));
  };
  const onPointerEnd = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (drag.current?.pointerId !== event.pointerId) return;
    drag.current = null;
    setDragging(false);
  };

  if (failed) return <BlockImageFailure />;

  return (
    <div className={styles.stageBox}>
      <div
        ref={stage}
        className={styles.stage}
        data-block-image="shown"
        data-zoomed={isZoomed(view) ? 'true' : 'false'}
        data-dragging={dragging ? 'true' : 'false'}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerEnd}
        onPointerCancel={onPointerEnd}
        onDoubleClick={() => {
          setView(WHOLE_IMAGE);
        }}
      >
        <div className={styles.canvas} style={{ transform: viewTransform(view) }}>
          <img
            className={styles.image}
            src={src}
            alt={alt}
            draggable={false}
            decoding="async"
            onError={() => {
              setFailed(true);
            }}
          />
        </div>
      </div>
      <p className={styles.stageHint}>
        <span className={styles.zoom} data-zoom={view.zoom}>
          {zoomLabel(view)}
        </span>{' '}
        Колесо мыши — масштаб, перетаскивание — сдвиг, двойной щелчок — сброс.
      </p>
    </div>
  );
}
