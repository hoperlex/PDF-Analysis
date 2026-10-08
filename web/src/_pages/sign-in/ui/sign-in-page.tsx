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
import { ErrorState } from '@/shared/ui';
import type { SignInRefusal } from '@/features/sign-in';
import { SignInForm, SignOutForm } from '@/features/sign-in';

export interface SignInPageProps {
  /** The login of the open session, or `null` when this browser has none. */
  readonly login?: string | null | undefined;
  /** The refusal the last attempt was redirected back with, if there was one. */
  readonly refusal?: SignInRefusal | null | undefined;
  /** The validated address to return to once signed in (`W50-PLAN.md` §3.2), if any. */
  readonly next?: string | null | undefined;
  readonly unknownRefusal?: boolean | undefined;
}

export function SignInPage({ login, refusal, next, unknownRefusal = false }: SignInPageProps) {
  const signedIn = typeof login === 'string' && login.length > 0;

  return (
    <PageShell
      title="Вход"
      subtitle={
        signedIn
          ? 'Сеанс открыт. Он хранится на сервере приложения; в браузере лежит только его номер.'
          : 'Адрес электронной почты и пароль уходят на сервер приложения. Для прежней учётной записи до завершения профиля принимается старый логин.'
      }
    >
      {signedIn ? <SignOutForm login={login} /> : <SignInForm refusal={refusal} next={next} />}
      {unknownRefusal ? <div data-sign-in-refusal="unknown"><ErrorState title="Неизвестный ответ входа" detail="Сервер вернул состояние, которое эта версия страницы не понимает." /></div> : null}
      <p className="am-note">
        Проверка пары имени и пароля целиком на стороне сервера. Эта страница не хранит
        ни пароль, ни пропуск и не обращается к хранилищу браузера.
      </p>
    </PageShell>
  );
}
