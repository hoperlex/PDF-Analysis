/** Public API of the `version-compare` page slice (`CMP-VC-UI-01`): the screen «Сравнение версий». */

export type { VersionComparePageProps } from './ui/version-compare-page';
export { CHOOSE_PROJECT_DETAIL, CHOOSE_PROJECT_TITLE, UPLOAD_BUTTON, VersionComparePage } from './ui/version-compare-page';
export type { CompareTab } from './model/tabs';
export { COMPARE_TABS, COMPARE_TAB_HINTS, COMPARE_TAB_LABELS, isCompareTab, tabAfterKey } from './model/tabs';
