/** Public API of the `section-optimisation` page slice (`R-66`, `UI-B-20`): the page, its header and the address it reads. */

export type { SectionOptimisationAddress } from './model/address';
export {
  DEFAULT_SECTION_OPTIMISATION_ADDRESS,
  objectDecided,
  readDocumentParam,
  readSectionOptimisationAddress,
  sectionOptimisationSearch,
  shownProject,
} from './model/address';
export type { SectionOptimisationTab, SectionOptimisationTabCounts } from './model/tabs';
export { SECTION_OPTIMISATION_TABS, SECTION_OPTIMISATION_TAB_LABELS, sectionOptimisationTabText } from './model/tabs';
export type { SectionOptimisationPageProps } from './ui/section-optimisation-page';
export { SectionOptimisationPage } from './ui/section-optimisation-page';
export type { SectionFilterBarProps } from './ui/section-filter-bar';
export { SectionFilterBar } from './ui/section-filter-bar';
export type { SectionHeaderProps } from './ui/section-header';
export { SECTION_ABOUT_TEXT, SectionHeader, sectionBackTarget, sectionLeadLine } from './ui/section-header';
export type { DocumentFilterOption, DocumentFilterProps } from './ui/document-filter';
export { DocumentFilter, documentFilterOptions, documentOptionLabel, withSelectedDocument } from './ui/document-filter';
