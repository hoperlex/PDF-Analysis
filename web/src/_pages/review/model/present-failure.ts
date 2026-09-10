/**
 * Turn a thrown transport failure into `ErrorState` props.
 *
 * One place, because the rule it encodes is easy to get wrong in five places
 * independently: **`retryable` comes from the envelope, never from the HTTP status**
 * (seam §4.4). A widget that decided for itself would eventually decide from a 503, and
 * offering "try again" for a refusal the contract calls terminal teaches the reviewer that
 * the button is noise.
 *
 * So `onRetry` is attached only when the failure says it may be retried. `UnrecognizedApiError`
 * never gets one by construction — it is an explicit state meaning the server is ahead of
 * this client, and retrying an unrecognized code is guessing.
 *
 * The widgets take `ErrorStateProps` rather than a raw error precisely so this mapping
 * happens once, at the page, and the widgets stay pure and DOM-free for testing.
 *
 * This module would be a better fit in `shared/ui` next to `ErrorState` itself, and it is
 * reported as a seam gap rather than added there: `web/src/shared/**` is frozen at the
 * Gate A commit and is not `B8`'s to edit.
 */

import { ApiError, ApiFailure, UnrecognizedApiError } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';

export interface PresentFailureOptions {
  /** What the user was trying to see or do, in their words. */
  readonly title: string;
  /** Offered only when the failure is retryable. */
  readonly onRetry?: (() => void) | undefined;
  readonly retryLabel?: string | undefined;
}

export function presentFailure(error: unknown, options: PresentFailureOptions): ErrorStateProps {
  const { title, onRetry, retryLabel } = options;

  if (error instanceof UnrecognizedApiError) {
    return {
      title,
      detail:
        'The server returned an error code this client does not recognize. Nothing was ' +
        'retried. Report the correlation id below.',
      correlationId: error.correlationId,
    };
  }

  if (error instanceof ApiError) {
    return {
      title,
      // The envelope message is contract-guaranteed caller-safe: no path, key, URL,
      // credential, token, prompt, payload, query or stack content.
      detail: `${error.errorCode}: ${error.envelope.message}`,
      correlationId: error.correlationId,
      ...(error.retryable && onRetry !== undefined ? { onRetry, retryLabel } : {}),
    };
  }

  if (error instanceof ApiFailure) {
    return {
      title,
      detail: error.message,
      correlationId: error.correlationId,
      ...(error.retryable && onRetry !== undefined ? { onRetry, retryLabel } : {}),
    };
  }

  return {
    title,
    detail: 'An error outside the API contract occurred. Nothing was retried.',
    correlationId: null,
  };
}

/** `presentFailure` when there is a failure, `null` when there is not. */
export function presentFailureOrNull(
  error: unknown,
  options: PresentFailureOptions,
): ErrorStateProps | null {
  if (error === null || error === undefined) return null;
  return presentFailure(error, options);
}
