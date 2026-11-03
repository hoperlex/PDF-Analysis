'use client';

/**
 * One pdf.js document per `blob:` URL, kept across page changes and destroyed with it.
 *
 * The document is opened once and every page of the declared set is read from it, so turning to
 * another cited page is a `getPage`, not another download and another worker. It is destroyed
 * when the URL changes or the viewer unmounts, which also stops its worker; a destroy that
 * overtakes a load cancels the load.
 *
 * The state carries the URL it belongs to. Without that, the render right after a URL change
 * would still see the PREVIOUS document as ready, for the one pass before the effect resets it,
 * and draw page 3 of the old file into the new file's pane.
 */

import { useCallback, useEffect, useState } from 'react';
import type { PDFDocumentLoadingTask, PDFDocumentProxy } from 'pdfjs-dist';

import { loadPdfJs } from './pdfjs-runtime';

export type PdfDocumentState =
  | { readonly status: 'loading' }
  | { readonly status: 'ready'; readonly document: PDFDocumentProxy; readonly pages: number }
  | { readonly status: 'failed'; readonly cause: unknown };

type Held = { readonly url: string; readonly attempt: number; readonly state: PdfDocumentState };

export function usePdfDocument(url: string): {
  readonly state: PdfDocumentState;
  readonly retry: () => void;
} {
  const [attempt, setAttempt] = useState(0);
  const [held, setHeld] = useState<Held | null>(null);

  useEffect(() => {
    let cancelled = false;
    let task: PDFDocumentLoadingTask | null = null;

    void (async () => {
      const pdfjs = await loadPdfJs();
      if (cancelled) return;
      // pdf.js 6 has no `isEvalSupported` option: the code path that compiled PDF functions with
      // `new Function` is gone from both bundles (`grep -c "new Function("` and `grep -c "eval("`
      // are 0 in `build/pdf.mjs` and `build/pdf.worker.mjs`), so there is nothing to switch off
      // and the page needs no `unsafe-eval`.
      task = pdfjs.getDocument({ url });
      const document = await task.promise;
      if (cancelled) return;
      setHeld({ url, attempt, state: { status: 'ready', document, pages: document.numPages } });
    })().catch((cause: unknown) => {
      if (cancelled) return;
      console.error('page viewer: the document could not be opened', cause);
      setHeld({ url, attempt, state: { status: 'failed', cause } });
    });

    return () => {
      cancelled = true;
      // Destroys the loaded document and its worker too; harmless if it never started.
      void (task as PDFDocumentLoadingTask | null)?.destroy();
    };
  }, [url, attempt]);

  const retry = useCallback(() => {
    setHeld(null);
    setAttempt((value) => value + 1);
  }, []);

  const state: PdfDocumentState =
    held !== null && held.url === url && held.attempt === attempt ? held.state : { status: 'loading' };
  return { state, retry };
}
