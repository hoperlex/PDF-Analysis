/**
 * Public API of the `finding-observation` entity.
 *
 * The declared pages of an observation, its evidence in contract order, and the quotation
 * handled as the immutable string it is.
 */

export {
  declaredPages,
  evidenceOnPage,
  firstDeclaredPage,
  isDeclaredPage,
  observationProviderMode,
  orderedEvidence,
} from './model/pages';

export {
  anchorLabel,
  anchorMatchesQuotation,
  quotationCodePointLength,
  quotationText,
} from './model/quotation';
