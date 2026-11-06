/** Public API of the `evidence-viewer` widget. */

export type { EvidenceViewerProps } from './ui/evidence-viewer';
export { EvidenceViewer } from './ui/evidence-viewer';

/*
 * The quotation card, exported so the styling census can render the states that only exist after
 * the viewer has read a page: a quotation framed from the line geometry, found in the text, found
 * more than once, and not found. It takes plain data and runs no effect.
 */
export type { QuotationCardProps, QuotationPlacement } from './ui/quotation-card';
export { QuotationCard } from './ui/quotation-card';

/*
 * `UI-A-27` «Просмотр PDF» on the version page: the version's document in a drawer, page by page. `DocumentViewer` reads the bytes
 * and is mounted only through the version page's `next/dynamic` boundary; `DocumentViewerView` is the same markup from plain data,
 * exported so the styling census can render the drawer open.
 */
export type { DocumentViewerProps, DocumentViewerViewProps } from './ui/document-viewer';
export { DocumentViewer, DocumentViewerView } from './ui/document-viewer';
