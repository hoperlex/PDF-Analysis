/**
 * Public API of the `open-evidence` feature: fetch a version's PDF bytes, draw one page of them
 * in a viewer the reader can move, and say where a finding points on it.
 *
 * `pdfPageUrl` and `objectUrlOf` address the browser's own PDF reader by `#page=N`. The review
 * screen no longer uses it (`PageViewer` draws the page); the norm document and the
 * specification panel still do, and are not this feature's to change.
 */

export { objectUrlOf, pdfPageUrl } from './model/page-url';

export type { EvidenceDocument } from './model/use-evidence-document';
export { useEvidenceDocument } from './model/use-evidence-document';

export { useVersionBlockIndex } from './model/use-version-block-index';

export type {
  Region,
  TargetMethod,
  TargetResolution,
  ViewerTarget,
} from './model/targets';
export { lineRects, regionOf, resolutionSentence } from './model/targets';

export type { PageViewerProps } from './ui/page-viewer';
export { PageViewer } from './ui/page-viewer';

/*
 * The viewer as markup, exported so the styling census can render the states that only exist
 * after pdf.js has drawn a page in a browser. It takes plain data and runs no effect.
 */
export type { PageViewerViewProps, ViewerState } from './ui/page-viewer-view';
export { PageViewerView } from './ui/page-viewer-view';
export type { Placement } from './model/targets';
