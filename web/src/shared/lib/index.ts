/** Public API of `shared/lib`. Generic helpers only; nothing domain-specific. */

export { assertNever } from './assert-never';
export { formatInstant } from './format-instant';

export type { IntentRecord } from './intent-key';
export { resolveIntentKey } from './intent-key';
export { useIntentKey } from './use-intent-key';

export type { RouteIdentities } from './routes';
export { routes } from './routes';

export type { ListingFailure, ListingFailureKind, ListingSubject } from './listing-failure';
export { classifyListingFailure } from './listing-failure';
