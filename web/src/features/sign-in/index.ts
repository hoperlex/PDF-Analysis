/**
 * Public API of the `sign-in` feature slice.
 *
 * The two forms and the vocabulary of the exchange. Nothing here holds a credential: the
 * credential lives in the Node process, in `app/bff/session/store.ts`, and this slice
 * knows only the two addresses to post to and the four ways the exchange can refuse.
 */

export type { SignInRefusal } from './model/exchange';
export {
  SESSION_CLOSE_PATH,
  SESSION_OPEN_PATH,
  SIGN_IN_LANDING_PATH,
  SIGN_IN_PATH,
  SIGN_IN_REFUSALS,
  SIGN_IN_REFUSAL_PARAM,
  isSignInRefusal,
  signInRefusalMessage,
  signInRefusalUrl,
} from './model/exchange';

export type { SignInFormProps } from './ui/sign-in-form';
export { SignInForm } from './ui/sign-in-form';

export type { SignOutFormProps } from './ui/sign-out-form';
export { SignOutForm } from './ui/sign-out-form';
