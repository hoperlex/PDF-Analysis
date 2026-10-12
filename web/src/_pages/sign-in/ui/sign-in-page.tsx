/**
 * `/login` — the screen that exchanges a login and a password for a session.
 *
 * Composition only, like every other page slice: the frame from `shared/ui`, the form from
 * the `sign-in` feature. No query, no mutation, no domain rule and — the point of the whole
 * design — no client JavaScript that could hold a credential: the form's only script is the
 * `SubmitLock` island, which reads no field (`C-22`).
 *
 * Only a guest sees this screen: the route's guard sends a browser that already holds a
 * session to `/` (`W50-PLAN.md` §3.2, decision five), and the frame's account menu carries
 * the way out. So the screen has one shape, the credentials form, and a link to the
 * registration form for someone who has no account yet (`C-21`).
 */

import Link from 'next/link';

import { REGISTER_SCREEN } from '@/shared/config/screen-registry';
import { ErrorState, PageShell } from '@/shared/ui';
import type { SignInRefusal } from '@/features/sign-in';
import { SignInForm } from '@/features/sign-in';

export interface SignInPageProps {
  /**
   * Unused since `C-25`: the guard never renders this screen for a session. Still accepted
   * because the route file (`app/login/page.tsx`) passes it; drop it there and here together.
   */
  readonly login?: string | null | undefined;
  /** The refusal the last attempt was redirected back with, if there was one. */
  readonly refusal?: SignInRefusal | null | undefined;
  /** The validated address to return to once signed in (`W50-PLAN.md` §3.2), if any. */
  readonly next?: string | null | undefined;
  readonly unknownRefusal?: boolean | undefined;
}

export function SignInPage({ refusal, next, unknownRefusal = false }: SignInPageProps) {
  return (
    <PageShell
      title="Вход"
      subtitle="Адрес электронной почты и пароль уходят на сервер приложения. Для прежней учётной записи до завершения профиля принимается старый логин."
    >
      <SignInForm refusal={refusal} next={next} />
      {unknownRefusal ? <div data-sign-in-refusal="unknown"><ErrorState title="Неизвестный ответ входа" detail="Сервер вернул состояние, которое эта версия страницы не понимает." /></div> : null}
      <p className="am-note" data-sign-in-register="">
        Нет учётной записи? <Link href={REGISTER_SCREEN}>Подать заявку на доступ</Link>
      </p>
      <p className="am-note">
        Проверка пары имени и пароля целиком на стороне сервера. Эта страница не хранит
        ни пароль, ни пропуск и не обращается к хранилищу браузера.
      </p>
    </PageShell>
  );
}
