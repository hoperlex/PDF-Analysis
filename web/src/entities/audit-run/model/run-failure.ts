/**
 * Every way starting or watching a run can fail, as one explicit state each.
 *
 * The case this module exists for is `dependency_unavailable`. When the provider is
 * unavailable the screen says so, offers a retry under the same idempotency key, and
 * offers **nothing else** — in particular it never offers to fall back to `recorded`
 * mode. A silent downgrade from live to replayed would produce a run that looks like
 * evidence of a provider call that never happened, which is the exact confusion
 * `provider_mode` exists to prevent.
 *
 * `analysis_input_invalid` is kept distinct from `validation_failed`: the first says the
 * declared analysis inputs are not acceptable, the second says the request was malformed,
 * and collapsing them would hide which one the operator has to fix.
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

export type RunFailureKind =
  | 'request_invalid'
  | 'analysis_input_invalid'
  | 'provider_unavailable'
  | 'not_found'
  | 'not_authenticated'
  | 'not_permitted'
  | 'duplicate_intent'
  | 'in_progress'
  | 'stale_intent'
  | 'conflict'
  | 'not_allowed'
  | 'analysis_failed'
  | 'server_error'
  | 'unrecognized'
  | 'transport'
  | 'unknown';

export interface RunFailure {
  readonly kind: RunFailureKind;
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

function fromApiError(error: ApiError): RunFailure {
  const base = {
    correlationId: error.correlationId,
    retryable: error.retryable,
    errorCode: error.errorCode,
  };

  switch (error.errorCode) {
    case 'dependency_unavailable':
      return {
        ...base,
        kind: 'provider_unavailable',
        presentation: 'error',
        title: 'Провайдер, нужный этому прогону, недоступен.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['dependency']) +
          ' Nothing was partially applied. Retrying reuses the same idempotency key; ' +
          'прогон не запускается вместо этого в другом режиме провайдера.',
      };
    case 'analysis_input_invalid':
      return {
        ...base,
        kind: 'analysis_input_invalid',
        presentation: 'unsupported',
        title: 'Объявленные входные данные анализа неприемлемы.',
        detail: error.envelope.message + classifiers(error.details, ['stage_id', 'reason']),
      };
    case 'validation_failed':
      return {
        ...base,
        kind: 'request_invalid',
        presentation: 'unsupported',
        title: 'Этот запрос на прогон недействителен.',
        detail:
          error.envelope.message + classifiers(error.details, ['constraint', 'field', 'aggregate_type']),
      };
    case 'authentication_required':
      return {
        ...base,
        kind: 'not_authenticated',
        presentation: 'error',
        title: 'Этот прогон не авторизован.',
        detail: AUTHENTICATION_REQUIRED_DETAIL,
      };
    case 'permission_denied':
      return {
        ...base,
        kind: 'not_permitted',
        presentation: 'error',
        title: 'Вам не разрешено действовать с этим прогоном.',
        detail:
          PERMISSION_DENIED_DETAIL +
          classifiers(error.details, ['aggregate_type', 'required_capability']),
      };
    case 'not_found':
      return {
        ...base,
        kind: 'not_found',
        presentation: 'error',
        title: 'Такого прогона или версии не существует.',
        detail: error.envelope.message + classifiers(error.details, ['aggregate_type']),
      };
    case 'idempotency_key_reuse':
      return {
        ...base,
        kind: 'duplicate_intent',
        presentation: 'error',
        title: 'Этот ключ прогона уже использован для другого запроса.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['command_type']) +
          ' No run was created and nothing was resubmitted.',
      };
    case 'idempotency_key_in_progress':
      return {
        ...base,
        kind: 'in_progress',
        presentation: 'error',
        title: 'Этот запрос на прогон ещё выполняется.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['command_type']) +
          ' Retrying asks about the same request under the same key. A new key would be a second run.',
      };
    case 'idempotency_key_stale':
      return {
        ...base,
        kind: 'stale_intent',
        presentation: 'error',
        title: 'Записанный результат этого запроса на прогон больше недоступен.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['command_type']) +
          ' It is not guessed.',
      };
    case 'state_transition_not_allowed':
      return {
        ...base,
        kind: 'not_allowed',
        presentation: 'error',
        title: 'Прогон не в том состоянии, которое это допускает.',
        detail:
          error.envelope.message +
          classifiers(error.details, ['machine', 'current_state', 'requested_state']),
      };
    case 'conflict':
      return {
        ...base,
        kind: 'conflict',
        presentation: 'error',
        title: 'Запрос вошёл в конфликт с инвариантом.',
        detail:
          error.envelope.message + classifiers(error.details, ['aggregate_type', 'expected_revision']),
      };
    case 'analysis_failed':
      return {
        ...base,
        kind: 'analysis_failed',
        presentation: 'error',
        title: 'Анализ завершился неудачей.',
        detail: error.envelope.message + classifiers(error.details, ['run_id', 'stage_id']),
      };
    default:
      return {
        ...base,
        kind: 'server_error',
        presentation: 'error',
        title: 'Запрос завершился ошибкой на сервере.',
        detail: error.envelope.message,
      };
  }
}

/** Classify anything thrown by `startRun` or by the run-status poll. */
export function classifyRunFailure(error: unknown): RunFailure {
  if (error instanceof ApiError) return fromApiError(error);

  if (error instanceof UnrecognizedApiError) {
    return {
      kind: 'unrecognized',
      presentation: 'error',
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
      presentation: 'error',
      title: 'Запрос не дошёл до API.',
      detail: `${error.message} The run state shown, if any, is the last reading and may be stale.`,
      correlationId: error.correlationId,
      retryable: error.retryable,
      errorCode: null,
    };
  }

  return {
    kind: 'unknown',
    presentation: 'error',
    title: 'Запрос не выполнен по неклассифицированной причине.',
    detail:
      error instanceof ApiFailure
        ? error.message
        : 'Клиент получил нечто, что не смог разобрать как отказ по контракту.',
    correlationId: error instanceof ApiFailure ? error.correlationId : null,
    retryable: false,
    errorCode: null,
  };
}
