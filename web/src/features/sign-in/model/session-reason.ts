/**
 * The sentence above the sign-in form when the screen knows why there is no session.
 *
 * The closed list is `@/shared/lib/session-end-reason` — the BFF writes it into the address
 * (`/login?reason=ended`) and into a short-lived note; this module only says each value in
 * Russian, the way the original portal's sign-in page did («Сеанс истёк», «Сеанс завершён»,
 * «Сеанс недействителен»).
 *
 * `ended` is deliberately the plain «Сеанс завершён»: the API answers an administrator's
 * «Завершить сеансы», a changed password, changed rights and an archived account with one
 * and the same `401`, so the screen cannot say which of them it was, and does not.
 */

import type { SessionEndReason } from '@/shared/lib/session-end-reason';

export type { SessionEndReason } from '@/shared/lib/session-end-reason';
export {
  SESSION_END_REASONS,
  SESSION_END_REASON_PARAM as SIGN_IN_REASON_PARAM,
  isSessionEndReason,
  sessionEndReasonOf,
} from '@/shared/lib/session-end-reason';

/** The sentence a reviewer reads. The machine value stays on the `data-` attribute. */
export function signInReasonMessage(reason: SessionEndReason): string {
  switch (reason) {
    case 'expired':
      return 'Сеанс истёк — войдите снова.';
    case 'ended':
      return 'Сеанс завершён — войдите снова.';
    case 'invalid':
      return 'Сеанс недействителен — войдите снова.';
  }
}
