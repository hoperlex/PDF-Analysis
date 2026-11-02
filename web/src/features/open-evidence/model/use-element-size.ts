'use client';

/**
 * The content box of an element, measured and followed.
 *
 * The first measurement is taken at once, because the first draw waits for it; later changes
 * are applied after the element has stopped resizing for `SETTLE_MS`, because every new size
 * re-fits the page and a window being dragged would otherwise re-fit it sixty times a second.
 * Null until the element has a real size (a pane that is collapsed or not yet laid out).
 */

import { useEffect, useRef, useState } from 'react';
import type { RefObject } from 'react';

import type { Size } from './view-state';

const SETTLE_MS = 120;

export function useElementSize(ref: RefObject<HTMLElement | null>): Size | null {
  const [size, setSize] = useState<Size | null>(null);
  const measured = useRef(false);

  useEffect(() => {
    const element = ref.current;
    if (element === null) return;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const apply = (width: number, height: number) => {
      const next = { width: Math.floor(width), height: Math.floor(height) };
      if (!(next.width > 0 && next.height > 0)) return;
      setSize((current) =>
        current !== null && current.width === next.width && current.height === next.height ? current : next,
      );
    };
    const observer = new ResizeObserver((entries) => {
      const entry = entries[entries.length - 1];
      if (entry === undefined) return;
      const { width, height } = entry.contentRect;
      if (!measured.current) {
        measured.current = true;
        apply(width, height);
        return;
      }
      if (timer !== null) clearTimeout(timer);
      timer = setTimeout(() => {
        apply(width, height);
      }, SETTLE_MS);
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
      if (timer !== null) clearTimeout(timer);
    };
  }, [ref]);

  return size;
}
