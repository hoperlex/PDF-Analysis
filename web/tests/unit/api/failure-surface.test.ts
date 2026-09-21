/**
 * The closed failure surface, and the nine predicates on it that nothing was reading.
 *
 * `errors.ts` is the module that decides whether a non-2xx response becomes an `ApiError`,
 * an `UnrecognizedApiError` or a `TransportError`, and whether the caller may retry. The
 * `W12-WEB` sweep mutated every rule in it. The four classifiers above it
 * (`classifyUploadFailure` and friends) are well covered, but they re-decide `retryable`
 * themselves for the non-`ApiError` cases, so nine rules in `errors.ts` could be deleted
 * with the suite green:
 *
 *   - `isErrorCode` admitting anything — the narrowing that decides whether a body is a
 *     catalog failure or an unrecognized one, read by `transport.decodeFailure`;
 *   - `isPc01ErrorCode` admitting any catalog code;
 *   - `UnrecognizedApiError.retryable` becoming true — the whole point of that class is
 *     that the server is ahead of the client and nothing is retried;
 *   - `TransportError`'s default retryability becoming true;
 *   - `isErrorEnvelope` dropping `error_code` or `retryable` from its structural check;
 *   - `hasErrorCode` ignoring the code it is asked about, which collapses
 *     `isIdempotencyInProgress` and `isIdempotencyKeyReuse` into one another — the
 *     in-progress case is retried under the same key, the reuse case is terminal, and a
 *     client that confused them would mint a second command.
 *
 * Every expectation is a literal. `ERROR_CODE_VALUES` is the contract catalog and is used
 * as the authority for what is in it, never as the expected value of the thing under test.
 */

import { describe, expect, it } from 'vitest';

import type { ErrorEnvelope } from '@/shared/api';
import {
  ApiError,
  ERROR_CODE_VALUES,
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
} from '@/shared/api';

function envelope(overrides: Partial<ErrorEnvelope> = {}): ErrorEnvelope {
  const base: ErrorEnvelope = {
    contract_version: '1.0.0-draft.1',
    error_code: 'validation_failed',
    message: 'The request is not valid.',
    correlation_id: 'corr-1',
    retryable: false,
  };
  return Object.assign(base, overrides);
}

// ---------------------------------------------------------------------------------------
// The catalog is closed
// ---------------------------------------------------------------------------------------

describe('a code outside the catalog is not a catalog code', () => {
  it('refuses a string nobody declared', () => {
    expect(isErrorCode('cost_budget_exhausted')).toBe(false);
    expect(isErrorCode('')).toBe(false);
    expect(isErrorCode('VALIDATION_FAILED')).toBe(false);
    expect(isErrorCode('validation_failed ')).toBe(false);
  });

  it('accepts one that is in the catalog', () => {
    expect(isErrorCode('validation_failed')).toBe(true);
    expect(isErrorCode('storage_integrity_error')).toBe(true);
  });

  it('is asked about a catalog the contract actually declares', () => {
    // The authority half: if the catalog shrinks, the two assertions above stop meaning
    // what they say, so the catalog is pinned as well.
    // Twenty-two since round 7: `R-8`, reinstated by `R-13`, added `staged_upload_lost`.
    // Twenty-one before it, when `R-3` added `dependency_credential_refused`.
    expect(ERROR_CODE_VALUES).toHaveLength(22);
    expect([...ERROR_CODE_VALUES]).toContain('validation_failed');
    expect([...ERROR_CODE_VALUES]).not.toContain('cost_budget_exhausted');
  });
});

describe('the PC-01 subset is a subset, not the catalog', () => {
  it('admits what the surface can return and refuses what it cannot', () => {
    // No length literal since `D-40`. The membership of this list is derived from the
    // frozen documents by `tests/contract/pc01-error-codes.contract.test.ts`; what is
    // tested here is the predicate over it, which is what nothing was reading.
    expect(PC01_ERROR_CODES.length).toBeGreaterThan(0);
    expect(isPc01ErrorCode('validation_failed')).toBe(true);
    expect(isPc01ErrorCode('dependency_unavailable')).toBe(true);
    // The two `R-3` added. Since the seam went in front of every operation, every PC-01
    // screen can receive either, so every PC-01 screen has to be able to render it.
    expect(isPc01ErrorCode('authentication_required')).toBe(true);
    expect(isPc01ErrorCode('permission_denied')).toBe(true);
    // `storage_integrity_error` is a 422 the `UploadRejected` response names, and
    // `upload-failure.ts` has rendered it with its own sentence since `W12-WEB`. It was
    // outside this list until `W27-WEB`, which is `D-40`'s shape a second time over.
    expect(isPc01ErrorCode('storage_integrity_error')).toBe(true);
    // Still a subset: `OD-11` exports a `partial` run, so nothing refuses one, and no
    // operation on this surface declares the 400 that carries a version refusal.
    expect(isPc01ErrorCode('partial_result_not_publishable')).toBe(false);
    expect(isPc01ErrorCode('unsupported_contract_version')).toBe(false);
  });

  it('names a code the catalog also names, for each of its own', () => {
    for (const code of PC01_ERROR_CODES) {
      expect([...ERROR_CODE_VALUES], `${code} is not a catalog code`).toContain(code);
    }
  });
});

// ---------------------------------------------------------------------------------------
// Retryability never comes from the class, and never from the status
// ---------------------------------------------------------------------------------------

describe('an unrecognized code retries nothing, ever', () => {
  it('is not retryable whatever the status was', () => {
    const at503 = new UnrecognizedApiError(503, 'cost_budget_exhausted', 'unknown', 'corr-2');
    const at400 = new UnrecognizedApiError(400, 'cost_budget_exhausted', 'unknown', 'corr-2');
    expect(at503.retryable).toBe(false);
    expect(at400.retryable).toBe(false);
  });

  it('keeps the raw code and the correlation id so it can be reported', () => {
    const failure = new UnrecognizedApiError(503, 'cost_budget_exhausted', 'unknown', 'corr-2');
    expect(failure.rawErrorCode).toBe('cost_budget_exhausted');
    expect(failure.correlationId).toBe('corr-2');
    expect(failure.status).toBe(503);
  });
});

describe('a transport failure is not retryable unless it was told it is', () => {
  it('defaults to false', () => {
    expect(new TransportError('no response').retryable).toBe(false);
    expect(new TransportError('no response', { status: 503 }).retryable).toBe(false);
  });

  it('is true only when the caller passed true', () => {
    expect(new TransportError('no response', { retryable: true }).retryable).toBe(true);
  });
});

describe('an ApiError copies retryability off the envelope, not off the status', () => {
  it('is not retryable at 503 when the envelope says it is not', () => {
    const failure = new ApiError(503, envelope({ error_code: 'internal_error', retryable: false }), null);
    expect(failure.retryable).toBe(false);
  });

  it('is retryable at 422 when the envelope says it is', () => {
    const failure = new ApiError(422, envelope({ retryable: true }), null);
    expect(failure.retryable).toBe(true);
  });
});

// ---------------------------------------------------------------------------------------
// What counts as an envelope
// ---------------------------------------------------------------------------------------

describe('a body is the contract envelope only when it has all four required fields', () => {
  it('accepts the full shape', () => {
    expect(isErrorEnvelope(envelope())).toBe(true);
  });

  it('does not require contract_version, which the contract declares required', () => {
    // Recorded rather than asserted the other way round: `isErrorEnvelope` checks four
    // fields and `ErrorEnvelope` declares five. This pins the behaviour that exists so a
    // change to it is visible; `src/` is not this session's to change.
    const body: Record<string, unknown> = { ...envelope() };
    delete body['contract_version'];
    expect(isErrorEnvelope(body)).toBe(true);
  });

  it('refuses a body missing any one of the four', () => {
    // Built by deleting one key from a complete envelope, so each case differs from the
    // accepted shape in exactly one place and the refusal names that place.
    for (const missing of ['error_code', 'message', 'correlation_id', 'retryable'] as const) {
      const body: Record<string, unknown> = { ...envelope() };
      delete body[missing];
      expect(isErrorEnvelope(body), `a body with no ${missing} was accepted`).toBe(false);
    }
  });

  it('refuses a body whose retryable is a string rather than a boolean', () => {
    expect(isErrorEnvelope({ ...envelope(), retryable: 'false' })).toBe(false);
  });

  it('refuses things that are not objects at all', () => {
    expect(isErrorEnvelope(null)).toBe(false);
    expect(isErrorEnvelope('validation_failed')).toBe(false);
    expect(isErrorEnvelope(42)).toBe(false);
  });
});

// ---------------------------------------------------------------------------------------
// Branching on one code, not on "an error happened"
// ---------------------------------------------------------------------------------------

describe('a slice branching on a code branches on that code', () => {
  const inProgress = new ApiError(409, envelope({ error_code: 'idempotency_key_in_progress' }), null);
  const reuse = new ApiError(409, envelope({ error_code: 'idempotency_key_reuse' }), null);
  const notFound = new ApiError(404, envelope({ error_code: 'not_found' }), null);

  it('answers true only for the code it was asked about', () => {
    expect(hasErrorCode(inProgress, 'idempotency_key_in_progress')).toBe(true);
    expect(hasErrorCode(inProgress, 'idempotency_key_reuse')).toBe(false);
    expect(hasErrorCode(notFound, 'idempotency_key_in_progress')).toBe(false);
  });

  it('keeps the in-progress case apart from the reuse case', () => {
    // The consequence of collapsing them: in-progress is retried under the same key, reuse
    // is terminal. A client that treated reuse as in-progress would resubmit a command the
    // server has already refused for carrying a different payload.
    expect(isIdempotencyInProgress(inProgress)).toBe(true);
    expect(isIdempotencyInProgress(reuse)).toBe(false);
    expect(isIdempotencyKeyReuse(reuse)).toBe(true);
    expect(isIdempotencyKeyReuse(inProgress)).toBe(false);
  });

  it('answers false for anything that is not an ApiError', () => {
    expect(hasErrorCode(new TransportError('no response'), 'not_found')).toBe(false);
    expect(hasErrorCode(new Error('something'), 'not_found')).toBe(false);
    expect(isIdempotencyInProgress(null)).toBe(false);
    expect(isIdempotencyKeyReuse(undefined)).toBe(false);
  });

  it('recognises an ApiError and nothing else as one', () => {
    expect(isApiError(notFound)).toBe(true);
    expect(isApiError(new TransportError('no response'))).toBe(false);
    expect(isApiError(new UnrecognizedApiError(500, 'x', 'y', null))).toBe(false);
  });
});
