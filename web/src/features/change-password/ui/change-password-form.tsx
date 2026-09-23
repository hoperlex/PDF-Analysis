/**
 * The password-change form.
 *
 * **A server component, and here that is load-bearing twice over.** There is no
 * `'use client'`, no `useState` and no handler: two passwords are typed into plain HTML
 * inputs and posted by the browser itself, so neither is ever a JavaScript value, in a
 * bundle, in a React tree, in an error report or in `localStorage`. One of the two is the
 * password that is about to become live.
 * `web/tests/unit/session/change-password-screen.test.ts` asserts the absence of the client
 * directive rather than trusting this paragraph, the way the sign-in screen's own test does.
 *
 * The outcome — success and refusal alike — is rendered from a closed set and carries its
 * machine value on `data-change-password-outcome` beside the Russian sentence. A refusal
 * goes through `shared/ui`'s `ErrorState`, the same block every other screen uses; the one
 * success is a note and not an `ErrorState`, because a block whose heading says a failure
 * happened is the wrong shape for the answer "it worked".
 *
 * `autoComplete` is spelled out on both fields. `current-password` and `new-password` are
 * what tell a password manager which is which; without them a manager offers to save the
 * *old* password as the new one, which would be this screen teaching a reviewer's own tools
 * to undo it.
 */

import { ErrorState } from '@/shared/ui';

import type { ChangePasswordOutcome } from '../model/exchange';
import {
  CHANGE_PASSWORD_SUBMIT_PATH,
  changePasswordMessage,
  isChangePasswordSuccess,
} from '../model/exchange';

export interface ChangePasswordFormProps {
  /** How the previous attempt ended, if there was one. */
  readonly outcome?: ChangePasswordOutcome | null | undefined;
}

export function ChangePasswordForm({ outcome }: ChangePasswordFormProps) {
  const reported = outcome ?? null;

  return (
    <form className="am-form" method="post" action={CHANGE_PASSWORD_SUBMIT_PATH}>
      <div className="am-form__field">
        <label htmlFor="change-password-current">
          <strong>Текущий пароль</strong>
        </label>
        <input
          id="change-password-current"
          name="current_password"
          type="password"
          autoComplete="current-password"
          required
          maxLength={1024}
          placeholder="Текущий пароль"
        />
      </div>

      <div className="am-form__field">
        <label htmlFor="change-password-new">
          <strong>Новый пароль</strong>
        </label>
        <input
          id="change-password-new"
          name="new_password"
          type="password"
          autoComplete="new-password"
          required
          maxLength={1024}
          placeholder="Новый пароль"
        />
      </div>

      <div className="am-form__row">
        <button type="submit" className="am-button">
          Сменить пароль
        </button>
      </div>

      <p className="am-form__hint">
        Смена пароля отзывает все выданные пропуска этой учётной записи: всё, что было
        выдано под прежним паролем, перестаёт приниматься в тот же момент. На этом
        устройстве сеанс продолжится новым пропуском; везде, где вход был выполнен раньше,
        потребуется войти заново.
      </p>

      {reported !== null ? (
        <div data-change-password-outcome={reported}>
          {isChangePasswordSuccess(reported) ? (
            <p className="am-note">
              <strong>Пароль изменён. </strong>
              {changePasswordMessage(reported)}
            </p>
          ) : (
            <ErrorState title="Пароль не изменён" detail={changePasswordMessage(reported)} />
          )}
        </div>
      ) : null}
    </form>
  );
}
