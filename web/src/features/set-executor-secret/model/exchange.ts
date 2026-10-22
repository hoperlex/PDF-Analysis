/**
 * The executor-secret seam as the browser sees it: one address per connection and a closed set
 * of outcomes (`EXEC-HTTP-01`).
 *
 * ## Why this mirrors `change-password` rather than using the generated client
 *
 * `setExecutorSecret` is in the generated client, and **nothing in `web/src` calls it**
 * (`web/tests/unit/workers/executor-secret-door.test.ts` scans for the name). A `fetch` with a
 * JSON body would make the key a JavaScript string: in a React state, in a component that
 * ships to the browser, one careless dependency or error report away from leaving the page. A
 * plain `<form method="post">` never gives it to JavaScript at all, so the form is a server
 * component with no client directive and no handler, and the BFF door
 * (`/bff/v1/executor-secret/<connection_id>`) forwards the key from the Node process.
 *
 * ## Why one closed set covers the success too
 *
 * A redirect has no body, so every answer — including "it worked" — has to survive as an
 * address. One parameter, one validator and one translation function cannot disagree.
 */

/** The screen that offers the form, and takes the redirect. */
export const EXECUTOR_SECRET_SCREEN = '/workers';

/** The query parameters the screen reads: which tab, which connection, how the post ended. */
export const EXECUTOR_SECRET_TAB_PARAM = 'tab';
export const EXECUTOR_SECRET_CONNECTION_PARAM = 'connection';
export const EXECUTOR_SECRET_OUTCOME_PARAM = 'secret';

/**
 * The BFF mount, written as the address it is, for the reasons `change-password` gives:
 * `NEXT_PUBLIC_API_BASE_URL` may be an absolute origin, and posting a key past the one
 * process allowed to hold the credential is the thing this design exists to avoid.
 */
const BFF_MOUNT = '/bff/v1';
const SECRET_SEGMENT = 'executor-secret';

/** The pattern of `ExecutorConnectionId` in the contract. */
const CONNECTION_ID = /^exc_[0-9A-HJKMNP-TV-Z]{26}$/;

export function isExecutorConnectionId(value: unknown): value is string {
  return typeof value === 'string' && CONNECTION_ID.test(value);
}

/** POST here to set the key of one connection. Form-encoded. */
export function executorSecretSubmitPath(connectionId: string): string {
  return `${BFF_MOUNT}/${SECRET_SEGMENT}/${connectionId}`;
}

/** The address the key form is offered at. */
export function executorSecretScreenUrl(connectionId: string): string {
  return `${EXECUTOR_SECRET_SCREEN}?${EXECUTOR_SECRET_TAB_PARAM}=connections&${EXECUTOR_SECRET_CONNECTION_PARAM}=${connectionId}`;
}

/** Every way the post can end, success included. */
export const EXECUTOR_SECRET_OUTCOMES = [
  'saved',
  'validation',
  'forbidden',
  'not_found',
  'conflict',
  'unavailable',
  'unconfigured',
  'upstream',
] as const;

export type ExecutorSecretOutcome = (typeof EXECUTOR_SECRET_OUTCOMES)[number];

/** True for exactly the values above, so a hand-typed query string renders nothing. */
export function isExecutorSecretOutcome(value: string | null | undefined): value is ExecutorSecretOutcome {
  return typeof value === 'string' && (EXECUTOR_SECRET_OUTCOMES as readonly string[]).includes(value);
}

export function isExecutorSecretSuccess(outcome: ExecutorSecretOutcome): boolean {
  return outcome === 'saved';
}

/** The sentence an administrator reads. The machine value stays on the `data-` attribute. */
export function executorSecretMessage(outcome: ExecutorSecretOutcome): string {
  switch (outcome) {
    case 'saved':
      return (
        'Ключ сохранён и запечатан: его нельзя прочитать обратно, видны только последние четыре ' +
        'символа. Нажмите «Проверить», чтобы убедиться, что подключение его принимает.'
      );
    case 'validation':
      return (
        'Ключ не сохранён: поле пустое, слишком короткое или слишком длинное, либо форму ' +
        'отправила другая страница. Введите ключ ещё раз.'
      );
    case 'forbidden':
      return 'Ключ не сохранён: вводить ключи подключений может только администратор.';
    case 'not_found':
      return 'Ключ не сохранён: такого подключения нет. Обновите список подключений.';
    case 'conflict':
      return (
        'Ключ не сохранён: подключение в архиве или у него ещё нет настроек. Сначала сохраните ' +
        'настройки подключения.'
      );
    case 'unavailable':
      return (
        'Ключ не сохранён: на стенде не настроено запечатывание секретов. Это вопрос к тому, ' +
        'кто разворачивал стенд.'
      );
    case 'unconfigured':
      return (
        'Ключ не сохранён: это развёртывание не настроено на обмен данными с сервером. Запрос ' +
        'никуда не отправлен; это вопрос к тому, кто разворачивал стенд.'
      );
    case 'upstream':
      return (
        'Ключ не сохранён: сервер не дал ответа, который ожидался. Введите ключ ещё раз; ' +
        'прежний ключ, если он был, остался прежним.'
      );
  }
}
