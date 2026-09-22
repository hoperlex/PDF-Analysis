/**
 * `/login` — the screen that exchanges a login and a password for a session.
 *
 * Composition only, like every other page slice: the frame from `shared/ui`, the forms
 * from the `sign-in` feature. No query, no mutation, no domain rule and — the point of the
 * whole design — no client JavaScript. The route above reads the cookie, asks the register
 * who the session belongs to, and hands the answer down as a prop; this file decides only
 * which of the two forms a reviewer is looking at.
 *
 * The screen carries the sign-out control because the application bar belongs to another
 * slice this wave does not own. That is a limitation of where the control sits, not of
 * what it does, and it is recorded in the session report rather than worked around by
 * editing someone else's chrome.
 */

import { PageShell } from '@/shared/ui';
import type { SignInRefusal } from '@/features/sign-in';
import { SignInForm, SignOutForm } from '@/features/sign-in';

export interface SignInPageProps {
  /** The login of the open session, or `null` when this browser has none. */
  readonly login?: string | null | undefined;
  /** The refusal the last attempt was redirected back with, if there was one. */
  readonly refusal?: SignInRefusal | null | undefined;
}

export function SignInPage({ login, refusal }: SignInPageProps) {
  const signedIn = typeof login === 'string' && login.length > 0;

  return (
    <PageShell
      title="Вход"
      subtitle={
        signedIn
          ? 'Сеанс открыт. Он хранится на сервере приложения; в браузере лежит только его номер.'
          : 'Имя пользователя и пароль уходят на сервер приложения и обмениваются на пропуск там же.'
      }
    >
      {signedIn ? <SignOutForm login={login} /> : <SignInForm refusal={refusal} />}
      <p className="am-note">
        Проверка пары имени и пароля целиком на стороне сервера. Эта страница не хранит
        ни пароль, ни пропуск и не обращается к хранилищу браузера.
      </p>
    </PageShell>
  );
}
