import { ApiError, ApiFailure, catalogMessage } from '@/shared/api';
// `W55B-WEB-BLOCKS` (`R-118`): a re-audit refused for its input budget prints the refusal's
// two figures, worded once in the run entity for the start-run control and this command alike.
import { inputBudgetSentence, routingRefusal } from '@/entities/audit-run';

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
    // `W59-SECTION-UI-01`: a re-audit is routed from the version's confirmed section exactly as
    // a start is, so its two routing refusals carry the run entity's own sentences.
    const routing =
      error.errorCode === 'required_norm_unavailable' ? routingRefusal(error.details) : null;
    return {
      kind,
      detail: kind === 'unknown_outcome'
        ? 'Исход команды неизвестен. Проверьте состояние и повторяйте только с тем же ключом.'
        : routing !== null
          ? `${routing.title} ${routing.detail}`
          : catalogMessage(error.errorCode) + budgetFigures(error),
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

/** The input-budget refusal's figures after its catalog sentence; nothing for any other code. */
function budgetFigures(error: ApiError): string {
  if (error.errorCode !== 'analysis_input_budget_exceeded') return '';
  const figures = inputBudgetSentence(error.details);
  return figures === null ? '' : ` ${figures}`;
}
