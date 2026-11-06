/**
 * Public API of the `section-accepted-optimisations` widget (`UI-B-27`): «Принято» on «Оптимизация разделов».
 * Mount `SectionAcceptedOptimisations`; the filters and the list are its pure parts, for the static harness.
 */

export type {
  ProjectOption,
  SectionAcceptedFiltersProps,
  SectionAcceptedListProps,
  SectionAcceptedOptimisationsProps,
} from './ui/section-accepted-optimisations';
export {
  SectionAcceptedFilters,
  SectionAcceptedList,
  SectionAcceptedOptimisations,
  acceptedQuantity,
  acceptedSaving,
  acceptedSectionTitle,
  projectOptions,
} from './ui/section-accepted-optimisations';
