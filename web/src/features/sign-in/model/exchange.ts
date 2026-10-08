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

/**
 * Where a completed sign-in lands when it carries no `next`: the application's front door.
 *
 * `/` since `W50-PLAN.md` §3.2, which moved it from `/projects` together with the BFF's own
 * copy (`AFTER_SIGN_IN` in `web/src/app/bff/v1/[...path]/route.ts`) and the journey's
 * `session.lands_on`. A default credential still lands on `/account/password`.
 */
export const SIGN_IN_LANDING_PATH = '/';

/**
 * The form field that carries the address a guest was sent to sign in from.
 *
 * Filled by the screen with a value the screen registry's `safeReturnPath` has already
 * accepted, and validated **again** by the BFF before it redirects there: the field is part of
 * a form the browser posts, so the server never trusts what comes back in it.
 */
export const SIGN_IN_NEXT_FIELD = 'next';

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
 * **A mirror, held to its copy by a test.** The route handler that answers the form,
 * `web/src/app/bff/v1/[...path]/route.ts`, declares the same values as its own
 * `type Refusal` rather than importing this module (its comment says why), and
 * `web/tests/unit/session/refusal-mirrors.test.ts` reads that union out of the handler's
 * source and asserts the two sets are equal. A value added on one side alone is red there.
 *
 * `credentials` is deliberately one value and not two. The API is required not to say
 * whether the login or the password was the wrong half, and a screen that said so would
 * put back the account-enumeration oracle the API refuses to be: an attacker who can tell
 * "no such user" from "wrong password" can harvest logins at leisure.
 *
 * **The account's throttle is still not a value here (`W40-LIMIT`), and `throttled` below is
 * not that throttle.** `W40-LIMIT` added a per-**account** rate limit and lockout to the
 * exchange and decided not to name it on this screen. The API answers a shut account with
 * exactly the `401 authentication_required` it answers a wrong password with, so this tier
 * could not tell them apart if it wanted to — and it must not want to: a refusal saying an
 * account is throttled would say "this account exists and somebody is attacking it right
 * now" to anybody who can type a login. That decision stands. What the `credentials`
 * sentence gained instead is a statement of the **policy**, which is public knowledge and
 * says nothing about any particular account: it is shown on every credentials refusal,
 * whether or not the account in front of it is anywhere near its allowance. A reviewer who
 * has mistyped five times and then types their real password needs to be told that waiting
 * is the answer, or they will conclude their password is broken — and the screen is the
 * only place that can be said.
 *
 * `throttled` (`W49-BFF-01`, `W49-PLAN.md` §3.5) is a per-**client** limit: the web tier's
 * guest bucket on this form and the registration form, keyed by the caller's address behind
 * the proxy. It refuses before any login is read, so it comes back the same whichever login
 * was typed, or none — it describes the person reading it and says nothing about any account.
 *
 * `pending` (`R-56` and its 2026-10-06 addendum) is the one registration status sign-in
 * shows: the pair proves an application an administrator has not decided yet. A rejected or
 * approved application proves nothing at sign-in and is answered `credentials`, as if none
 * existed. A stranger who types `?refusal=pending` by hand sees the pending sentence and
 * learns nothing about any application, which is why no reason and no notice ever travels in
 * this parameter.
 */
export const SIGN_IN_REFUSALS = [
  'credentials',
  'validation',
  'unconfigured',
  'upstream',
  'pending',
  'throttled',
] as const;

export type SignInRefusal = (typeof SIGN_IN_REFUSALS)[number];

/** True for exactly the six values above; an unknown query value renders a typed fault. */
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
        'можно было бы перебирать имена. Ничего не изменено. ' +
        'После нескольких неудачных попыток подряд вход в учётную запись ненадолго ' +
        'приостанавливается, и тогда не принимается даже верный пароль: подождите ' +
        'несколько минут и попробуйте снова.'
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
    case 'pending':
      return (
        'Заявка на регистрацию ещё не рассмотрена: войти можно будет, когда администратор ' +
        'её одобрит. Подавать заявку повторно не нужно.'
      );
    case 'throttled':
      return (
        'Слишком много попыток входа и подачи заявок за короткое время. Ничего не изменено: ' +
        'подождите немного и попробуйте снова. Это ограничение относится к подключению, ' +
        'с которого идут попытки, а не к учётной записи.'
      );
  }
}

/** The address the exchange redirects to when it refuses. */
export function signInRefusalUrl(refusal: SignInRefusal): string {
  return `${SIGN_IN_PATH}?${SIGN_IN_REFUSAL_PARAM}=${refusal}`;
}
