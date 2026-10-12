/**
 * Public API of the `sign-in` feature slice.
 *
 * The credentials form and the vocabulary of the exchange (the way out is the frame's
 * account menu, which posts to `SESSION_CLOSE_PATH`). Nothing here holds a credential: the
 * credential lives in the Node process, in `app/bff/session/store.ts`, and this slice
 * knows only the two addresses to post to and the six ways the exchange can refuse.
 */

export type { SignInRefusal } from './model/exchange';
export {
  SESSION_CLOSE_PATH,
  SESSION_OPEN_PATH,
  SIGN_IN_LANDING_PATH,
  SIGN_IN_NEXT_FIELD,
  SIGN_IN_PATH,
  SIGN_IN_REFUSALS,
  SIGN_IN_REFUSAL_PARAM,
  isSignInRefusal,
  signInRefusalMessage,
  signInRefusalUrl,
} from './model/exchange';

export type { SignInFormProps } from './ui/sign-in-form';
export { SignInForm } from './ui/sign-in-form';
