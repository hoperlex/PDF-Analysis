/**
 * What a failed read or command on a managed account says (`W51`, `C-23`).
 *
 * The conflict reasons and the two refusals an administrator meets on this screen have their
 * own sentences; every other failure is the shared reading (`failureMessage`), so a value
 * that is not a request failure is reported as an unexpected error and never as a
 * transport failure, and no thrown message is ever printed.
 */

import { ApiError } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';
import { UnknownRoleError } from '@/entities/account';

export interface UserFailure {
  readonly kind: string;
  readonly detail: string;
  readonly correlationId: string | null;
}

const CONFLICT_REASONS: Readonly<Record<string, string>> = {
  last_admin: 'Нельзя удалить роль или архивировать последнего действующего администратора.',
  account_referenced: 'Учётная запись связана с данными системы и не может быть удалена.',
  login_taken: 'Адрес уже занят другой действующей учётной записью; восстановление невозможно.',
};

export function userFailure(error: unknown): UserFailure {
  if (error instanceof UnknownRoleError) {
    return { kind: 'unknown_role', detail: 'Сервер назвал роль, которой эта версия приложения не знает.', correlationId: null };
  }
  if (error instanceof ApiError && error.errorCode === 'conflict') {
    const reason = error.details.conflict_reason;
    const detail = typeof reason === 'string' ? CONFLICT_REASONS[reason] : undefined;
    if (detail !== undefined && typeof reason === 'string') {
      return { kind: reason, detail, correlationId: error.correlationId };
    }
  }
  const failure = failureMessage(error, {
    permission_denied: 'Операция запрещена. В частности, администратор не может архивировать себя или снять собственную роль.',
    state_transition_not_allowed: 'Для текущего состояния учётной записи это действие недоступно.',
  });
  return { kind: failure.kind, detail: failure.detail, correlationId: failure.correlationId };
}
