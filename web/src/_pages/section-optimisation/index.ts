/** Public API of the `section-optimisation` page slice (`R-66`, `UI-B-20`): the page and the address it reads. */

export type { SectionOptimisationAddress } from './model/address';
export {
  DEFAULT_SECTION_OPTIMISATION_ADDRESS,
  readSectionOptimisationAddress,
  sectionOptimisationSearch,
} from './model/address';
export type { SectionOptimisationTab, SectionOptimisationTabCounts } from './model/tabs';
export { SECTION_OPTIMISATION_TABS, SECTION_OPTIMISATION_TAB_LABELS, sectionOptimisationTabText } from './model/tabs';
export type { SectionOptimisationPageProps } from './ui/section-optimisation-page';
export { SectionOptimisationPage } from './ui/section-optimisation-page';
export type { ProjectFilterOption, SectionFilterBarProps, SectionMember } from './ui/section-filter-bar';
export { ProjectOptionName, SectionFilterBar, projectFilterOptions } from './ui/section-filter-bar';
