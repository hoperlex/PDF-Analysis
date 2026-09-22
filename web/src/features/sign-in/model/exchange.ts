/**
 * The sign-in seam as the browser sees it: two addresses and a closed set of refusals.
 *
 * ## Why the form posts instead of calling the client
 *
 * Every other write in this application goes through the generated client: the browser
 * holds the request, reads the answer and renders it. Sign-in deliberately does not.
 *
 * The password is the reason. A `fetch` with a JSON body means the password exists as a
 * JavaScript string, in a React state, in a component that is part of the browser bundle —
 * and from there it is one careless dependency, one error report, one `console` call away
 * from leaving the page. A plain `<form method="post">` never gives it to JavaScript at
 * all: the browser encodes the fields and navigates, and the only process that ever holds
 * the password is the Next server that receives the POST. The sign-in screen therefore
 * ships **no client component and no client JavaScript**.
 *
 * The answer is a `303` back to a screen, which is also why no code here decodes a body.
 * Nothing this seam returns carries the token: the token is recorded in
 * `app/bff/session/store.ts` and the browser receives only an opaque cookie.
 *
 * ## Why the refusal is a code in the query string
 *
 * A redirect has no body, so the refusal has to survive as an address. It is a **closed
 * set of machine values**, translated for the screen by `signInRefusalMessage` and carried
 * on a `data-` attribute beside the sentence — the owner's 2026-09-22 ruling, the same
 * shape the run-state badges use.
 */

/** The screen that offers the exchange. */
export const SIGN_IN_PATH = '/login';

/** Where a completed sign-in lands. The application's own front door. */
export const SIGN_IN_LANDING_PATH = '/projects';

/**
 * The BFF mount, written as the address it is.
 *
 * Not read from `NEXT_PUBLIC_API_BASE_URL` and not imported from
 * `shared/api/credentialed-forward`: the first is the base the *generated client* was
 * configured with and may legitimately be an absolute origin, and posting a password to an
 * absolute origin would be posting it past the one process allowed to hold it. The second
 * is a server-only module, and this one renders. So the mount is spelled here, and
 * `web/tests/unit/session/bff-session.test.ts` asserts it is the mount the route tree
 * actually serves — an address, checked against the thing at that address.
 */
const BFF_MOUNT = '/bff/v1';

/** POST here to exchange a login and a password for a session. Form-encoded. */
export const SESSION_OPEN_PATH = `${BFF_MOUNT}/session`;

/** POST here to end the session. The server forgets the credential; the cookie is cleared. */
export const SESSION_CLOSE_PATH = `${BFF_MOUNT}/session/end`;

/** The query parameter the redirect carries a refusal in. */
export const SIGN_IN_REFUSAL_PARAM = 'refusal';

/**
 * Every way the exchange can refuse.
 *
 * `credentials` is deliberately one value and not two. The API is required not to say
 * whether the login or the password was the wrong half, and a screen that said so would
 * put back the account-enumeration oracle the API refuses to be: an attacker who can tell
 * "no such user" from "wrong password" can harvest logins at leisure.
 */
export const SIGN_IN_REFUSALS = ['credentials', 'validation', 'unconfigured', 'upstream'] as const;

export type SignInRefusal = (typeof SIGN_IN_REFUSALS)[number];

/** True for exactly the four values above, so a hand-typed query string renders nothing. */
export function isSignInRefusal(value: string | null | undefined): value is SignInRefusal {
  return typeof value === 'string' && (SIGN_IN_REFUSALS as readonly string[]).includes(value);
}

/** The sentence a reviewer reads. The machine value stays on the `data-` attribute. */
export function signInRefusalMessage(refusal: SignInRefusal): string {
  switch (refusal) {
    case 'credentials':
      return (
        'Войти не удалось: такая пара имени пользователя и пароля не принята. ' +
        'Какая из двух частей не подошла, не сообщается — иначе по одному лишь ответу ' +
        'можно было бы перебирать имена. Ничего не изменено.'
      );
    case 'validation':
      return 'Заполните оба поля: имя пользователя и пароль. Запрос никуда не отправлен.';
    case 'unconfigured':
      return (
        'Войти нельзя: это развёртывание не настроено на обмен учётными данными. ' +
        'Запрос никуда не отправлен; это вопрос к тому, кто разворачивал стенд.'
      );
    case 'upstream':
      return (
        'Обмен учётных данных не состоялся: сервер не получил ответа, который он ожидал. ' +
        'Ничего не изменено, попытку можно повторить.'
      );
  }
}

/** The address the exchange redirects to when it refuses. */
export function signInRefusalUrl(refusal: SignInRefusal): string {
  return `${SIGN_IN_PATH}?${SIGN_IN_REFUSAL_PARAM}=${refusal}`;
}
