/**
 * Public API of the `document-version` entity: the PC-01 input envelope (a portal bundle),
 * the pre-check a browser can honestly make, the classification of every upload failure, the
 * read-only panel for a published version, and (`W59-SECTION-UI-01`) the version's
 * expert-confirmed stage and section with the review that offers them.
 */

export type { ChosenFile, UploadPrecheckProblem } from './model/upload-envelope';
export {
  PC01_UPLOAD_ENVELOPE,
  UPLOAD_CONSTRAINTS_STATED,
  UPLOAD_ENVELOPE_RULES,
  formatBytes,
  precheckProblemMessage,
  precheckUploadFile,
  uploadConstraintSentence,
} from './model/upload-envelope';

export type { UploadFailure, UploadFailureKind } from './model/upload-failure';
export { classifyUploadFailure } from './model/upload-failure';

export { looksLikeDocumentUid, looksLikeVersionUid } from './model/address';

export type {
  ClassificationFailure,
  ClassificationFailureKind,
  OrderedSectionOptions,
  ProjectStagePresentation,
  SuggestionEvidence,
  VersionAddress,
} from './model/classification';
export {
  ALREADY_CLASSIFIED_DETAIL,
  CLASSIFY_NOT_PERMITTED_DETAIL,
  PROJECT_STAGES,
  PROJECT_STAGE_LABELS,
  canClassifyVersion,
  classificationFailure,
  orderSectionOptions,
  reviewOptionOf,
  sectionTitleOf,
  stageBadgeText,
  stageChoiceText,
  suggestionEvidence,
} from './model/classification';
export { sectionReviewQueryOptions, useSectionReview } from './api/use-section-review';

export { useDocumentVersion } from './api/use-document-version';
export {
  DOCUMENT_PAGE_LIMIT,
  documentListQueryOptions,
  useDocumentList,
} from './api/use-document-list';
export { VERSION_PAGE_LIMIT, useVersionList } from './api/use-version-list';

export type { VersionRowProps } from './ui/version-row';
export { VersionRow } from './ui/version-row';

export type { VersionPanelProps } from './ui/version-panel';
export { VersionPanel } from './ui/version-panel';

export type { ClassificationBadgesProps } from './ui/classification-badges';
export { ClassificationBadges } from './ui/classification-badges';
