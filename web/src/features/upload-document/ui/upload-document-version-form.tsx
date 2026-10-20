'use client';

/**
 * Choose one portal bundle and upload it as the next version of this document
 * (`W59-VERSION-UPLOAD-01`).
 *
 * The same envelope, pre-check and refusals as the first upload — `UploadOutcome` renders
 * them for both forms — with two differences that are the operation's own: the document is
 * already chosen (it is this screen's), and there is no title field, because a further
 * version takes none: the document keeps its title, and the new version's stage and section
 * are confirmed by an expert on the version itself, never inherited.
 */

import { useState } from 'react';

import type { DocumentUid, DocumentVersion, ProjectUid } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';
import type { UploadFailure, UploadPrecheckProblem } from '@/entities/document-version';
import {
  PC01_UPLOAD_ENVELOPE,
  classifyUploadFailure,
  formatBytes,
  precheckUploadFile,
} from '@/entities/document-version';

import { useUploadDocumentVersion } from '../model/use-upload-document-version';
import { UploadOutcome } from './upload-outcome';

export interface UploadDocumentVersionFormProps {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  /** Called with the new version, so the screen can lead to it. */
  readonly onUploaded?: ((version: DocumentVersion) => void) | undefined;
}

export function UploadDocumentVersionForm({
  projectUid,
  documentUid,
  onUploaded,
}: UploadDocumentVersionFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [precheck, setPrecheck] = useState<UploadPrecheckProblem | null>(null);

  // The intent is this file for this document: two presses over the same choice are one
  // command, and another file is another one.
  const signature = `upload-version:${projectUid}:${documentUid}:${file?.name ?? ''}:${
    file?.size ?? 0
  }:${file?.lastModified ?? 0}`;
  const idempotencyKey = useIntentKey(signature);
  const mutation = useUploadDocumentVersion();

  const choose = (chosen: File | null) => {
    mutation.reset();
    setFile(chosen);
    setPrecheck(chosen === null ? null : precheckUploadFile(chosen));
  };

  const send = () => {
    if (file === null || precheck !== null) return;
    mutation.mutate(
      { projectUid, documentUid, file, idempotencyKey },
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
      <div className="am-form">
        <label htmlFor="upload-version-file">
          <strong>Комплект портала новой версии (ZIP)</strong>
        </label>
        <input
          id="upload-version-file"
          name="file"
          type="file"
          accept={PC01_UPLOAD_ENVELOPE.accept}
          onChange={(event) => choose(event.target.files?.[0] ?? null)}
        />

        {file !== null ? (
          <p className="am-form__chosen">
            Выбран файл: {file.name} · {formatBytes(file.size)}
          </p>
        ) : null}

        <div>
          <button
            type="submit"
            className="am-button"
            disabled={file === null || precheck !== null || mutation.isPending}
          >
            Загрузить новую версию
          </button>
        </div>
      </div>

      <UploadOutcome
        precheck={precheck}
        pending={mutation.isPending}
        failure={failure}
        onRetry={send}
      />
    </form>
  );
}
