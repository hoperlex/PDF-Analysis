/** Public API of the `norms` entity: the normative corpus as the «Нормы» screens read it. */

export {
  NORM_EVENT_PAGE_LIMIT, NORM_PARAGRAPH_PAGE_LIMIT, NORM_SEARCH_PAGE_LIMIT, NORM_SNAPSHOT_LIMIT,
  normDocumentQueryOptions, normParagraphsQueryOptions, normSearchQueryOptions,
  normSnapshotEventsQueryOptions, normSnapshotsQueryOptions,
  useNormContent, useNormDocument, useNormParagraphs, useNormSearch, useNormSnapshotEvents,
  useNormSnapshots,
} from './api/use-norms';
export type { NormContent } from './api/use-norms';
export { NO_CURRENT_SNAPSHOT_DETAIL, normFailure } from './model/failure';
export type { NormFailure, NormFailureKind } from './model/failure';
export {
  attributionLabel, buildStateLabel, clauseLabel, currentSnapshotOf, fragmentParts, isUnreliable,
  looksLikeNormDocumentId, pageFromAddress, wantsNormPdf,
} from './model/presentation';
export type { CurrentSnapshotReading, FragmentPart } from './model/presentation';
