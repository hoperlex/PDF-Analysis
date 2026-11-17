/** Public API of the `section-detail` page slice: one section of one project (`R-151l`). */

export type { SectionDetailPageProps } from './ui/section-detail-page';
export { SectionDetailPage, sectionPageTitle } from './ui/section-detail-page';
// `UI-A-35`: «Выбрать все» over the whole listing — the row and the walk behind it, for the static harnesses.
export type { SectionHeaderProps } from './ui/section-header';
export { SectionHeader, objectHomeHref } from './ui/section-header';
export type { SectionBatchBarProps } from './ui/section-batch-bar';
export { SectionBatchBar } from './ui/section-batch-bar';
export type { ListingScope, ListingWalk } from './model/use-listing-walk';
export { useListingWalk } from './model/use-listing-walk';
export type { SectionChoices } from './model/section-choices';
export { sectionChoices } from './model/section-choices';
