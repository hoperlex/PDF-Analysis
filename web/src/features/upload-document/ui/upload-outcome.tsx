'use client';

/**
 * What an upload form shows besides itself: the pre-check refusal, the upload in flight, and
 * the server's refusal in its two presentations.
 *
 * One component for both uploads — a document's first version (`UploadDocumentForm`) and its
 * next one (`UploadDocumentVersionForm`, `W59-VERSION-UPLOAD-01`) — because the envelope, the
 * transport and every refusal are the same, so the reviewer must read the same words for the
 * same rule whichever form sent the bundle. See `upload-document-form.tsx` for why these are
 * four distinct states and none of them is a spinner or a success.
 */

import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';
import type { UploadFailure, UploadPrecheckProblem } from '@/entities/document-version';
import { precheckProblemMessage } from '@/entities/document-version';

export interface UploadOutcomeProps {
  readonly precheck: UploadPrecheckProblem | null;
  readonly pending: boolean;
  readonly failure: UploadFailure | null;
  /** Sends the same upload again under the same key. Offered only for a retryable failure. */
  readonly onRetry: () => void;
}

export function UploadOutcome({ precheck, pending, failure, onRetry }: UploadOutcomeProps) {
  return (
    <>
      {precheck !== null ? (
        <UnsupportedState
          title="Файл выходит за допустимые ограничения."
          detail={
            <>
              <p data-precheck-problem={precheck}>{precheckProblemMessage(precheck)}</p>
              <p>Ничего не отправлено. Выберите другой файл.</p>
            </>
          }
        />
      ) : null}

      {pending ? <LoadingState what="загружаемый файл" /> : null}

      {failure !== null && failure.presentation === 'unsupported' ? (
        <UnsupportedState
          title={failure.title}
          detail={
            <>
              <p data-upload-failure={failure.kind}>{failure.detail}</p>
              {failure.correlationId === null ? null : (
                <p>
                  Идентификатор корреляции <code>{failure.correlationId}</code>
                </p>
              )}
              <p>Версия не опубликована, прогон не запущен.</p>
            </>
          }
        />
      ) : null}

      {failure !== null && failure.presentation === 'error' ? (
        <ErrorState
          title={failure.title}
          detail={<span data-upload-failure={failure.kind}>{failure.detail}</span>}
          correlationId={failure.correlationId}
          {...(failure.retryable
            ? {
                onRetry,
                retryLabel: 'Повторить с тем же ключом',
              }
            : {})}
        />
      ) : null}
    </>
  );
}
