/**
 * Public API of the `document-version` entity: the PC-01 input envelope, the pre-check a
 * browser can honestly make, the classification of every upload failure, and the
 * read-only panel for a published version.
 */

export type { ChosenFile, UploadPrecheckProblem } from './model/upload-envelope';
export {
  PC01_UPLOAD_ENVELOPE,
  UPLOAD_ENVELOPE_RULES,
  formatBytes,
  precheckProblemMessage,
  precheckUploadFile,
} from './model/upload-envelope';

export type { UploadFailure, UploadFailureKind } from './model/upload-failure';
export { classifyUploadFailure } from './model/upload-failure';

export { useDocumentVersion } from './api/use-document-version';

export type { VersionPanelProps } from './ui/version-panel';
export { VersionPanel } from './ui/version-panel';
