/** Public API of the `manage-document` feature: archive, restore and rename one document, archive several (`R-151a`, `UIP-S02-04`). */

export type { DocumentAddress } from './model/use-manage-document';
// `UIP-S02-04`: «В архив (N)» over the chosen documents of a section, one keyed command per document.
export type { ArchiveFailure, ArchiveProgress, ArchiveReport, ArchiveSend, ArchiveTarget } from './model/bulk-archive';
export { archiveDocuments, archiveReportLine } from './model/bulk-archive';
export type { UseArchiveDocuments } from './model/use-archive-documents';
export { useArchiveDocuments } from './model/use-archive-documents';
export {
  cleanTag, tagProblem, titleProblem, useRenameDocument, useSetDocumentArchived, useSetDocumentGroup, useSetDocumentTags,
} from './model/use-manage-document';
export type { DocumentLifecycleProps, DocumentLifecycleViewProps } from './ui/document-lifecycle';
export { DocumentLifecycle, DocumentLifecycleView } from './ui/document-lifecycle';
export type { DocumentTagsProps, DocumentTagsViewProps } from './ui/document-tags';
export { DocumentTags, DocumentTagsView } from './ui/document-tags';
