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

/**
 * `AR-V3-OPT-IN` (contract 1.38.0): the two refusals of an AR v3 run that a `409 conflict` carries in `conflict_reason`. Neither is
 * a lost race, which is what the catalog's own sentence for `conflict` says, so each has a sentence of its own, worded once here
 * for every screen that turns a start, estimate or re-audit refusal into text.
 *
 * - `ar_v3_member_not_repeatable`: `reauditRun`, or `estimateRunCost` with `reaudit_of_run_id`, named a member of an AR v3 group;
 *   a repeat would route by the section and silently become the standard analysis, so it is refused and AR v3 is repeated by a
 *   new start of the group.
 * - `ar_v3_start_not_enabled`: `startArV3BetaGroup` or `estimateArV3GroupCost` was asked while the server does not allow starts.
 */
export const AR_V3_MEMBER_NOT_REPEATABLE_TEXT = 'Прогон из группы АР v3 не повторяется: повторите группу новым запуском.';
export const AR_V3_START_NOT_ENABLED_TEXT = 'Запуск АР v3 на этом сервере не разрешён.';

const AR_V3_CONFLICT_TEXT: Readonly<Record<string, string>> = {
  ar_v3_member_not_repeatable: AR_V3_MEMBER_NOT_REPEATABLE_TEXT,
  ar_v3_start_not_enabled: AR_V3_START_NOT_ENABLED_TEXT,
};

/** The sentence for an AR v3 conflict refusal, or `null` for any other error (a reason this client does not know is not guessed). */
export function arV3ConflictSentence(error: unknown): string | null {
  if (!(error instanceof ApiError) || error.errorCode !== 'conflict') return null;
  const reason = error.details['conflict_reason'];
  return typeof reason === 'string' && Object.prototype.hasOwnProperty.call(AR_V3_CONFLICT_TEXT, reason)
    ? (AR_V3_CONFLICT_TEXT[reason] ?? null)
    : null;
}

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
    const routing = routingRefusal(error.errorCode);
    const arV3 = arV3ConflictSentence(error);
    return {
      kind,
      detail: kind === 'unknown_outcome'
        ? 'Исход команды неизвестен. Проверьте состояние и повторяйте только с тем же ключом.'
        : routing !== null
          ? `${routing.title} ${routing.detail}`
          : arV3 !== null
            ? arV3
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
