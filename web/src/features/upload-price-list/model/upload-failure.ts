/**
 * How a failed price-list upload is said (`WEB-FOLLOWUPS-02`, `D-195`).
 *
 * Two readings, and the choice between them is the point:
 *
 *   - An answer from the WEB SERVER in front of the API (a 413 from its own body-size limit, a
 *     502, 503 or 504) is not an `ErrorEnvelope`, so the transport can only report "the body
 *     is not an envelope", an operator's note. The price-list entity read that as a transport
 *     failure and told the user the request "did not reach the server" and to try again,
 *     which for a 413 is a file refused again. The document upload already says these in
 *     Russian through `classifyUploadFailure`; this feature uses the same reading, with the
 *     price list's own size limit in the 413 sentence (10 MiB, not the document envelope's).
 *   - Everything else is the price-list entity's reading, which knows the file constraints of
 *     `uploadPriceList` (`UPLOAD_CONSTRAINT_TEXT`) and says what to do about each.
 *
 * The result is the `FailureMessage` the form already renders, so no screen changes shape.
 */

import { classifyUploadFailure } from '@/entities/document-version';
import { uploadFailureMessage } from '@/entities/price-list';
import type { FailureMessage } from '@/shared/api/failure-message';

/** The largest file the API accepts, as the user reads it. */
export const PRICE_LIST_LIMIT_LABEL = '10 MiB';

export function priceListUploadFailure(error: unknown): FailureMessage {
  const web = classifyUploadFailure(error, { limitLabel: PRICE_LIST_LIMIT_LABEL });
  if (web.kind === 'edge_too_large' || web.kind === 'edge_unavailable') {
    return {
      kind: 'transport',
      detail: web.detail,
      correlationId: web.correlationId,
      errorCode: null,
      retryable: web.retryable,
    };
  }
  return uploadFailureMessage(error);
}
