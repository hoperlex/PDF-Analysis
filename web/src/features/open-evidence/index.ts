/**
 * Public API of the `open-evidence` feature: fetch a version's PDF bytes for the viewer
 * and address one page of them.
 */

export { objectUrlOf, pdfPageUrl } from './model/page-url';

export type { EvidenceDocument } from './model/use-evidence-document';
export { useEvidenceDocument } from './model/use-evidence-document';
