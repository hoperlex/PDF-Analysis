/**
 * What a failed dispatcher read or command says (`W61-DISPATCHER-01`).
 *
 * The refusals this screen can meet have their own sentences, chosen by the closed detail
 * values the contract registers (`error-codes.json` notes); every other failure is the shared
 * reading (`failureMessage`), so a value that is not a request failure is reported as an
 * unexpected error and no thrown message is ever printed.
 */

import { ApiError } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';

export interface AssignmentFailure {
  readonly kind: string;
  readonly detail: string;
  readonly correlationId: string | null;
}

const CONSTRAINTS: Readonly<Record<string, string>> = {
  active_expert_required: 'Назначить работу можно только действующему пользователю с ролью «Эксперт».',
  differs_from_current_assignee: 'Работа уже назначена этому эксперту — выберите другого.',
};

export function assignmentFailure(error: unknown): AssignmentFailure {
  if (error instanceof ApiError) {
    const { conflict_reason: reason, constraint, required_capability: capability } = error.details;
    if (error.errorCode === 'conflict' && reason === 'assignment_open') {
      return {
        kind: 'assignment_open',
        detail:
          'У этого проекта или документа уже есть незакрытое назначение. Переназначьте или отмените его вместо нового.',
        correlationId: error.correlationId,
      };
    }
    if (error.errorCode === 'validation_failed' && typeof constraint === 'string') {
      const detail = CONSTRAINTS[constraint];
      if (detail !== undefined) return { kind: constraint, detail, correlationId: error.correlationId };
    }
    if (error.errorCode === 'permission_denied' && capability === 'assignment:assignee') {
      return {
        kind: 'assignee_only',
        detail: 'Взять в работу, выполнить или вернуть задачу может только эксперт, которому она назначена.',
        correlationId: error.correlationId,
      };
    }
  }
  const failure = failureMessage(error, {
    not_found: 'Такого назначения нет или оно вам не видно.',
    state_transition_not_allowed:
      'Состояние назначения уже изменилось, и это действие для него недоступно. Обновите список.',
    validation_failed: 'Сервер отклонил данные назначения. Проверьте поля и повторите.',
  });
  return { kind: failure.kind, detail: failure.detail, correlationId: failure.correlationId };
}
