/**
 * The two authorization refusals, as one wording every screen shares.
 *
 * Before `W15-AUTH` neither code had a branch anywhere in `web/src`: every classifier's
 * `switch` fell through to `default: 'server_error'`, so a 401 rendered as "the request
 * failed on the server". That sentence sends an operator to look at the API — which is
 * working perfectly, and is refusing correctly. The credential is the thing to look at,
 * and the screen has to say so.
 *
 * The wording lives here rather than in each classifier because five copies of a sentence
 * about a credential drift into five different diagnoses of the same fact. What varies
 * per screen is only what the operator was trying to do, which each classifier supplies as
 * its own title.
 *
 * Neither is retryable and the catalog says so — `contracts/domain/v1/error-codes.json`
 * pins `retryable: false` on both — so no screen offers a retry button for either. A
 * button that re-sends the same credential to the same refusal teaches the operator that
 * buttons are noise.
 */

import type { ErrorCode } from './generated/types.gen';
import { ApiError } from './errors';

/** The `authorization` category of the catalog, as the eighteen operations can return it. */
export const AUTHORIZATION_ERROR_CODES = ['authentication_required', 'permission_denied'] as const;

export type AuthorizationErrorCode = (typeof AUTHORIZATION_ERROR_CODES)[number];

/** Compile-time proof both codes are in the generated catalog. */
const _authorizationCodesAreContractCodes: readonly ErrorCode[] = AUTHORIZATION_ERROR_CODES;
void _authorizationCodesAreContractCodes;

/**
 * `authentication_required`.
 *
 * The detail covers both halves on purpose. From the browser the two are the same event —
 * the deployment's credential is absent, or it is present and the API does not accept it —
 * and the API is required not to tell them apart: the 401 "carries no hint about the
 * addressed resource". Naming both is what makes the sentence actionable instead of
 * merely accurate.
 */
export const AUTHENTICATION_REQUIRED_DETAIL =
  'API не принял учётные данные для этого запроса. Либо в этом развёртывании они не ' +
  'настроены, либо предъявляемые API не принимает. Ничего не применено, и повтор отправит ' +
  'те же учётные данные к тому же отказу.';

/** `permission_denied`. The credential was accepted; the subject is not allowed this. */
export const PERMISSION_DENIED_DETAIL =
  'Учётные данные приняты, но эта операция над этим ресурсом им не разрешена. ' +
  'Авторизацию решает API, и этот экран её выдать не может. ' +
  'Ничего не применено.';

/** The shared sentence for one of the two codes. */
export function authorizationDetail(code: AuthorizationErrorCode): string {
  return code === 'authentication_required'
    ? AUTHENTICATION_REQUIRED_DETAIL
    : PERMISSION_DENIED_DETAIL;
}

/** True for exactly the two catalog codes above. */
export function isAuthorizationErrorCode(value: ErrorCode): value is AuthorizationErrorCode {
  return (AUTHORIZATION_ERROR_CODES as readonly string[]).includes(value);
}

/** True when the thrown failure is an `ApiError` carrying one of the two codes. */
export function isAuthorizationFailure(value: unknown): boolean {
  return value instanceof ApiError && isAuthorizationErrorCode(value.errorCode);
}
