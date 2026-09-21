/**
 * Every way an upload can fail, turned into one explicit, distinguishable state.
 *
 * The rule this module exists to enforce: an upload that did not publish a version never
 * looks like one that did, and never looks like "something went wrong". The three the
 * PC-01 acceptance criteria name separately are separate here —
 *
 *   unsupported input   `validation_failed`, the file is outside the envelope;
 *   checksum failure    `storage_integrity_error`, the stored bytes do not match their
 *                       declared identity, so nothing was published;
 *   dependency down     `dependency_unavailable`, the one retryable code on this surface.
 *
 * — and each carries the server's own reason rather than a generic sentence. A spinner
 * that never resolves and a green result over a failed upload are both refusals to say
 * which of these happened.
 *
 * Retryability is read from the decoded envelope and never inferred from a status code,
 * which is why `retryable` is copied off the failure rather than decided here.
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

/** The distinguishable outcomes of a failed upload. */
export type UploadFailureKind =
  | 'unsupported_input'
  | 'checksum_mismatch'
  | 'dependency_unavailable'
  | 'not_authenticated'
  | 'not_permitted'
  | 'duplicate_intent'
  | 'in_progress'
  | 'stale_intent'
  | 'project_not_found'
  | 'conflict'
  | 'server_error'
  | 'unrecognized'
  | 'transport'
  | 'unknown';

export interface UploadFailure {
  readonly kind: UploadFailureKind;
  /** Which shared state primitive renders it. `unsupported` offers no retry, by design. */
  readonly presentation: 'unsupported' | 'error';
  readonly title: string;
  /** The server's caller-safe sentence, plus the safe classifiers it declared. */
  readonly detail: string;
  readonly correlationId: string | null;
  /** Copied from the envelope. The panel offers a retry only when this is true. */
  readonly retryable: boolean;
  readonly errorCode: ErrorCode | null;
}

/**
 * Render the safe scalar classifiers the catalog declares for a code, in a fixed order.
 *
 * Only keys the catalog lists as safe for that code are read. Nothing here reaches for a
 * key the envelope happens to carry, so a server that ever leaked one does not get it
 * printed on a screen.
 */
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

function fromApiError(error: ApiError): UploadFailure {
  const base = {
    correlationId: error.correlationId,
    retryable: error.retryable,
    errorCode: error.errorCode,
  };

  switch (error.errorCode) {
    case 'validation_failed':
      return {
        ...base,
        kind: 'unsupported_input',
        presentation: 'unsupported',
        title: 'Файл выходит за допустимые ограничения.',
        detail:
          catalogMessage(error.errorCode) + classifiers(error.details, ['constraint', 'field', 'aggregate_type']),
      };
    case 'storage_integrity_error':
      return {
        ...base,
        kind: 'checksum_mismatch',
        presentation: 'error',
        title: 'Сохранённые байты не совпали с объявленной контрольной суммой.',
        detail:
          catalogMessage(error.errorCode) +
          classifiers(error.details, ['role', 'expected_sha256', 'actual_sha256']) +
          ' Ничего не опубликовано: ни версии, ни манифеста, ни читаемого объекта.',
      };
    case 'dependency_unavailable':
      return {
        ...base,
        kind: 'dependency_unavailable',
        presentation: 'error',
        title: 'Зависимость, нужная этой загрузке, недоступна.',
        detail:
          catalogMessage(error.errorCode) +
          classifiers(error.details, ['dependency']) +
          ' Ничего не применено частично. Повтор использует тот же ключ идемпотентности.',
      };
    case 'idempotency_key_reuse':
      return {
        ...base,
        kind: 'duplicate_intent',
        presentation: 'error',
        title: 'Этот ключ загрузки уже использован для другого файла.',
        detail:
          catalogMessage(error.errorCode) +
          classifiers(error.details, ['command_type']) +
          ' Ничего не создано и ничего не отправлено повторно. Выберите файл заново, чтобы начать новую загрузку.',
      };
    case 'idempotency_key_in_progress':
      return {
        ...base,
        kind: 'in_progress',
        presentation: 'error',
        title: 'Эта загрузка ещё обрабатывается.',
        detail:
          catalogMessage(error.errorCode) +
          classifiers(error.details, ['command_type']) +
          ' Повтор спрашивает о той же загрузке под тем же ключом и никогда не начинает вторую.',
      };
    case 'idempotency_key_stale':
      return {
        ...base,
        kind: 'stale_intent',
        presentation: 'error',
        title: 'Записанный результат этой загрузки больше недоступен.',
        detail:
          catalogMessage(error.errorCode) +
          classifiers(error.details, ['command_type']) +
          ' Он не домысливается. Выберите файл заново, чтобы начать новую загрузку.',
      };
    case 'authentication_required':
      return {
        ...base,
        kind: 'not_authenticated',
        presentation: 'error',
        title: 'Загрузка не авторизована.',
        detail: AUTHENTICATION_REQUIRED_DETAIL,
      };
    case 'permission_denied':
      return {
        ...base,
        kind: 'not_permitted',
        presentation: 'error',
        title: 'Вам не разрешено загружать в этот проект.',
        detail:
          PERMISSION_DENIED_DETAIL +
          classifiers(error.details, ['aggregate_type', 'required_capability']),
      };
    case 'not_found':
      return {
        ...base,
        kind: 'project_not_found',
        presentation: 'error',
        title: 'Такого проекта не существует.',
        detail: catalogMessage(error.errorCode) + classifiers(error.details, ['aggregate_type']),
      };
    case 'conflict':
      return {
        ...base,
        kind: 'conflict',
        presentation: 'error',
        title: 'Загрузка вошла в конфликт с инвариантом.',
        detail:
          catalogMessage(error.errorCode) + classifiers(error.details, ['aggregate_type', 'expected_revision']),
      };
    default:
      return {
        ...base,
        kind: 'server_error',
        presentation: 'error',
        title: 'Загрузка завершилась ошибкой на сервере.',
        detail: catalogMessage(error.errorCode),
      };
  }
}

/**
 * Classify anything thrown by `uploadDocument`.
 *
 * Nothing reaches a `catch (unknown)` and becomes a success: a value this module does not
 * recognise is an explicit `unknown` state with no retry, because a retry of something
 * nobody classified is how a second command gets issued.
 */
export function classifyUploadFailure(error: unknown): UploadFailure {
  if (error instanceof ApiError) return fromApiError(error);

  if (error instanceof UnrecognizedApiError) {
    return {
      kind: 'unrecognized',
      presentation: 'error',
      title: 'Сервер сообщил об ошибке, которую этот клиент не распознаёт.',
      detail:
        `Код ошибки «${error.rawErrorCode}» находится вне контракта этого клиента. ` +
        'Повтор не выполнялся.',
      correlationId: error.correlationId,
      retryable: false,
      errorCode: null,
    };
  }

  if (error instanceof TransportError) {
    return {
      kind: 'transport',
      presentation: 'error',
      title: 'Загрузка не дошла до API.',
      detail:
        `${error.message} Было ли что-нибудь опубликовано, неизвестно; повтор под тем же ` +
        'ключом безопасен.',
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: null,
    };
  }

  return {
    kind: 'unknown',
    presentation: 'error',
    title: 'Загрузка не выполнена по неклассифицированной причине.',
    detail:
      error instanceof ApiFailure
        ? error.message
        : 'Клиент получил нечто, что не смог разобрать как отказ по контракту.',
    correlationId: error instanceof ApiFailure ? error.correlationId : null,
    retryable: false,
    errorCode: null,
  };
}
