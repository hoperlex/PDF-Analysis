/**
 * Public API of the `set-executor-secret` feature slice (`EXEC-HTTP-01`).
 *
 * The form and the vocabulary of the post. Nothing here holds a key: the credential lives in
 * the Node process, in `app/bff/session/store.ts`, and this slice knows only the one address to
 * post to and the eight ways the post can end. `setExecutorSecret` is deliberately **not**
 * wrapped in a mutation hook: a hook would make the key a JavaScript value.
 */

export type { ExecutorSecretOutcome } from './model/exchange';
export {
  EXECUTOR_SECRET_CONNECTION_PARAM,
  EXECUTOR_SECRET_OUTCOMES,
  EXECUTOR_SECRET_OUTCOME_PARAM,
  EXECUTOR_SECRET_SCREEN,
  EXECUTOR_SECRET_TAB_PARAM,
  executorSecretMessage,
  executorSecretScreenUrl,
  executorSecretSubmitPath,
  isExecutorConnectionId,
  isExecutorSecretOutcome,
  isExecutorSecretSuccess,
} from './model/exchange';

export type { SetExecutorSecretFormProps } from './ui/set-executor-secret-form';
export { SetExecutorSecretForm } from './ui/set-executor-secret-form';
