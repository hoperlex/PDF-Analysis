/** Public API of the `auth-event` entity (contract 1.36.0, `UI-A-94`): the access journal's reads and wording. */

export { AUTH_EVENT_PAGE_LIMIT, useAuthEvents } from './api/use-auth-events';
export { AUTH_EVENT_LABELS, authEventDetails } from './model/presentation';
export { authEventFailure } from './model/failure';
export type { AuthEventFailure } from './model/failure';
