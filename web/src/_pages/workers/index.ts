/** Public API of the `workers` page slice. */

export { WorkersPage } from './ui/workers-page';
export type { WorkersPageProps } from './ui/workers-page';
export { WorkersAdvancedPage } from './ui/workers-advanced-page';
export type { WorkersAdvancedPageProps } from './ui/workers-advanced-page';
export { DEFAULT_WORKERS_TAB, WORKERS_TABS, WORKERS_TAB_LABELS, WORKERS_TAB_PARAM, isWorkersTab, tabAfterKey } from './model/tabs';
export type { WorkersTab } from './model/tabs';
export {
  ADVANCED_LINK_LABEL, ADVANCED_SECTIONS, ADVANCED_SECTION_LABELS, WORKERS_ADVANCED_ADDRESS, isAdvancedSection,
  legacyAdvancedTab,
} from './model/advanced';
export type { AdvancedSection } from './model/advanced';
