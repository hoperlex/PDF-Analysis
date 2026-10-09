import { ApiError, ApiFailure, catalogMessage } from '@/shared/api';

export type ExecutionFailureKind =
  | 'authentication'
  | 'permission'
  | 'transition'
  | 'conflict'
  | 'refusal'
  | 'unknown_outcome'
  | 'read_unavailable'
  | 'unexpected';

export interface ExecutionFailure {
  readonly kind: ExecutionFailureKind;
  readonly detail: string;
  readonly correlationId: string | null;
}

export function executionFailure(error: unknown, write: boolean): ExecutionFailure {
  if (error instanceof ApiError) {
    const kind: ExecutionFailureKind =
      error.errorCode === 'authentication_required' ? 'authentication'
      : error.errorCode === 'permission_denied' ? 'permission'
      : error.errorCode === 'state_transition_not_allowed' ? 'transition'
      : write && (error.status >= 500 || error.errorCode === 'idempotency_key_in_progress')
        ? 'unknown_outcome'
      : error.errorCode === 'conflict' || error.errorCode === 'idempotency_key_reuse'
        ? 'conflict' : 'refusal';
    return {
      kind,
      detail: kind === 'unknown_outcome'
        ? 'Исход команды неизвестен. Проверьте состояние и повторяйте только с тем же ключом.'
        : catalogMessage(error.errorCode),
      correlationId: error.correlationId,
    };
  }
  if (error instanceof ApiFailure) {
    return {
      kind: write ? 'unknown_outcome' : 'read_unavailable',
      detail: write
        ? 'Исход команды неизвестен. Проверьте состояние и повторяйте только с тем же ключом.'
        : 'Сервер не ответил. Повторите чтение после проверки соединения.',
      correlationId: error.correlationId,
    };
  }
  return {
    kind: write ? 'unknown_outcome' : 'unexpected',
    detail: write
      ? 'Исход команды неизвестен. Проверьте состояние перед повтором.'
      : 'Не удалось прочитать данные выполнения.',
    correlationId: null,
  };
}
