/**
 * The typed failure surface of the API client.
 *
 * The contract has exactly one failure shape — the `ErrorEnvelope` — and one closed
 * twenty-code catalog. This module turns a non-2xx response into one of three things and
 * never into anything else:
 *
 *   - `ApiError`            the body was a valid envelope carrying a catalog code;
 *   - `UnrecognizedApiError` the body was a valid envelope carrying a code this client
 *                            does not know, which is an explicit state and never a
 *                            success and never a generic retry;
 *   - `TransportError`       the request never produced a decodable envelope at all.
 *
 * `retryable` always comes from the envelope, which the contract pins to the catalog
 * value for the reported code. A caller never infers it from the HTTP status, and this
 * module never invents it.
 */

import type { ErrorCode, ErrorEnvelope } from './generated/types.gen';
import { ERROR_CODE_VALUES } from './generated/types.gen';

/**
 * The subset of the catalog the PC-01 surface can actually return, per `P3-API-01`.
 *
 * The generated `ErrorCode` union is the full twenty-code catalog, because that is what
 * the contract declares. These ten are the ones a PC-01 screen has to be able to render;
 * `P02_SEAMS.md` section 9.4 records why each of the other ten has no PC-01 producer.
 * The union carries no partial-specific refusal: under `OD-11` a `partial` run **is**
 * exported, and a run whose terminal does not publish a result is refused with
 * `state_transition_not_allowed`, which is already in the list.
 *
 * This is a narrowing of the contract, never a replacement for it. A code outside the
 * list but inside the catalog is still an `ApiError`; only a code outside the catalog is
 * unrecognized.
 */
export const PC01_ERROR_CODES = [
  'validation_failed',
  'not_found',
  'conflict',
  'state_transition_not_allowed',
  'idempotency_key_reuse',
  'idempotency_key_in_progress',
  'idempotency_key_stale',
  'dependency_unavailable',
  'analysis_failed',
  'internal_error',
] as const;

export type Pc01ErrorCode = (typeof PC01_ERROR_CODES)[number];

/**
 * Compile-time proof that every code above is in the generated catalog. If session A1
 * ever removes one from the contract, this line stops type-checking.
 */
const _pc01CodesAreContractCodes: readonly ErrorCode[] = PC01_ERROR_CODES;
void _pc01CodesAreContractCodes;

const CATALOG: ReadonlySet<string> = new Set<string>(ERROR_CODE_VALUES);

/** Narrow an arbitrary string to the closed contract catalog. */
export function isErrorCode(value: string): value is ErrorCode {
  return CATALOG.has(value);
}

/** Narrow a catalog code to the subset a PC-01 screen is expected to render. */
export function isPc01ErrorCode(value: ErrorCode): value is Pc01ErrorCode {
  return (PC01_ERROR_CODES as readonly string[]).includes(value);
}

/** Common shape of everything this client throws, so a UI can render one panel. */
export abstract class ApiFailure extends Error {
  /** The correlation id an operator needs to find the diagnostic record. May be absent. */
  readonly correlationId: string | null;

  /** Whether the caller may retry. Never inferred; `false` unless the contract says so. */
  abstract readonly retryable: boolean;

  protected constructor(message: string, correlationId: string | null) {
    super(message);
    this.correlationId = correlationId;
  }
}

/** A decoded `ErrorEnvelope` carrying a code from the closed catalog. */
export class ApiError extends ApiFailure {
  readonly status: number;
  readonly errorCode: ErrorCode;
  readonly envelope: ErrorEnvelope;
  readonly retryable: boolean;

  constructor(status: number, envelope: ErrorEnvelope, correlationId: string | null) {
    super(`${envelope.error_code}: ${envelope.message}`, correlationId ?? envelope.correlation_id);
    this.name = 'ApiError';
    this.status = status;
    this.errorCode = envelope.error_code;
    this.envelope = envelope;
    this.retryable = envelope.retryable;
  }

  /** Safe scalar classifiers the catalog allows for this code. Never contains a key or path. */
  get details(): Readonly<Record<string, string | number | boolean | null>> {
    return this.envelope.details ?? {};
  }
}

/**
 * A well-formed envelope carrying a code this client's contract does not declare.
 *
 * This is an explicit state, not a fallback: the UI shows "unrecognized error" with the
 * correlation id, and nothing is retried. It means the server is ahead of the client, and
 * the contract drift guard should already have caught it before deployment.
 */
export class UnrecognizedApiError extends ApiFailure {
  readonly status: number;
  readonly rawErrorCode: string;
  readonly retryable = false;

  constructor(status: number, rawErrorCode: string, message: string, correlationId: string | null) {
    super(
      `Unrecognized error code '${rawErrorCode}' (HTTP ${status}). ` +
        'The server reported a code outside this client\'s contract; nothing was retried.',
      correlationId,
    );
    this.name = 'UnrecognizedApiError';
    this.status = status;
    this.rawErrorCode = rawErrorCode;
    void message;
  }
}

/**
 * The request produced no decodable envelope: a network failure, an abort, a non-JSON
 * body, or a JSON body that is not an envelope.
 */
export class TransportError extends ApiFailure {
  readonly status: number | null;
  readonly retryable: boolean;
  override readonly cause: unknown;

  constructor(
    message: string,
    options: { status?: number | null; correlationId?: string | null; retryable?: boolean; cause?: unknown } = {},
  ) {
    super(message, options.correlationId ?? null);
    this.name = 'TransportError';
    this.status = options.status ?? null;
    this.retryable = options.retryable ?? false;
    this.cause = options.cause;
  }
}

/** Raised before any request leaves, when the caller's input cannot form a legal request. */
export class ClientUsageError extends ApiFailure {
  readonly retryable = false;

  constructor(message: string) {
    super(message, null);
    this.name = 'ClientUsageError';
  }
}

/** Structural check that a decoded body really is the contract's envelope. */
export function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    typeof candidate['error_code'] === 'string' &&
    typeof candidate['message'] === 'string' &&
    typeof candidate['correlation_id'] === 'string' &&
    typeof candidate['retryable'] === 'boolean'
  );
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

/** True when the failure is exactly this catalog code. The way a slice branches. */
export function hasErrorCode(value: unknown, code: ErrorCode): boolean {
  return value instanceof ApiError && value.errorCode === code;
}

/**
 * `idempotency_key_in_progress` means the same key with the same payload is still
 * executing. The caller retries under the same key and never mints a new one.
 */
export function isIdempotencyInProgress(value: unknown): boolean {
  return hasErrorCode(value, 'idempotency_key_in_progress');
}

/**
 * `idempotency_key_reuse` means the same key arrived with a different payload. It is a
 * terminal, user-visible conflict: nothing was created and nothing is resubmitted.
 */
export function isIdempotencyKeyReuse(value: unknown): boolean {
  return hasErrorCode(value, 'idempotency_key_reuse');
}
