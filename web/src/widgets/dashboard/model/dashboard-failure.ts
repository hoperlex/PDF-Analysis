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
  /**
   * The address names a project the server does not know (`?project=`, `404 not_found`,
   * `UI-PARITY-P0A`). Only ever produced when a project was asked for: without one the
   * dashboard has no parent to miss, and a `not_found` there is the generic read failure.
   */
  | 'project_not_found'
  | 'request_invalid'
  | 'dependency_unavailable'
  | 'not_authenticated'
  | 'not_permitted'
  | 'server_error'
  | 'unrecognized'
  | 'transport'
  | 'unknown'
  /** A panel's own closed vocabulary did not arrive whole. See `incompleteBreakdownFailure`. */
  | 'incomplete';

export interface DashboardFailure {
  readonly kind: DashboardFailureKind;
  readonly title: string;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryable: boolean;
  readonly errorCode: ErrorCode | null;
}

/**
 * Classify anything thrown by `getDashboardSummary`.
 *
 * @param projectUid the project the read asked for, or `null` for «Все проекты». A `not_found`
 *   is «Проект не найден» only when one was asked for: the unknown project is shown as exactly
 *   that, never as a summary of zeros and never as «Все проекты».
 */
export function classifyDashboardFailure(
  error: unknown,
  projectUid: string | null = null,
): DashboardFailure {
  if (error instanceof ApiError) {
    if (error.errorCode === 'not_found' && projectUid !== null) {
      return {
        kind: 'project_not_found',
        title: 'Проект не найден',
        detail:
          'В адресе указан проект, которого нет в системе или который вам не виден, поэтому сводку ' +
          'по нему показать нельзя. Сводка по всем проектам доступна по ссылке ниже.',
        correlationId: error.correlationId,
        retryable: false,
        errorCode: error.errorCode,
      };
    }
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

/**
 * A panel's own closed set of rows did not arrive whole — one missing, one repeated, or
 * one the panel does not recognise (`section-breakdown.ts`, `verdict-breakdown.ts`,
 * `run-state-breakdown.ts`). Not a thrown error: `getDashboardSummary` succeeded, so this
 * is never a branch of `classifyDashboardFailure` above. It is built directly, in the
 * shape, by the panel that found the gap — one way for the whole widget to say "this
 * cannot be shown", not two.
 */
export function incompleteBreakdownFailure(title: string): DashboardFailure {
  return {
    kind: 'incomplete',
    title,
    detail:
      'Часть значений, которые эта разбивка обязана показывать, отсутствует или не опознана — частичный счёт не показывается.',
    correlationId: null,
    retryable: false,
    errorCode: null,
  };
}
