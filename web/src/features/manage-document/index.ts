/** Public API of the `manage-document` feature: archive, restore and rename one document (`R-151a`). */

export type { DocumentAddress } from './model/use-manage-document';
export {
  cleanTag, tagProblem, titleProblem, useRenameDocument, useSetDocumentArchived, useSetDocumentTags,
} from './model/use-manage-document';
export type { DocumentLifecycleProps, DocumentLifecycleViewProps } from './ui/document-lifecycle';
export { DocumentLifecycle, DocumentLifecycleView } from './ui/document-lifecycle';
export type { DocumentTagsProps, DocumentTagsViewProps } from './ui/document-tags';
export { DocumentTags, DocumentTagsView } from './ui/document-tags';
