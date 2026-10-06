/**
 * What the API answers `getMe` with, as the contract declares `Account`, for the session suites.
 *
 * Every property the contract requires is present, so a fixture that omitted one cannot make
 * a handler look stricter than it is. `overrides` replaces whole properties, including with a
 * value of the wrong type: that is how the refusal cases build a body the handler must not
 * understand.
 */

export const ACCOUNT_LOGIN = 'reviewer@example.test';
export const ACCOUNT_LABEL = 'Проверяющая А. Б.';

export function accountBody(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B',
    login: ACCOUNT_LOGIN,
    display_label: ACCOUNT_LABEL,
    last_name: 'Проверяющая',
    first_name: 'Анна',
    middle_name: 'Борисовна',
    roles: ['expert'],
    is_default_credential: false,
    profile_complete: true,
    archived_at: null,
    ...overrides,
  };
}

export function accountAnswer(overrides: Record<string, unknown> = {}): Response {
  return new Response(JSON.stringify(accountBody(overrides)), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });
}

/** The API's own `401` envelope, as the contract declares it. */
export function authenticationRequired(correlationId = 'api-correlation-401'): Response {
  return new Response(
    JSON.stringify({
      contract_version: '1.0.0-draft.1',
      correlation_id: correlationId,
      error_code: 'authentication_required',
      message: 'The credential is not accepted.',
      retryable: false,
    }),
    {
      status: 401,
      headers: { 'content-type': 'application/json', 'x-correlation-id': correlationId },
    },
  );
}

/** A `conflict` envelope carrying the closed `conflict_reason` detail. */
export function conflict(reason: unknown): Response {
  return new Response(
    JSON.stringify({
      contract_version: '1.0.0-draft.1',
      correlation_id: 'api-correlation-409',
      error_code: 'conflict',
      message: 'Conflict.',
      retryable: false,
      details: { conflict_reason: reason },
    }),
    { status: 409, headers: { 'content-type': 'application/json' } },
  );
}
