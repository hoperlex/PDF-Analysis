'use client';

/**
 * Choose one portal bundle (a ZIP archive) and upload it.
 *
 * Two refusals live on this screen and they are deliberately different states:
 *
 *   the pre-check refusal   the browser can see the file is not a ZIP, is empty, or is
 *                           over 250 MiB. No request is sent, and `UnsupportedState` says
 *                           which rule was broken with no retry offered, because no
 *                           retry of the same file can help.
 *   the server refusal      everything the browser cannot see — the archive's members,
 *                           encryption, page count, a missing text layer — comes back
 *                           as `validation_failed` with the server's own reason, and is
 *                           rendered as that reason rather than as "upload failed".
 *
 * A checksum failure (`storage_integrity_error`) is a third, separate state, and a
 * dependency outage a fourth. None of them is a spinner, and none is a success. They are
 * rendered by `UploadOutcome`, which the next-version form shares (`W59-VERSION-UPLOAD-01`).
 */

import { useRef, useState } from 'react';

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { useIntentKey } from '@/shared/lib';
import type { UploadFailure, UploadPrecheckProblem } from '@/entities/document-version';
import {
  PC01_UPLOAD_ENVELOPE,
  classifyUploadFailure,
  formatBytes,
  precheckUploadFile,
} from '@/entities/document-version';

import { showChosen } from '../model/drop-files';
import { useUploadDocument } from '../model/use-upload-document';
import { DropZone } from './drop-zone';
import { UploadOutcome } from './upload-outcome';

export interface UploadDocumentFormProps {
  readonly projectUid: ProjectUid;
  /** Called with the published version, so the screen can offer to start a run. */
  readonly onUploaded?: ((version: DocumentVersion) => void) | undefined;
  /**
   * Called with the files of a drop on the field when there is more than one (`UIP-S22-03`): they go to «Несколько файлов»,
   * which the caller opens. Without it the field takes one archive and says so when several are dropped.
   */
  readonly onDropMany?: ((files: readonly File[]) => void) | undefined;
}

export function UploadDocumentForm({ projectUid, onUploaded, onDropMany }: UploadDocumentFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);
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

  /** A drop on the field: one file is chosen as the picker would choose it, several go where the caller put them. */
  const dropped = (files: readonly File[]) => {
    const [only] = files;
    if (only === undefined) return;
    if (files.length > 1) {
      onDropMany?.(files);
      return;
    }
    choose(only);
    showChosen(fileInput.current, only);
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
      <div className="am-form">
        <DropZone onFiles={dropped} several={onDropMany !== undefined}>
          <label htmlFor="upload-file">
            <strong>Комплект портала (ZIP)</strong>
          </label>
          <input
            id="upload-file"
            name="file"
            type="file"
            ref={fileInput}
            accept={PC01_UPLOAD_ENVELOPE.accept}
            onChange={(event) => choose(event.target.files?.[0] ?? null)}
          />
          <p className="am-form__hint">
            {onDropMany === undefined
              ? 'Архив можно перетащить сюда.'
              : 'Архив можно перетащить сюда; несколько архивов откроют «Несколько файлов».'}
          </p>
        </DropZone>

        <label htmlFor="upload-title">
          Отображаемое название{' '}
          <em className="am-form__hint">(необязательно; не идентификатор)</em>
        </label>
        <input
          id="upload-title"
          name="display_title"
          type="text"
          value={displayTitle}
          onChange={(event) => setDisplayTitle(event.target.value)}
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
            Загрузить
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
