/** Public API of the `section-specification` entity (`W63-SECTION-FORM7-01`). */

export type { SectionSpecificationRequest } from './api/use-section-specification';
export {
  SECTION_ROW_LIMIT,
  sectionSpecificationQueryOptions,
  useSectionSpecification,
} from './api/use-section-specification';
export {
  SECTION_EXCLUSION_LABELS,
  SECTION_LIMIT_MESSAGES,
  SECTION_PRICE_STATE_MESSAGES,
  SECTION_ROW_STATUS_LABELS,
  SECTION_SOURCE_STATE_MESSAGES,
  SECTION_UNKNOWN_LABEL,
  sectionExclusionLabel,
  sectionLimitMessage,
  sectionPriceStateMessage,
  sectionRowStatusLabel,
  sectionSourceStateMessage,
  stageMark,
} from './model/presentation';
