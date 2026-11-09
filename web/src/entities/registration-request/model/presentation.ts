import type { RegistrationStatus } from '@/shared/api';
import { failureMessage } from '@/shared/api/failure-message';

import { UnknownRegistrationStatusError } from '../api/use-registration-requests';

export const REGISTRATION_STATUS_LABELS: Readonly<Record<RegistrationStatus, string>> = {
  pending: 'Ожидает решения',
  approved: 'Одобрена',
  rejected: 'Отклонена',
};

/** The tone of a status badge (`UI-A-90`): a waiting request is amber, an approved one green, a rejected one red. */
export const REGISTRATION_STATUS_TONES: Readonly<Record<RegistrationStatus, 'degraded' | 'ok' | 'failed'>> = {
  pending: 'degraded',
  approved: 'ok',
  rejected: 'failed',
};

/** The filter chips of the queue: the original's tab says «Заявки (N)», here «Ожидают» says it and the others name what they hold. */
export const REGISTRATION_FILTER_LABELS: Readonly<Record<RegistrationStatus | 'all', string>> = {
  pending: 'Ожидают решения',
  approved: 'Одобрены',
  rejected: 'Отклонены',
  all: 'Все',
};

export interface RegistrationFailure {
  readonly kind: string;
  readonly detail: string;
  readonly correlationId: string | null;
}

/**
 * What a failed read or decision on registration requests says (`C-23`): the shared reading
 * (`failureMessage`) with this screen's one more precise sentence. A value that is not a
 * request failure is an unexpected error, never a transport failure.
 */
export function registrationFailure(error: unknown): RegistrationFailure {
  if (error instanceof UnknownRegistrationStatusError) {
    return { kind: 'unknown_status', detail: 'Заявка содержит состояние, которого эта версия приложения не знает.', correlationId: null };
  }
  const failure = failureMessage(error, {
    state_transition_not_allowed: 'Решение по этой заявке уже принято. Повторное решение невозможно.',
  });
  return { kind: failure.kind, detail: failure.detail, correlationId: failure.correlationId };
}
