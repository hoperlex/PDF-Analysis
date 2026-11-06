/**
 * How a line of the access journal reads in Russian (contract 1.36.0, `UI-A-94`).
 *
 * The journal holds identities, a role, a source word, one boolean and one count and nothing else, so everything
 * a row says is built from those; no login, address or password exists to print.
 */

import type { AuthEvent, AuthEventType } from '@/shared/api';
import { isKnownRole, roleLabel } from '@/entities/account';

export const AUTH_EVENT_LABELS: Readonly<Record<AuthEventType, string>> = {
  sign_in_succeeded: 'Вход',
  sign_in_blocked: 'Вход заблокирован',
  password_changed: 'Пароль изменён',
  password_reset: 'Пароль сброшен администратором',
  role_granted: 'Роль выдана',
  role_revoked: 'Роль снята',
  sessions_ended: 'Сеансы завершены администратором',
};

/** The facts beyond the type, as short phrases; empty when the type carries none. */
export function authEventDetails(event: Pick<AuthEvent, 'event_type' | 'role' | 'failures' | 'default_credential' | 'source'>): readonly string[] {
  const details: string[] = [];
  // A role this build does not know is printed as the code the server sent: a journal line is history, and a
  // vocabulary that moved must not hide it.
  if (event.role !== null) details.push(`Роль: ${isKnownRole(event.role) ? roleLabel(event.role) : event.role}`);
  if (event.failures !== null) details.push(`Неудачных попыток подряд: ${event.failures}`);
  if (event.default_credential === true) details.push('С исходным или временным паролем');
  if (event.source === 'host_cli') details.push('Выполнено на сервере');
  return details;
}
