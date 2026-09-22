/**
 * The control that ends the session.
 *
 * Also a form and also a server component, for the reason the sign-in form is: pressing it
 * is a POST the browser performs, so nothing about the session is readable or forgeable
 * from a script on the page. The server deletes the row that holds the credential and
 * clears the cookie in the same answer — a logout that removed only the cookie would leave
 * a live credential in the register with nothing to reach it, which is a leak that looks
 * like a logout.
 */

import { SESSION_CLOSE_PATH } from '../model/exchange';

export interface SignOutFormProps {
  /** Who the session belongs to, as the register recorded it. */
  readonly login: string;
}

export function SignOutForm({ login }: SignOutFormProps) {
  return (
    <form className="am-form" method="post" action={SESSION_CLOSE_PATH}>
      <p className="am-note" data-session-login={login}>
        Вы вошли как <strong>{login}</strong>.
      </p>
      <div className="am-form__row">
        <button type="submit" className="am-button">
          Выйти
        </button>
      </div>
      <p className="am-form__hint">
        Пропуск хранится на сервере, а не в браузере. «Выйти» удаляет его там же, поэтому
        номер сеанса, оставшийся у браузера, после этого ничего не открывает.
      </p>
    </form>
  );
}
