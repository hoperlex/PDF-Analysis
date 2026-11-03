/**
 * The URL the browser's own PDF reader is pointed at, addressed by the PDF Open Parameters
 * fragment `#page=N`.
 *
 * The review screen does not use this any more: `PageViewer` draws the cited page with pdf.js
 * (`OD-09`, taken by the owner on 2026-10-22). The norm document and the specification panel
 * still open their pages this way and are not this feature's to change, so the helpers stay.
 *
 * Its limits are the reader's own: no bounding box, no highlight, page-level navigation only, and
 * a toolbar the product cannot hide.
 *
 * The fragment is **not** a query parameter. `?page=N` would be sent to the server, and the
 * content operation declares no such parameter, so the transport would drop it; a fragment never
 * leaves the browser, which is also why it is safe on an object URL.
 */

/**
 * Point a viewer at one page of an already-fetched object URL.
 *
 * The page number is the server's, used as given. It is range-checked by the caller
 * against the observation's declared pages — this function refuses only the values that
 * cannot be a page at all, because emitting `#page=0` or `#page=NaN` produces a viewer
 * that silently falls back to page 1 and shows the reviewer the wrong text.
 */
export function pdfPageUrl(objectUrl: string, page: number): string {
  if (!Number.isInteger(page) || page < 1) {
    throw new RangeError(
      `pdfPageUrl: page must be a positive integer page number, received ${String(page)}.`,
    );
  }
  return `${objectUrl}#page=${page}`;
}

/**
 * The object URL alone, with any fragment removed, for revocation.
 *
 * `URL.revokeObjectURL` is given the URL it was handed by `createObjectURL`; passing the
 * `#page=` form back leaks the blob for the lifetime of the document.
 */
export function objectUrlOf(viewerUrl: string): string {
  const hash = viewerUrl.indexOf('#');
  return hash === -1 ? viewerUrl : viewerUrl.slice(0, hash);
}
