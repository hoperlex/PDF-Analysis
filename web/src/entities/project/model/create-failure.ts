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
  catalogMessage,
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
        title: 'Сервер отклонил это название проекта.',
        detail:
          catalogMessage(error.errorCode) + classifiers(error.details, ['field', 'constraint', 'aggregate_type']),
      };
    case 'dependency_unavailable':
      return {
        ...base,
        kind: 'dependency_unavailable',
        presentation: 'error',
        title: 'Зависимость недоступна.',
        detail:
          catalogMessage(error.errorCode) +
          classifiers(error.details, ['dependency']) +
          ' Ничего не применено частично. Повтор использует тот же ключ идемпотентности.',
      };
    case 'authentication_required':
      return {
        ...base,
        kind: 'not_authenticated',
        presentation: 'error',
        title: 'Создание проекта не авторизовано.',
        detail: AUTHENTICATION_REQUIRED_DETAIL,
      };
    case 'permission_denied':
      return {
        ...base,
        kind: 'not_permitted',
        presentation: 'error',
        title: 'Вам не разрешено создавать проект.',
        detail:
          PERMISSION_DENIED_DETAIL +
          classifiers(error.details, ['aggregate_type', 'required_capability']),
      };
    case 'idempotency_key_reuse':
      return {
        ...base,
        kind: 'duplicate_intent',
        presentation: 'error',
        title: 'Этот ключ уже использован для другого проекта.',
        detail:
          catalogMessage(error.errorCode) +
          classifiers(error.details, ['command_type']) +
          ' Ничего не создано и ничего не отправлено повторно.',
      };
    case 'idempotency_key_in_progress':
      return {
        ...base,
        kind: 'in_progress',
        presentation: 'error',
        title: 'Этот проект ещё создаётся.',
        detail:
          catalogMessage(error.errorCode) +
          classifiers(error.details, ['command_type']) +
          ' Повтор спрашивает снова под тем же ключом; новый ключ создал бы второй проект.',
      };
    case 'idempotency_key_stale':
      return {
        ...base,
        kind: 'stale_intent',
        presentation: 'error',
        title: 'Записанный результат этого запроса больше недоступен.',
        detail:
          catalogMessage(error.errorCode) + classifiers(error.details, ['command_type']) + ' Он не домысливается.',
      };
    case 'conflict':
      return {
        ...base,
        kind: 'conflict',
        presentation: 'error',
        title: 'Запрос вошёл в конфликт с инвариантом.',
        detail:
          catalogMessage(error.errorCode) + classifiers(error.details, ['aggregate_type', 'expected_revision']),
      };
    default:
      return {
        ...base,
        kind: 'server_error',
        presentation: 'error',
        title: 'Создание проекта завершилось ошибкой на сервере.',
        detail: catalogMessage(error.errorCode),
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
      title: 'Запрос не дошёл до API.',
      detail:
        `${error.message} Повтор под тем же ключом безопасен: это та же команда, а не вторая.`,
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: null,
    };
  }

  return {
    kind: 'unknown',
    presentation: 'error',
    title: 'Создать проект не удалось по неклассифицированной причине.',
    detail:
      error instanceof ApiFailure
        ? error.message
        : 'Клиент получил нечто, что не смог разобрать как отказ по контракту.',
    correlationId: error instanceof ApiFailure ? error.correlationId : null,
    retryable: false,
    errorCode: null,
  };
}
