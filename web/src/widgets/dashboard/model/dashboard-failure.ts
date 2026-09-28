/**
 * Failure states for `getDashboardSummary`.
 *
 * One aggregate read, no parent to name and no page to blame — the same reason
 * `entities/project`'s `classifyProjectListFailure` writes its own wording instead of
 * reusing `shared/lib`'s `classifyListingFailure`, whose sentences are all built around a
 * `parent` (`project` | `document` | `version`) this read does not have. This module is
 * the same shape, once, for the dashboard's own subject.
 */

import type { ErrorCode } from '@/shared/api';
import {
  AUTHENTICATION_REQUIRED_DETAIL,
  ApiError,
  ApiFailure,
  PERMISSION_DENIED_DETAIL,
  TransportError,
  UnrecognizedApiError,
  catalogMessage,
} from '@/shared/api';

export type DashboardFailureKind =
  | 'request_invalid'
  | 'dependency_unavailable'
  | 'not_authenticated'
  | 'not_permitted'
  | 'server_error'
  | 'unrecognized'
  | 'transport'
  | 'unknown';

export interface DashboardFailure {
  readonly kind: DashboardFailureKind;
  readonly title: string;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
  readonly errorCode: ErrorCode | null;
}

/** Classify anything thrown by `getDashboardSummary`. */
export function classifyDashboardFailure(error: unknown): DashboardFailure {
  if (error instanceof ApiError) {
    const base = {
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: error.errorCode,
      detail: catalogMessage(error.errorCode),
    };
    switch (error.errorCode) {
      case 'validation_failed':
        return { ...base, kind: 'request_invalid', title: 'Запрос сводки отклонён.' };
      case 'dependency_unavailable':
        return {
          ...base,
          kind: 'dependency_unavailable',
          title: 'Зависимость, нужная сводке, недоступна.',
        };
      case 'authentication_required':
        return {
          ...base,
          kind: 'not_authenticated',
          title: 'Чтение сводки не авторизовано.',
          detail: AUTHENTICATION_REQUIRED_DETAIL,
        };
      case 'permission_denied':
        return {
          ...base,
          kind: 'not_permitted',
          title: 'Вам не разрешено читать сводку.',
          detail: PERMISSION_DENIED_DETAIL,
        };
      default:
        return { ...base, kind: 'server_error', title: 'Сводку прочитать не удалось.' };
    }
  }

  if (error instanceof UnrecognizedApiError) {
    return {
      kind: 'unrecognized',
      title: 'Сервер сообщил об ошибке, которую этот клиент не распознаёт.',
      detail: `Код ошибки «${error.rawErrorCode}» этому клиенту не знаком. Повтор не выполнялся.`,
      correlationId: error.correlationId,
      retryable: false,
      errorCode: null,
    };
  }

  if (error instanceof TransportError) {
    return {
      kind: 'transport',
      title: 'Запрос сводки не дошёл до сервера.',
      detail: error.message,
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: null,
    };
  }

  return {
    kind: 'unknown',
    title: 'Сводку прочитать не удалось.',
    detail:
      error instanceof ApiFailure
        ? error.message
        : 'Клиент получил ответ, форму которого он не смог разобрать как отказ.',
    correlationId: error instanceof ApiFailure ? error.correlationId : null,
    retryable: false,
    errorCode: null,
  };
}
