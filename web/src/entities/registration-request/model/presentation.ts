import type { RegistrationStatus } from '@/shared/api';
import { ApiError, catalogMessage } from '@/shared/api';

import { UnknownRegistrationStatusError } from '../api/use-registration-requests';

export const REGISTRATION_STATUS_LABELS: Readonly<Record<RegistrationStatus, string>> = {
  pending: 'Ожидает решения',
  approved: 'Одобрена',
  rejected: 'Отклонена',
};

export interface RegistrationFailure {
  readonly kind: string;
  readonly detail: string;
  readonly correlationId: string | null;
}

export function registrationFailure(error: unknown): RegistrationFailure {
  if (error instanceof UnknownRegistrationStatusError) {
    return { kind: 'unknown_status', detail: error.message, correlationId: null };
  }
  if (!(error instanceof ApiError)) {
    return { kind: 'transport', detail: 'Ответ сервера получить не удалось. Повторите попытку.', correlationId: null };
  }
  if (error.errorCode === 'state_transition_not_allowed') {
    return { kind: 'state_transition_not_allowed', detail: 'Решение по этой заявке уже принято. Повторное решение невозможно.', correlationId: error.correlationId };
  }
  return { kind: error.errorCode, detail: catalogMessage(error.errorCode), correlationId: error.correlationId };
}
