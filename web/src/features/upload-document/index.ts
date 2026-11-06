/** Public API of the `upload-document` feature. */

export type { UploadDocumentCommand } from './model/use-upload-document';
export { useUploadDocument } from './model/use-upload-document';
export type { UploadDocumentVersionCommand } from './model/use-upload-document-version';
export { useUploadDocumentVersion } from './model/use-upload-document-version';

export type { UploadDocumentFormProps } from './ui/upload-document-form';
export { UploadDocumentForm } from './ui/upload-document-form';
export type { UploadDocumentVersionFormProps } from './ui/upload-document-version-form';
export { UploadDocumentVersionForm } from './ui/upload-document-version-form';

// `R-151b`: several files, each to its explicit target.
export type { ManyFile, ManyOutcome, UploadTarget } from './model/upload-many';
export { NEW_DOCUMENT, manyFileSignature, sendable, targetOf, targetValue } from './model/upload-many';
export type { UploadManyApi } from './model/use-upload-many';
export { useUploadMany } from './model/use-upload-many';
export type { UploadManyFormProps, UploadManyViewProps, UploadTargetOption } from './ui/upload-many-form';
export { UploadManyForm, UploadManyView } from './ui/upload-many-form';
