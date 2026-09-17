/**
 * Public API of `shared/api` — the transport seam `B7` and `B8` both import.
 *
 * A slice imports from `@/shared/api` and from nothing deeper. It never reaches into
 * `./generated`, never sees a `Response`, never builds a URL and never writes an error
 * string by hand.
 *
 * Layout:
 *   generated/**   produced from contracts/api/v1/openapi.json; never hand-edited
 *   transport.ts   the only `fetch` in `web/`
 *   errors.ts      the closed failure surface
 *   authorization.ts  the two refusals of `T-6`'s seam, worded once
 *   credentialed-forward.ts  server-only; the `/bff/v1` route handler's rules
 *   idempotency.ts one key per intent, reused on every retry
 *   run-state.ts   terminal / non-terminal / exportable, and the `succeeded` split
 *   polling.ts     the one run-progress loop
 *   query-keys.ts  the frozen cache namespaces
 */

// Generated: every schema type, every operation input/result, every client function.
export * from './generated';

// Transport and its types.
export type {
  ApiResponse,
  FetchLike,
  OperationDescriptor,
  OperationInput,
  RequestOptions,
} from './transport';
export { request } from './transport';

// Failure surface.
export type { AuthorizationErrorCode } from './authorization';
export {
  AUTHENTICATION_REQUIRED_DETAIL,
  AUTHORIZATION_ERROR_CODES,
  PERMISSION_DENIED_DETAIL,
  authorizationDetail,
  isAuthorizationErrorCode,
  isAuthorizationFailure,
} from './authorization';

export type { Pc01ErrorCode } from './errors';
export {
  ApiError,
  ApiFailure,
  ClientUsageError,
  PC01_ERROR_CODES,
  TransportError,
  UnrecognizedApiError,
  hasErrorCode,
  isApiError,
  isErrorCode,
  isErrorEnvelope,
  isIdempotencyInProgress,
  isIdempotencyKeyReuse,
  isPc01ErrorCode,
} from './errors';

export { newIdempotencyKey } from './idempotency';

export type { NonTerminalRunState, TerminalRunState } from './run-state';
export {
  EXPORTABLE_RUN_STATES,
  NON_TERMINAL_RUN_STATES,
  TERMINAL_RUN_STATES,
  isExportableRunState,
  isTerminalRunState,
  stageCarriesError,
} from './run-state';

export type { PollRunOptions } from './polling';
export { pollRunStatus } from './polling';

export type { FindingListFilters, QueryNamespace } from './query-keys';
export { QUERY_NAMESPACES, queryKeys } from './query-keys';

export type { CsvColumn } from './csv-columns';
export { CSV_COLUMNS, CSV_ENCODING, csvFileName } from './csv-columns';
