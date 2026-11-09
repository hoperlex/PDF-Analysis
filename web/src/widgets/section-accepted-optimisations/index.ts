/**
 * Public API of the `section-accepted-optimisations` widget (`UI-B-27`): «Принято» on «Оптимизация разделов».
 * Mount `SectionAcceptedOptimisations`; the list is its pure part, for the static harness. The section and project choice
 * is the page's, in the row of the tabs (`UI-B-24`).
 */

export type { SectionAcceptedListProps, SectionAcceptedOptimisationsProps } from './ui/section-accepted-optimisations';
export {
  SectionAcceptedList,
  SectionAcceptedOptimisations,
  acceptedQuantity,
  acceptedSaving,
  acceptedSectionTitle,
} from './ui/section-accepted-optimisations';
