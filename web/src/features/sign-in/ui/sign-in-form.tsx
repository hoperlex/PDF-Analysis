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
 * The one script the form carries is `shared/ui`'s `SubmitLock` (`C-22`): an island that
 * disables the submit button once the browser posts, so a second press cannot post the
 * credentials twice. It reads no field.
 *
 * The refusal is rendered through `shared/ui`'s `ErrorState` — the same block every other
 * screen uses for a failure the server will not change on retry — and carries its machine
 * value on `data-sign-in-refusal` beside the Russian sentence. It stands above the fields,
 * where a reader who was sent back looks first.
 */

import { ErrorState } from '@/shared/ui';
import { SubmitLock } from '@/shared/ui/submit-lock';

import type { SignInRefusal } from '../model/exchange';
import { SESSION_OPEN_PATH, SIGN_IN_NEXT_FIELD, signInRefusalMessage } from '../model/exchange';

import styles from './sign-in-form.module.css';

export interface SignInFormProps {
  /** The refusal the previous attempt was redirected back with, if there was one. */
  readonly refusal?: SignInRefusal | null | undefined;
  /**
   * Where to go once signed in: an address the route has already passed through the screen
   * registry's `safeReturnPath`, or nothing. Posted back in a hidden field; the BFF validates
   * it again before it redirects there.
   */
  readonly next?: string | null | undefined;
}

export function SignInForm({ refusal, next }: SignInFormProps) {
  const action = next ? `${SESSION_OPEN_PATH}?next=${encodeURIComponent(next)}` : SESSION_OPEN_PATH;
  return (
    <form className={styles.form} method="post" action={action}>
      <SubmitLock />
      {typeof next === 'string' && next.length > 0 ? (
        <input type="hidden" name={SIGN_IN_NEXT_FIELD} value={next} />
      ) : null}

      {refusal !== null && refusal !== undefined ? (
        <div data-sign-in-refusal={refusal}>
          <ErrorState title="Вход не выполнен" detail={signInRefusalMessage(refusal)} />
        </div>
      ) : null}

      <div className={styles.field}>
        <label htmlFor="sign-in-login">Адрес электронной почты</label>
        <input
          id="sign-in-login"
          name="login"
          type="text"
          autoComplete="username"
          required
          maxLength={320}
          placeholder="Почта или прежний логин"
        />
      </div>

      <div className={styles.field}>
        <label htmlFor="sign-in-password">Пароль</label>
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

      <button type="submit" className={`am-button ${styles.submit}`}>
        Войти
      </button>

      <p className={styles.hint}>
        Пароль проверяет сервер приложения. Страница не хранит ни пароль, ни пропуск и не
        обращается к хранилищу браузера.
      </p>
    </form>
  );
}
