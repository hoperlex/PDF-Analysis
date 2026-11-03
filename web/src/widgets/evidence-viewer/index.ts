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
