/**
 * The credentials form.
 *
 * **A server component on purpose, and it is the security property rather than a style
 * preference.** There is no `'use client'` here, no `useState`, and no handler: the
 * password is typed into a plain HTML input and posted by the browser itself. It is never
 * a JavaScript value, so it is in no bundle, no React tree, no error report and no
 * `localStorage`. `web/tests/unit/session/sign-in-screen.test.ts` asserts the absence of
 * the client directive rather than trusting this paragraph.
 *
 * The refusal is rendered through `shared/ui`'s `ErrorState` — the same block every other
 * screen uses for a failure the server will not change on retry — and carries its machine
 * value on `data-sign-in-refusal` beside the Russian sentence.
 */

import { ErrorState } from '@/shared/ui';

import type { SignInRefusal } from '../model/exchange';
import { SESSION_OPEN_PATH, signInRefusalMessage } from '../model/exchange';

export interface SignInFormProps {
  /** The refusal the previous attempt was redirected back with, if there was one. */
  readonly refusal?: SignInRefusal | null | undefined;
}

export function SignInForm({ refusal }: SignInFormProps) {
  return (
    <form className="am-form" method="post" action={SESSION_OPEN_PATH}>
      <div className="am-form__field">
        <label htmlFor="sign-in-login">
          <strong>Имя пользователя</strong>
        </label>
        <input
          id="sign-in-login"
          name="login"
          type="text"
          autoComplete="username"
          required
          maxLength={320}
          placeholder="Имя пользователя"
        />
      </div>

      <div className="am-form__field">
        <label htmlFor="sign-in-password">
          <strong>Пароль</strong>
        </label>
        <input
          id="sign-in-password"
          name="password"
          type="password"
          autoComplete="current-password"
          required
          maxLength={1024}
          placeholder="Пароль"
        />
      </div>

      <div className="am-form__row">
        <button type="submit" className="am-button">
          Войти
        </button>
      </div>

      <p className="am-form__hint">
        Пароль уходит на сервер этого приложения и обменивается на пропуск там же. В браузер
        пропуск не попадает и в хранилище браузера не кладётся: сюда возвращается только
        непрозрачный номер сеанса, недоступный сценариям страницы.
      </p>

      {refusal !== null && refusal !== undefined ? (
        <div data-sign-in-refusal={refusal}>
          <ErrorState title="Вход не выполнен" detail={signInRefusalMessage(refusal)} />
        </div>
      ) : null}
    </form>
  );
}
