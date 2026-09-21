'use client';

/**
 * Choose one PDF and upload it.
 *
 * Two refusals live on this screen and they are deliberately different states:
 *
 *   the pre-check refusal   the browser can see the file is not a PDF, is empty, or is
 *                           over 25 MiB. No request is sent, and `UnsupportedState` says
 *                           which rule was broken with no retry offered, because no
 *                           retry of the same file can help.
 *   the server refusal      everything the browser cannot see — encryption, page count,
 *                           a missing text layer — comes back as `validation_failed`
 *                           with the server's own reason, and is rendered as that reason
 *                           rather than as "upload failed".
 *
 * A checksum failure (`storage_integrity_error`) is a third, separate state, and a
 * dependency outage a fourth. None of them is a spinner, and none is a success.
 */

import { useState } from 'react';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { ErrorState, LoadingState, UnsupportedState } from '@/shared/ui';
import { useIntentKey } from '@/shared/lib';
import type { UploadFailure, UploadPrecheckProblem } from '@/entities/document-version';
import {
  PC01_UPLOAD_ENVELOPE,
  classifyUploadFailure,
  formatBytes,
  precheckProblemMessage,
  precheckUploadFile,
} from '@/entities/document-version';

import { useUploadDocument } from '../model/use-upload-document';

export interface UploadDocumentFormProps {
  readonly projectUid: ProjectUid;
  /** Called with the published version, so the screen can offer to start a run. */
  readonly onUploaded?: ((version: DocumentVersion) => void) | undefined;
}

export function UploadDocumentForm({ projectUid, onUploaded }: UploadDocumentFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [displayTitle, setDisplayTitle] = useState('');
  const [precheck, setPrecheck] = useState<UploadPrecheckProblem | null>(null);

  // The signature is the intent: this file, at this size, with this title. Two presses of
  // "Upload" over the same choice are one command; choosing another file is another one.
  const signature = `upload:${projectUid}:${file?.name ?? ''}:${file?.size ?? 0}:${
    file?.lastModified ?? 0
  }:${displayTitle.trim()}`;
  const idempotencyKey = useIntentKey(signature);
  const mutation = useUploadDocument();

  const choose = (chosen: File | null) => {
    mutation.reset();
    setFile(chosen);
    setPrecheck(chosen === null ? null : precheckUploadFile(chosen));
  };

  const send = () => {
    if (file === null || precheck !== null) return;
    mutation.mutate(
      { projectUid, file, displayTitle, idempotencyKey },
      { onSuccess: (version) => onUploaded?.(version) },
    );
  };

  const failure: UploadFailure | null =
    mutation.error === null || mutation.error === undefined
      ? null
      : classifyUploadFailure(mutation.error);

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        send();
      }}
    >
      <div style={{ display: 'grid', gap: '0.5rem', maxWidth: '38rem' }}>
        <label htmlFor="upload-file">
          <strong>PDF</strong>
        </label>
        <input
          id="upload-file"
          name="file"
          type="file"
          accept={PC01_UPLOAD_ENVELOPE.mediaType}
          onChange={(event) => choose(event.target.files?.[0] ?? null)}
        />

        <label htmlFor="upload-title">
          Display title <em>(необязательно; не идентификатор)</em>
        </label>
        <input
          id="upload-title"
          name="display_title"
          type="text"
          value={displayTitle}
          onChange={(event) => setDisplayTitle(event.target.value)}
          style={{ padding: '0.4rem 0.5rem' }}
        />

        {file !== null ? (
          <p>
            Chosen: {file.name} · {formatBytes(file.size)}
          </p>
        ) : null}

        <div>
          <button
            type="submit"
            className="am-button"
            disabled={file === null || precheck !== null || mutation.isPending}
          >
            Upload
          </button>
        </div>
      </div>

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

      {mutation.isPending ? <LoadingState what="the upload" /> : null}

      {failure !== null && failure.presentation === 'unsupported' ? (
        <UnsupportedState
          title={failure.title}
          detail={
            <>
              <p data-upload-failure={failure.kind}>{failure.detail}</p>
              {failure.correlationId === null ? null : (
                <p>
                  Correlation id <code>{failure.correlationId}</code>
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
                onRetry: send,
                retryLabel: 'Повторить с тем же ключом',
              }
            : {})}
        />
      ) : null}
    </form>
  );
}
