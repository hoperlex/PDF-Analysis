/**
 * The key form of one connection (`EXEC-HTTP-01`).
 *
 * **A server component, and here that is load-bearing.** There is no `'use client'`, no
 * `useState` and no handler: the key is typed into a plain HTML input and posted by the
 * browser itself, so it is never a JavaScript value, in a bundle, in a React tree, in an
 * error report or in `localStorage`.
 * `web/tests/unit/workers/executor-secret-door.test.ts` asserts the absence of the client
 * directive rather than trusting this paragraph. Its one script is `shared/ui`'s
 * `SubmitLock` (`C-22`), which disables the submit button once the browser posts and reads
 * no field.
 *
 * `type="password"` so the key is not shown over a shoulder, and `autoComplete="off"` so a
 * password manager does not offer to store it as a login. The key is write-only: nothing the
 * server returns carries it, and the connection's card shows its last four characters only.
 *
 * The page's idempotency key is minted here, when the page is rendered, and travels in a
 * hidden field: a form posted twice (a double click that got past the lock, a resubmit from
 * the back button) seals one secret, not two.
 *
 * The outcome of the previous post — success and refusal alike — is rendered from a closed
 * set beside its machine value on `data-executor-secret-outcome`.
 */

import { newIdempotencyKey } from '@/shared/api';
import { ErrorState } from '@/shared/ui';
import { SubmitLock } from '@/shared/ui/submit-lock';

import type { ExecutorSecretOutcome } from '../model/exchange';
import {
  executorSecretMessage,
  executorSecretSubmitPath,
  isExecutorSecretSuccess,
} from '../model/exchange';

export interface SetExecutorSecretFormProps {
  /** The connection whose key is being set; the address the form posts to carries it. */
  readonly connectionId: string;
  /** How the previous post ended, if there was one. */
  readonly outcome?: ExecutorSecretOutcome | null | undefined;
}

export function SetExecutorSecretForm({ connectionId, outcome }: SetExecutorSecretFormProps) {
  const reported = outcome ?? null;
  const fieldId = `executor-secret-${connectionId}`;
  return (
    <form
      className="am-form"
      method="post"
      action={executorSecretSubmitPath(connectionId)}
      data-executor-secret-form={connectionId}
    >
      <SubmitLock />
      <input type="hidden" name="intent" value={newIdempotencyKey()} />
      <div className="am-form__field">
        <label htmlFor={fieldId}>
          <strong>Ключ доступа к модели</strong>
        </label>
        <input
          id={fieldId}
          name="value"
          type="password"
          autoComplete="off"
          spellCheck={false}
          required
          minLength={8}
          maxLength={8192}
          placeholder="Вставьте ключ"
        />
      </div>
      <div className="am-form__row">
        <button type="submit" className="am-button">
          Сохранить ключ
        </button>
      </div>
      <p className="am-form__hint">
        Ключ привязан к адресу, для которого он введён, и запечатывается при отправке. Прочитать
        его обратно нельзя нигде: после сохранения видны только последние четыре символа, время
        и автор. Если сменить адрес подключения, прежний ключ перестанет открываться, и его
        придётся вставить заново.
      </p>
      {reported !== null ? (
        <div data-executor-secret-outcome={reported}>
          {isExecutorSecretSuccess(reported) ? (
            <p className="am-note" role="status">
              <strong>Ключ сохранён. </strong>
              {executorSecretMessage(reported)}
            </p>
          ) : (
            <ErrorState title="Ключ не сохранён" detail={executorSecretMessage(reported)} />
          )}
        </div>
      ) : null}
    </form>
  );
}
