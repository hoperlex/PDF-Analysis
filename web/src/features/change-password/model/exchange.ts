/**
 * The password-change seam as the browser sees it: one address and a closed set of outcomes.
 *
 * ## Why this mirrors `sign-in` rather than using the generated client
 *
 * The same reason, for the same value. A `fetch` with a JSON body would make the password a
 * JavaScript string — in a React state, in a component that ships to the browser, one
 * careless dependency or error report away from leaving the page. A plain
 * `<form method="post">` never gives it to JavaScript at all, so this screen ships **no
 * client component and no client JavaScript**, exactly like the sign-in screen.
 *
 * Here it matters twice over: this form carries *two* passwords, and one of them is the
 * password that is about to become live.
 *
 * ## Why the address is the reserved BFF segment and not the contract path
 *
 * `POST /auth/password` answers with a **credential**. If the browser reached it through
 * the catch-all forwarder, that credential would arrive in the page — which is the defect
 * `JUDGE-SEC` drove against `issueToken` and got `200 {"token": …}` in a browser. The whole
 * `auth` segment is refused to the browser for that reason, and this seam goes through
 * `/bff/v1/session/password`, where the Node process reads the new credential, swaps it into
 * the register and returns nothing but a redirect and a cookie.
 *
 * ## Why one closed set covers the success too
 *
 * A redirect has no body, so every answer — including "it worked" — has to survive as an
 * address. Making success a member of the same closed set means one parameter, one
 * validator, one translation function and one `data-` attribute, instead of two of each
 * that can disagree. The machine value travels on `data-change-password-outcome`; the
 * Russian sentence is `changePasswordMessage`'s, the same shape the run-state badges and the
 * sign-in refusals use.
 */

/** The screen that offers the change. */
export const CHANGE_PASSWORD_PATH = '/account/password';

/**
 * The BFF mount, written as the address it is.
 *
 * Spelled here rather than read from `NEXT_PUBLIC_API_BASE_URL` or imported from
 * `shared/api/credentialed-forward`, for the two reasons `sign-in`'s copy states: the first
 * is the base the *generated client* was configured with and may be an absolute origin —
 * posting a password past the one process allowed to hold it — and the second is
 * server-only while this module renders. `web/tests/unit/session/change-password-screen.test.ts`
 * asserts it is the mount the route tree actually serves.
 */
const BFF_MOUNT = '/bff/v1';

/** POST here to change the password. Form-encoded, like the sign-in exchange. */
export const CHANGE_PASSWORD_SUBMIT_PATH = `${BFF_MOUNT}/session/password`;

/** The query parameter the redirect carries the outcome in. */
export const CHANGE_PASSWORD_OUTCOME_PARAM = 'outcome';

/**
 * Every way the change can end, success included.
 *
 * `credentials` is one value and not two for the same reason the sign-in refusal is: the API
 * answers one refusal for a wrong current password and for an account that is no longer
 * there, and a screen that separated them would re-create the oracle the API refuses to be.
 *
 * `unchanged` is refused **here**, before anything is sent, and it is also refused by the
 * API independently. Two checks and not one: the API's is the one that counts, and this one
 * means a reviewer who typed the same password twice gets a Russian sentence rather than a
 * translated API message — and no request carrying two passwords goes out for nothing.
 */
export const CHANGE_PASSWORD_OUTCOMES = [
  'changed',
  'credentials',
  'unchanged',
  'validation',
  'unconfigured',
  'upstream',
] as const;

export type ChangePasswordOutcome = (typeof CHANGE_PASSWORD_OUTCOMES)[number];

/** True for exactly the six values above, so a hand-typed query string renders nothing. */
export function isChangePasswordOutcome(
  value: string | null | undefined,
): value is ChangePasswordOutcome {
  return (
    typeof value === 'string' && (CHANGE_PASSWORD_OUTCOMES as readonly string[]).includes(value)
  );
}

/** True for the one outcome that is not a refusal. The screen renders it differently. */
export function isChangePasswordSuccess(outcome: ChangePasswordOutcome): boolean {
  return outcome === 'changed';
}

/** The sentence a reviewer reads. The machine value stays on the `data-` attribute. */
export function changePasswordMessage(outcome: ChangePasswordOutcome): string {
  switch (outcome) {
    case 'changed':
      return (
        'Пароль изменён. Все пропуска, выданные под прежним паролем, перестали ' +
        'приниматься — на этом устройстве сеанс продолжен уже новым пропуском, а все ' +
        'остальные входы прерваны и потребуют входа заново.'
      );
    case 'credentials':
      return (
        'Текущий пароль не подошёл, поэтому ничего не изменено. Пароль остался прежним, ' +
        'и ни один пропуск не отозван.'
      );
    case 'unchanged':
      return (
        'Новый пароль совпадает с текущим. Запрос никуда не отправлен: смена пароля, ' +
        'которая ничего не меняет, сообщила бы о смене там, где её не было.'
      );
    case 'validation':
      return 'Заполните оба поля: текущий пароль и новый. Запрос никуда не отправлен.';
    case 'unconfigured':
      return (
        'Сменить пароль нельзя: это развёртывание не настроено на обмен учётными ' +
        'данными. Запрос никуда не отправлен; это вопрос к тому, кто разворачивал стенд.'
      );
    case 'upstream':
      return (
        'Смена пароля не состоялась: сервер не получил ответа, который он ожидал. ' +
        'Пароль не изменён, попытку можно повторить.'
      );
  }
}

/** The address the seam redirects to, whatever the outcome. */
export function changePasswordOutcomeUrl(outcome: ChangePasswordOutcome): string {
  return `${CHANGE_PASSWORD_PATH}?${CHANGE_PASSWORD_OUTCOME_PARAM}=${outcome}`;
}
