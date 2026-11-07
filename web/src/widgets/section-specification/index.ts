/**
 * Public API of the `section-specification` widget (`W63-SECTION-FORM7-01`): the «Форма 7» tab of «Оптимизация
 * разделов» for `/section-optimisation`. Mount `SectionSpecificationSection`; `SectionSpecificationAnswer` is its pure part,
 * for the static harnesses. The section and project choice moved to the page's tab row (`UI-B-24`), where the original has it.
 */

export type { SectionSpecificationAnswerProps, SectionSpecificationColumns } from './ui/section-specification-answer';
export { SectionSpecificationAnswer, groupRowsByProject } from './ui/section-specification-answer';
export type { SectionSpecificationSectionProps } from './ui/section-specification-section';
export { PROJECT_SELECT_ID, SECTION_SELECT_ID, SectionSpecificationSection } from './ui/section-specification-section';
