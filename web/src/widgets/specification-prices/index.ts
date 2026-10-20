/**
 * Public API of the `specification-prices` widget (`W60-OPT-MATCH-01`): «Спецификация и цены»
 * for the project's «Оптимизация» tab. Mount `SpecificationPricesSection` with the project's
 * identity; the other two are its pure parts, for the static harnesses.
 */

export type { SpecificationPricesAnswerProps } from './ui/specification-prices-answer';
export { SpecificationPricesAnswer } from './ui/specification-prices-answer';
export type {
  SpecificationPricesChooserProps,
  SpecificationPricesSectionProps,
} from './ui/specification-prices-section';
export {
  SpecificationPricesChooser,
  SpecificationPricesSection,
  arDocumentSets,
} from './ui/specification-prices-section';
