/**
 * Public API of the `change-password` feature slice.
 *
 * The form and the vocabulary of the change. Nothing here holds a credential or a password:
 * the credential lives in the Node process, in `app/bff/session/store.ts`, and this slice
 * knows only the one address to post to and the six ways the change can end.
 */

export type { ChangePasswordOutcome } from './model/exchange';
export {
  CHANGE_PASSWORD_OUTCOMES,
  CHANGE_PASSWORD_OUTCOME_PARAM,
  CHANGE_PASSWORD_PATH,
  CHANGE_PASSWORD_SUBMIT_PATH,
  changePasswordMessage,
  changePasswordOutcomeUrl,
  isChangePasswordOutcome,
  isChangePasswordSuccess,
} from './model/exchange';

export type { ChangePasswordFormProps } from './ui/change-password-form';
export { ChangePasswordForm } from './ui/change-password-form';
