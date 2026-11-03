/**
 * The pdf.js library, loaded when the first page is drawn and never before.
 *
 * `OD-09` (the browser PDF rendering approach) was taken by the owner on 2026-10-22 in
 * favour of pdf.js. The library is large (the main module is ~0.9 MB and the worker ~1.3 MB
 * minified), so it is reached only through a dynamic `import()` made from inside a client
 * effect: the review screen's own bundle does not carry it, the evidence-viewer chunk
 * (`_pages/review/ui/lazy-evidence-viewer.tsx`) does not carry it, and it is requested the
 * first time a reviewer opens a finding's page. Nothing here runs on the server.
 *
 * The worker is addressed with `new URL(..., import.meta.url)`, which the bundler turns into
 * an emitted static asset next to the chunk. That is the one place a build can silently fail
 * to ship it, so `npm run build` is the check for it.
 */

import type * as PdfJs from 'pdfjs-dist';

export type PdfJsModule = typeof PdfJs;

let loading: Promise<PdfJsModule> | null = null;

/** The pdf.js module with its worker configured. One load per page view, shared by every caller. */
export function loadPdfJs(): Promise<PdfJsModule> {
  if (loading === null) {
    loading = import('pdfjs-dist')
      .then((pdfjs) => {
        pdfjs.GlobalWorkerOptions.workerSrc = new URL(
          'pdfjs-dist/build/pdf.worker.min.mjs',
          import.meta.url,
        ).toString();
        return pdfjs;
      })
      .catch((error: unknown) => {
        // A failed load must not be remembered: the next attempt (the retry button) tries again.
        loading = null;
        throw error;
      });
  }
  return loading;
}
