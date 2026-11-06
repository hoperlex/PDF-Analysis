/**
 * What a failed read of the access journal says. Only the shared reading applies (`failureMessage`), plus the one
 * refusal this screen can meet: a caller who is not an administrator.
 */

import { failureMessage } from '@/shared/api/failure-message';

export interface AuthEventFailure {
  readonly kind: string;
  readonly detail: string;
  readonly correlationId: string | null;
}

export function authEventFailure(error: unknown): AuthEventFailure {
  const failure = failureMessage(error, {
    permission_denied: 'Журнал входов доступен только администратору.',
  });
  return { kind: failure.kind, detail: failure.detail, correlationId: failure.correlationId };
}
