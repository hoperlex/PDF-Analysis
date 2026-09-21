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
        return { ...base, kind: 'request_invalid', title: 'Запрос списка проектов отклонён.' };
      case 'dependency_unavailable':
        return {
          ...base,
          kind: 'dependency_unavailable',
          title: 'Зависимость, нужная списку проектов, недоступна.',
        };
      case 'authentication_required':
        return {
          ...base,
          kind: 'not_authenticated',
          title: 'Чтение списка проектов не авторизовано.',
          detail: AUTHENTICATION_REQUIRED_DETAIL,
        };
      case 'permission_denied':
        return {
          ...base,
          kind: 'not_permitted',
          title: 'Вам не разрешено читать список проектов.',
          detail: PERMISSION_DENIED_DETAIL,
        };
      default:
        return { ...base, kind: 'server_error', title: 'Список проектов прочитать не удалось.' };
    }
  }

  if (error instanceof UnrecognizedApiError) {
    return {
      kind: 'unrecognized',
      title: 'Сервер сообщил об ошибке, которую этот клиент не распознаёт.',
      detail: `Error code '${error.rawErrorCode}' is outside this client's contract. Nothing was retried.`,
      correlationId: error.correlationId,
      retryable: false,
      errorCode: null,
    };
  }

  if (error instanceof TransportError) {
    return {
      kind: 'transport',
      title: 'Запрос списка проектов не дошёл до API.',
      detail: error.message,
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: null,
    };
  }

  return {
    kind: 'unknown',
    title: 'Список проектов прочитать не удалось.',
    detail:
      error instanceof ApiFailure
        ? error.message
        : 'Клиент получил нечто, что не смог разобрать как отказ по контракту.',
    correlationId: error instanceof ApiFailure ? error.correlationId : null,
    retryable: false,
    errorCode: null,
  };
}
