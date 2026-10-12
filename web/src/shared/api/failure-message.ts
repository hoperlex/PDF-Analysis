/**
 * The one Russian reading of a failed request for the identity screens (`C-23`).
 *
 * `ApiError.message` is `"<error_code>: <the API's English message>"` and is never a sentence
 * for a reviewer. Before this module four mappers each wrote their own answer — the user and
 * registration entities, the profile form and the home tiles — and two of them reported
 * *anything* that was not an `ApiError` as a transport failure, including a client defect that
 * had nothing to do with the network. Here each thrown value gets exactly one honest kind:
 *
 *   - an `ApiError` is its catalog code, worded by `catalogMessage` (or the shared
 *     authorization sentence for the two authorization codes), unless the caller has a more
 *     precise sentence for that code on its own screen;
 *   - an `UnrecognizedApiError` is a code this client does not know, said so;
 *   - a `TransportError` is a request that produced no envelope, said in one fixed sentence
 *     (its own message names the operation and the HTTP status, which are for an operator);
 *   - anything else is an **unexpected** client-side failure — not a transport failure, which
 *     it was not shown to be. Its message is never printed: a thrown value can carry a path,
 *     a key or an upstream answer.
 *
 * `detail` is the only text a screen renders; `kind` goes on a `data-` attribute beside it.
 */

import type { ErrorCode } from './generated/types.gen';
import { AUTHENTICATION_REQUIRED_DETAIL, PERMISSION_DENIED_DETAIL } from './authorization';
import { catalogMessage } from './catalog-message';
import { ApiError, TransportError, UnrecognizedApiError } from './errors';

/** What kind of failure it was: a catalog code, or one of the three non-envelope kinds. */
export type FailureKind = ErrorCode | 'unrecognized' | 'transport' | 'unexpected';

export interface FailureMessage {
  readonly kind: FailureKind;
  /** The Russian sentence a screen renders. Never a thrown value's own message. */
  readonly detail: string;
  readonly correlationId: string | null;
  /** The catalog code when the failure was an `ApiError`, otherwise `null`. */
  readonly errorCode: ErrorCode | null;
  readonly retryable: boolean;
}

/** A screen's own sentences for the codes it can say more precisely about. */
export type FailureWording = Readonly<Partial<Record<ErrorCode, string>>>;

/** The sentence for a thrown value this client does not recognise as a request failure. */
export const UNEXPECTED_FAILURE_DETAIL =
  'Непредвиденная ошибка в приложении: ответ не удалось обработать. Ничего не изменено; повторите попытку, а если ошибка повторится, сообщите администратору.';

/** The sentence for a request that produced no readable answer. */
export const TRANSPORT_FAILURE_DETAIL =
  'Запрос не дошёл до сервера или его ответ не удалось прочитать. Ничего не изменено; повторите попытку.';

/** The sentence for an envelope whose code this client's contract does not declare. */
export function unrecognizedFailureDetail(rawErrorCode: string): string {
  return `Код ошибки «${rawErrorCode}» этому клиенту не знаком. Повтор не выполнялся.`;
}

/** The Russian sentence for a catalog code, before any screen-specific wording. */
function codeDetail(code: ErrorCode): string {
  if (code === 'authentication_required') return AUTHENTICATION_REQUIRED_DETAIL;
  if (code === 'permission_denied') return PERMISSION_DENIED_DETAIL;
  return catalogMessage(code);
}

/**
 * Classify anything a request (or the code around it) threw, and say it in Russian.
 *
 * `wording` lets a screen keep its own sentence for a code it knows more about (the profile
 * form's `validation_failed`, say); every other code falls back to the shared reading.
 */
export function failureMessage(error: unknown, wording: FailureWording = {}): FailureMessage {
  if (error instanceof ApiError) {
    return {
      kind: error.errorCode,
      detail: wording[error.errorCode] ?? codeDetail(error.errorCode),
      correlationId: error.correlationId,
      errorCode: error.errorCode,
      retryable: error.retryable,
    };
  }
  if (error instanceof UnrecognizedApiError) {
    return {
      kind: 'unrecognized',
      detail: unrecognizedFailureDetail(error.rawErrorCode),
      correlationId: error.correlationId,
      errorCode: null,
      retryable: false,
    };
  }
  if (error instanceof TransportError) {
    return {
      kind: 'transport',
      detail: TRANSPORT_FAILURE_DETAIL,
      correlationId: error.correlationId,
      errorCode: null,
      retryable: error.retryable,
    };
  }
  return {
    kind: 'unexpected',
    detail: UNEXPECTED_FAILURE_DETAIL,
    correlationId: null,
    errorCode: null,
    retryable: false,
  };
}
