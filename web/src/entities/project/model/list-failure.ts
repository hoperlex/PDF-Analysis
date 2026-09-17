/**
 * Failure states for reading the project list.
 *
 * A read is a much smaller surface than a write — no idempotency case can arise — but it
 * gets its own wording rather than borrowing the create classifier's, because "creating
 * the project failed" over a failed `GET /projects` is a sentence that sends the reader
 * looking for a project they never asked to create.
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

export type ProjectListFailureKind =
  | 'request_invalid'
  | 'dependency_unavailable'
  | 'not_authenticated'
  | 'not_permitted'
  | 'server_error'
  | 'unrecognized'
  | 'transport'
  | 'unknown';

export interface ProjectListFailure {
  readonly kind: ProjectListFailureKind;
  readonly title: string;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
  readonly errorCode: ErrorCode | null;
}

/** Classify anything thrown by `listProjects`. */
export function classifyProjectListFailure(error: unknown): ProjectListFailure {
  if (error instanceof ApiError) {
    const base = {
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: error.errorCode,
      detail: error.envelope.message,
    };
    switch (error.errorCode) {
      case 'validation_failed':
        return { ...base, kind: 'request_invalid', title: 'The project list request was refused.' };
      case 'dependency_unavailable':
        return {
          ...base,
          kind: 'dependency_unavailable',
          title: 'A dependency the project list needs is unavailable.',
        };
      case 'authentication_required':
        return {
          ...base,
          kind: 'not_authenticated',
          title: 'Reading the project list is not authorized.',
          detail: AUTHENTICATION_REQUIRED_DETAIL,
        };
      case 'permission_denied':
        return {
          ...base,
          kind: 'not_permitted',
          title: 'You are not permitted to read the project list.',
          detail: PERMISSION_DENIED_DETAIL,
        };
      default:
        return { ...base, kind: 'server_error', title: 'The project list could not be read.' };
    }
  }

  if (error instanceof UnrecognizedApiError) {
    return {
      kind: 'unrecognized',
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
      title: 'The project list request did not reach the API.',
      detail: error.message,
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: null,
    };
  }

  return {
    kind: 'unknown',
    title: 'The project list could not be read.',
    detail:
      error instanceof ApiFailure
        ? error.message
        : 'The client received something it could not decode as a contract failure.',
    correlationId: error instanceof ApiFailure ? error.correlationId : null,
    retryable: false,
    errorCode: null,
  };
}
