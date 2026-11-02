'use client';

/**
 * One page of an open document, with its targets already placed on it.
 *
 * Reading a page is cheap and drawing it is not, and the viewer needs to know what is on the page
 * (and where the targets are) BEFORE it draws, because it opens the page already focused on the
 * target: the zoom it draws at depends on the answer. So this resolves in two awaits (the page,
 * then its text if some target has no geometry of its own) and hands back the page, its size in
 * points and the placements; drawing is the caller's.
 *
 * Like the document hook, the answer carries the request it answers. A page change shows
 * `loading` at once, never the previous page's content under the new page number.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import type { PDFDocumentProxy, PDFPageProxy } from 'pdfjs-dist';

import type { TextRun } from './locate-quotation';
import type { Placement, TextSnapshot, ViewerTarget } from './targets';
import { placeTargets } from './targets';
import type { Size } from './view-state';

export interface PageContent {
  readonly pageNumber: number;
  readonly page: PDFPageProxy;
  /** The page in points, rotation applied. */
  readonly size: Size;
  readonly placements: readonly Placement[];
}

export type PageContentState =
  | { readonly status: 'loading' }
  | { readonly status: 'missing' }
  | { readonly status: 'failed'; readonly cause: unknown }
  | { readonly status: 'ready'; readonly content: PageContent };

type Held = { readonly key: string; readonly state: PageContentState };

/** A change of this string is a different request: another document, page or set of targets. */
export function targetsKey(targets: readonly ViewerTarget[]): string {
  return JSON.stringify(
    targets.map((target) => [target.id, target.badge, target.quote ?? null, target.rects ?? null, target.region ?? null]),
  );
}

export function usePageContent(
  document: PDFDocumentProxy | null,
  pageNumber: number,
  targets: readonly ViewerTarget[],
): { readonly state: PageContentState; readonly retry: () => void } {
  const [attempt, setAttempt] = useState(0);
  const [held, setHeld] = useState<Held | null>(null);

  // The latest targets, read inside the effect; the effect restarts on their KEY, not on the
  // identity of an array the parent rebuilds on every render.
  const targetsRef = useRef(targets);
  targetsRef.current = targets;
  const key = `${pageNumber}:${attempt}:${targetsKey(targets)}`;

  useEffect(() => {
    if (document === null) return;
    let cancelled = false;

    void (async () => {
      if (!Number.isInteger(pageNumber) || pageNumber < 1 || pageNumber > document.numPages) {
        setHeld({ key, state: { status: 'missing' } });
        return;
      }
      const page = await document.getPage(pageNumber);
      if (cancelled) return;
      // Scale 1 is points; the viewport applies the page's own `/Rotate`.
      const viewport = page.getViewport({ scale: 1 });
      const size = { width: viewport.width, height: viewport.height };
      const placements = await placeTargets(targetsRef.current, size, async (): Promise<TextSnapshot> => {
        const text = await page.getTextContent();
        // Marked-content markers carry no `str`; they are not requested, but are not trusted away.
        const items: TextRun[] = [];
        for (const item of text.items) {
          if ('str' in item) items.push(item);
        }
        return { items, transform: viewport.transform };
      });
      if (cancelled) return;
      setHeld({ key, state: { status: 'ready', content: { pageNumber, page, size, placements } } });
    })().catch((cause: unknown) => {
      if (cancelled) return;
      console.error('page viewer: the page could not be read', cause);
      setHeld({ key, state: { status: 'failed', cause } });
    });

    return () => {
      cancelled = true;
    };
    // `key` carries the page, the attempt and the targets; `document` is the other input.
  }, [document, key, pageNumber]);

  const retry = useCallback(() => {
    setAttempt((value) => value + 1);
  }, []);

  const state: PageContentState =
    document !== null && held !== null && held.key === key ? held.state : { status: 'loading' };
  return { state, retry };
}
