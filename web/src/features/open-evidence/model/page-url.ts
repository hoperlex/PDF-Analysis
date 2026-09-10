/**
 * The URL the PDF island is pointed at.
 *
 * `OD-09` — the browser PDF rendering approach — is **untaken**. `P3-WEB-00` deferred it
 * (`docs/program/tasks/P3-WEB-00.md`, "Deferred decisions") and the seam says so in
 * `web/docs/PC01_UI_SEAM.md` §10: no rendering approach is pinned there. `B8` may not add
 * a dependency, so `pdfjs-dist` and every other renderer is out of reach for this session.
 *
 * What is left is the renderer already present in every target browser, addressed through
 * the PDF Open Parameters fragment — `#page=N`. It costs no dependency, keeps the island
 * bounded to one element, and opens the declared page. Its limits are real and are stated
 * in the viewer: no bounding box, no highlight, page-level navigation only. `P3-WEB-02`
 * already lists all three as non-goals, and the acceptance criterion is the quotation
 * beside the page, which does not depend on the renderer at all.
 *
 * The fragment is **not** a query parameter. `?page=N` would be sent to the server, and
 * the content operation declares no such parameter, so the transport would drop it; a
 * fragment never leaves the browser, which is also why it is safe on an object URL.
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
