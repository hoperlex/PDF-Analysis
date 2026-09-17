/**
 * Every way creating a project can fail, as one explicit state each.
 *
 * The idempotency cases are the ones worth separating. `idempotency_key_in_progress`
 * means the same key and payload is still executing and is retried under **the same**
 * key; `idempotency_key_reuse` means the same key arrived with a different payload and
 * is terminal — nothing was created and nothing is resubmitted. A screen that showed one
 * sentence for both would invite the user to mint a fresh key, which is a second command,
 * not a retry.
 */

import type { ErrorCode } from '@/shared/api';
import {
  AUTHENTICATION_REQUIRED_DETAIL,
  ApiError,
  ApiFailure,
  PERMISSION_DENIED_DETAIL,
  TransportError,
  UnrecognizedApiError,
} from '@/shared/api';

export type CreateProjectFailureKind =
  | 'invalid_name'
  | 'dependency_unavailable'
  | 'not_authenticated'
  | 'not_permitted'
  | 'duplicate_intent'
  | 'in_progress'
  | 'stale_intent'
  | 'conflict'
  | 'server_error'
  | 'unrecognized'
  | 'transport'
  | 'unknown';

export interface CreateProjectFailure {
  readonly kind: CreateProjectFailureKind;
  readonly presentation: 'unsupported' | 'error';
  readonly title: string;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
  readonly errorCode: ErrorCode | null;
}

/** Render only the safe scalar classifiers the catalog declares for this code. */
function classifiers(
  details: Readonly<Record<string, string | number | boolean | null>>,
  keys: readonly string[],
): string {
  const parts: string[] = [];
  for (const key of keys) {
    const value = details[key];
    if (value === undefined || value === null || value === '') continue;
    parts.push(`${key}: ${String(value)}`);
  }
  return parts.length === 0 ? '' : ` (${parts.join(', ')})`;
}

function fromApiError(error: ApiError): CreateProjectFailure {
  const base = {
    correlationId: error.correlationId,
    retryable: error.retryable,
    errorCode: error.errorCode,
  };

  switch (error.errorCode) {
    case 'validation_failed':
      return {
        ...base,
        kind: 'invalid_name',
        presentation: 'unsupported',
        title: 'The server refused this project name.',
        detail:
          error.envelope.message + classifiers(error.details, ['field', 'constraint', 'aggregate_type']),
      };
    case 'dependency_unavailable':
      return {
        ...base,
        kind: 'dependency_unavailable',
        presentation: 'error',
        title: 'A dependency is unavailable.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['dependency']) +
          ' Nothing was partially applied. Retrying reuses the same idempotency key.',
      };
    case 'authentication_required':
      return {
        ...base,
        kind: 'not_authenticated',
        presentation: 'error',
        title: 'Creating a project is not authorized.',
        detail: AUTHENTICATION_REQUIRED_DETAIL,
      };
    case 'permission_denied':
      return {
        ...base,
        kind: 'not_permitted',
        presentation: 'error',
        title: 'You are not permitted to create a project.',
        detail:
          PERMISSION_DENIED_DETAIL +
          classifiers(error.details, ['aggregate_type', 'required_capability']),
      };
    case 'idempotency_key_reuse':
      return {
        ...base,
        kind: 'duplicate_intent',
        presentation: 'error',
        title: 'This key was already used for a different project.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['command_type']) +
          ' Nothing was created and nothing was resubmitted.',
      };
    case 'idempotency_key_in_progress':
      return {
        ...base,
        kind: 'in_progress',
        presentation: 'error',
        title: 'This project is still being created.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['command_type']) +
          ' Retrying asks again under the same key; a new key would create a second project.',
      };
    case 'idempotency_key_stale':
      return {
        ...base,
        kind: 'stale_intent',
        presentation: 'error',
        title: 'The recorded outcome of this request is no longer available.',
        detail:
          error.envelope.message + classifiers(error.details, ['command_type']) + ' It is not guessed.',
      };
    case 'conflict':
      return {
        ...base,
        kind: 'conflict',
        presentation: 'error',
        title: 'The request conflicted with an invariant.',
        detail:
          error.envelope.message + classifiers(error.details, ['aggregate_type', 'expected_revision']),
      };
    default:
      return {
        ...base,
        kind: 'server_error',
        presentation: 'error',
        title: 'Creating the project failed on the server.',
        detail: error.envelope.message,
      };
  }
}

/** Classify anything thrown by `createProject`. */
export function classifyCreateProjectFailure(error: unknown): CreateProjectFailure {
  if (error instanceof ApiError) return fromApiError(error);

  if (error instanceof UnrecognizedApiError) {
    return {
      kind: 'unrecognized',
      presentation: 'error',
      title: 'The server reported an error this client does not recognise.',
      detail: `Error code '${error.rawErrorCode}' is outside this client's contract. Nothing was retried.`,
      correlationId: error.correlationId,
      retryable: false,
      errorCode: null,
    };
  }

  if (error instanceof TransportError) {
    return {
      kind: 'transport',
      presentation: 'error',
      title: 'The request did not reach the API.',
      detail: `${error.message} Retrying under the same key is safe: it is the same command, not a second one.`,
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: null,
    };
  }

  return {
    kind: 'unknown',
    presentation: 'error',
    title: 'Creating the project failed for an unclassified reason.',
    detail:
      error instanceof ApiFailure
        ? error.message
        : 'The client received something it could not decode as a contract failure.',
    correlationId: error instanceof ApiFailure ? error.correlationId : null,
    retryable: false,
    errorCode: null,
  };
}
