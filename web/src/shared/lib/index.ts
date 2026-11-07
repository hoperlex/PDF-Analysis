/** Public API of `shared/lib`. Generic helpers only; nothing domain-specific. */

export { assertNever } from './assert-never';
export { formatInstant } from './format-instant';

export type { IntentRecord } from './intent-key';
export { resolveIntentKey } from './intent-key';
export { useIntentKey } from './use-intent-key';

// `UI-PARITY` second pass: a screen's state kept in the address, one hook for the screens that had a copy each.
export type { AddressParams, AddressStep } from './use-address-state';
export { useAddressState } from './use-address-state';

export type { RouteIdentities } from './routes';
export { VERSION_CLASSIFICATION_ANCHOR, routes } from './routes';

export type { ListingFailure, ListingFailureKind, ListingSubject } from './listing-failure';
export { classifyListingFailure } from './listing-failure';

// `R-150c` (`UI-PARITY-01`): the project the user works in, read from and written to the address.
export type { ProjectContext, ProjectScope, ProjectSource, SearchParamsLike } from './project-context';
export {
  PROJECT_DEPENDENT_PARAMS,
  PROJECT_PARAM,
  canonicalProjectParams,
  projectScopeOf,
  readProjectContext,
  switchProject,
  withProjectParam,
} from './project-context';
