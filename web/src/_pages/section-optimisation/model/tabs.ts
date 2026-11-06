/** The tabs of «Оптимизация разделов» (`UI-B-22`, `UI-B-27`): the specification, and the accepted optimisations. */

export const SECTION_OPTIMISATION_TABS = ['specification', 'accepted'] as const;
export type SectionOptimisationTab = (typeof SECTION_OPTIMISATION_TABS)[number];

export const SECTION_OPTIMISATION_TAB_LABELS: Readonly<Record<SectionOptimisationTab, string>> = {
  specification: 'Спецификация',
  accepted: 'Принято',
};
