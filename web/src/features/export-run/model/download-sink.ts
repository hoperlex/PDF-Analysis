/**
 * Handing a downloaded blob to the browser, behind an interface.
 *
 * The three browser calls involved — `createObjectURL`, a synthetic anchor click, and
 * `revokeObjectURL` — are the only part of the export path that cannot run outside a DOM.
 * Putting them behind this interface keeps the part that matters (which run is exported,
 * what the file is called, and that the URL is always revoked) testable in the `node`
 * environment `A5` pinned for vitest, with no `jsdom` and no testing-library — neither is
 * a dependency of this project and `B8` may not add one.
 *
 * Nothing here builds a CSV. `CSV_COLUMNS` describes what the server will send; the seam
 * is explicit that the browser never builds a CSV from cached data, and the export
 * endpoint is synchronous, so there is no export resource and nothing to poll.
 */

export interface DownloadSink {
  createObjectUrl(blob: Blob): string;
  saveAs(url: string, fileName: string): void;
  revokeObjectUrl(url: string): void;
}

/**
 * Deliver a blob as a file download, revoking the object URL whatever happens.
 *
 * The `finally` is not defensive noise: an object URL that is not revoked pins the whole
 * CSV in memory for the lifetime of the document, and the throw it would leak on is
 * exactly the case where nobody is around to clean up.
 */
export function deliverDownload(sink: DownloadSink, blob: Blob, fileName: string): void {
  const url = sink.createObjectUrl(blob);
  try {
    sink.saveAs(url, fileName);
  } finally {
    sink.revokeObjectUrl(url);
  }
}

/**
 * The real browser sink.
 *
 * Built lazily and only when an export is actually requested, so that importing this
 * module during a server render or a unit test touches no DOM global.
 */
export function browserDownloadSink(): DownloadSink {
  return {
    createObjectUrl: (blob) => URL.createObjectURL(blob),
    saveAs: (url, fileName) => {
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = fileName;
      anchor.rel = 'noopener';
      // Appended before clicking: a detached anchor's click is ignored in some browsers.
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
    },
    revokeObjectUrl: (url) => {
      URL.revokeObjectURL(url);
    },
  };
}
