/**
 * Public API of the `section-specification` widget (`W63-SECTION-FORM7-01`): the «Форма 7» tab of «Оптимизация
 * разделов» for `/section-optimisation`. Mount `SectionSpecificationSection`; `SectionSpecificationAnswer` is its pure part,
 * for the static harnesses. The section is chosen in the page's header and the object in the top strip (`UI-B-24`, `UIP-S11-01`); the
 * table is grouped by document (`UIP-S11-02`).
 */

export type { SectionSpecificationAnswerProps, SectionSpecificationColumns } from './ui/section-specification-answer';
export { SectionSpecificationAnswer, groupRowsByDocument } from './ui/section-specification-answer';
export type { SectionSpecificationSectionProps } from './ui/section-specification-section';
export { SECTION_SELECT_ID, SectionSpecificationSection } from './ui/section-specification-section';
