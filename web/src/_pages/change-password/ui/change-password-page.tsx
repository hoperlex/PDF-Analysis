/**
 * `/account/password` — the screen that changes a password and, by doing so, revokes every
 * credential minted under the old one.
 *
 * Composition only, like every other page slice: the frame from `shared/ui`, the form from
 * the `change-password` feature. No query, no mutation, no domain rule and — the point of
 * the design this inherits from the sign-in screen — no client JavaScript. The route above
 * reads the cookie, asks the register who the session belongs to, and hands the answer down
 * as a prop.
 *
 * **Two shapes, selected by whether there is a session.** Changing a password requires
 * proving the current one *and* holding a credential, so a browser with no session is shown
 * the way to the sign-in screen rather than a form whose submission could only be refused.
 * That is not a convenience: a form that is always refused teaches a reviewer that the
 * refusal means nothing.
 */

import Link from 'next/link';

import { PageShell } from '@/shared/ui';
import type { ChangePasswordOutcome } from '@/features/change-password';
import { ChangePasswordForm } from '@/features/change-password';

export interface ChangePasswordPageProps {
  /** The login of the open session, or `null` when this browser has none. */
  readonly login?: string | null | undefined;
  /** How the last attempt ended, if there was one. */
  readonly outcome?: ChangePasswordOutcome | null | undefined;
}

export function ChangePasswordPage({ login, outcome }: ChangePasswordPageProps) {
  const signedIn = typeof login === 'string' && login.length > 0;

  return (
    <PageShell
      title="Смена пароля"
      subtitle={
        signedIn
          ? 'Смена пароля отзывает все ранее выданные пропуска этой учётной записи.'
          : 'Чтобы сменить пароль, нужно сначала войти: требуется подтвердить текущий пароль.'
      }
    >
      {signedIn ? (
        <ChangePasswordForm outcome={outcome} />
      ) : (
        <p className="am-note" data-change-password-session="none">
          Сеанс не открыт, поэтому менять нечего и подтверждать нечем.{' '}
          <Link href="/login">Перейдите на экран входа</Link> и войдите под своей учётной
          записью.
        </p>
      )}
      <p className="am-note">
        Оба пароля уходят на сервер этого приложения и дальше — на сервер учётных записей.
        Эта страница не хранит ни пароль, ни пропуск и не обращается к хранилищу браузера.
        Новый пропуск выдаётся сразу после смены и остаётся на сервере: в браузер
        возвращается только непрозрачный номер сеанса.
      </p>
    </PageShell>
  );
}
