import { ApiError, catalogMessage } from '@/shared/api';
import { UnknownRoleError } from '@/entities/account';

export interface UserFailure {
  readonly kind: string;
  readonly detail: string;
  readonly correlationId: string | null;
}

export function userFailure(error: unknown): UserFailure {
  if (error instanceof UnknownRoleError) {
    return { kind: 'unknown_role', detail: 'Сервер назвал роль, которой эта версия приложения не знает.', correlationId: null };
  }
  if (!(error instanceof ApiError)) {
    return { kind: 'transport', detail: 'Ответ сервера получить не удалось. Повторите попытку.', correlationId: null };
  }
  const reason = error.details.conflict_reason;
  if (error.errorCode === 'conflict' && reason === 'last_admin') {
    return { kind: 'last_admin', detail: 'Нельзя удалить роль или архивировать последнего действующего администратора.', correlationId: error.correlationId };
  }
  if (error.errorCode === 'conflict' && reason === 'account_referenced') {
    return { kind: 'account_referenced', detail: 'Учётная запись связана с данными системы и не может быть удалена.', correlationId: error.correlationId };
  }
  if (error.errorCode === 'conflict' && reason === 'login_taken') {
    return { kind: 'login_taken', detail: 'Адрес уже занят другой действующей учётной записью; восстановление невозможно.', correlationId: error.correlationId };
  }
  if (error.errorCode === 'permission_denied') {
    return { kind: 'permission_denied', detail: 'Операция запрещена. В частности, администратор не может архивировать себя или снять собственную роль.', correlationId: error.correlationId };
  }
  if (error.errorCode === 'state_transition_not_allowed') {
    return { kind: 'state_transition_not_allowed', detail: 'Для текущего состояния учётной записи это действие недоступно.', correlationId: error.correlationId };
  }
  return { kind: error.errorCode, detail: catalogMessage(error.errorCode), correlationId: error.correlationId };
}
