'use client';

/**
 * «Несколько файлов» (`R-151b`): choose several portal bundles; for each, say where it goes; upload them one by one.
 *
 * Every file starts at «Новый документ». The other choices are the project's documents, each receiving the file as
 * its next version; nothing is chosen from the file's name. A file the browser can already see is wrong (not a ZIP,
 * empty, too large) is listed with that reason and not sent. After «Загрузить» each file shows its own outcome: the
 * published version, or the server's reason.
 *
 * {@link UploadManyView} is pure markup; {@link UploadManyForm} holds the choice and sends.
 */

import { useState } from 'react';
import Link from 'next/link';

import type { DocumentUid, ProjectUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import { PC01_UPLOAD_ENVELOPE, formatBytes, precheckProblemMessage, precheckUploadFile } from '@/entities/document-version';

import type { ManyFile, ManyOutcome, UploadTarget } from '../model/upload-many';
import { NEW_DOCUMENT, sendable, targetOf, targetValue } from '../model/upload-many';
import { useUploadMany } from '../model/use-upload-many';

export interface UploadTargetOption {
  readonly documentUid: DocumentUid;
  readonly title: string;
}

export interface UploadManyViewProps {
  readonly projectUid: string;
  readonly files: readonly ManyFile[];
  readonly outcomes: ReadonlyMap<string, ManyOutcome>;
  /** The project's documents a file may become the next version of. */
  readonly documents: readonly UploadTargetOption[];
  /** The documents above are the first page of the project's; more exist. */
  readonly documentsPartial: boolean;
  readonly sending: boolean;
  readonly onChoose: (files: readonly File[]) => void;
  readonly onTarget: (id: string, target: UploadTarget) => void;
  readonly onSend: () => void;
}

function OutcomeLine({ projectUid, outcome }: { readonly projectUid: string; readonly outcome: ManyOutcome | undefined }) {
  if (outcome === undefined) return null;
  if (outcome.kind === 'sending') return <span className="am-form__hint"> · загружается…</span>;
  if (outcome.kind === 'published') {
    return (
      <span>
        {' · '}
        <Link href={routes.version(projectUid, outcome.version.version_uid)}>опубликована версия {outcome.version.version_ordinal}</Link>
      </span>
    );
  }
  return <span role="alert"> · не загружен: {outcome.failure.title}. {outcome.failure.detail}</span>;
}

export function UploadManyView({
  projectUid, files, outcomes, documents, documentsPartial, sending, onChoose, onTarget, onSend,
}: UploadManyViewProps) {
  const ready = sendable(files, outcomes).length;
  return (
    <div className="am-form" data-upload-many={files.length}>
      <label htmlFor="upload-many-files">
        <strong>Несколько комплектов портала (ZIP)</strong>
      </label>
      <input
        id="upload-many-files"
        name="files"
        type="file"
        multiple
        accept={PC01_UPLOAD_ENVELOPE.accept}
        disabled={sending}
        onChange={(event) => onChoose(Array.from(event.target.files ?? []))}
      />
      {files.length === 0 ? null : (
        <ol data-upload-many-list="">
          {files.map((item) => {
            const outcome = outcomes.get(item.id);
            const locked = sending || outcome?.kind === 'published';
            return (
              <li key={item.id} data-upload-many-file={item.id}>
                <span>{item.file.name} · {formatBytes(item.file.size)}</span>
                {item.precheck === null ? (
                  <label>
                    {' '}Куда:{' '}
                    <select
                      value={targetValue(item.target)}
                      disabled={locked}
                      onChange={(event) => onTarget(item.id, targetOf(event.target.value))}
                    >
                      <option value="">Новый документ</option>
                      {documents.map((document) => (
                        <option key={document.documentUid} value={document.documentUid}>
                          Новая версия: {document.title}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : (
                  <span role="alert"> · не будет загружен: {precheckProblemMessage(item.precheck)}</span>
                )}
                <OutcomeLine projectUid={projectUid} outcome={outcome} />
              </li>
            );
          })}
        </ol>
      )}
      {documentsPartial ? (
        <p className="am-form__hint">В списке «Куда» — первые документы проекта; новую версию другого документа загрузите на его странице.</p>
      ) : null}
      <div>
        <button type="button" className="am-button" disabled={ready === 0 || sending} onClick={onSend}>
          {sending ? 'Загружается…' : `Загрузить ${ready}`}
        </button>
      </div>
    </div>
  );
}

export interface UploadManyFormProps {
  readonly projectUid: ProjectUid;
  readonly documents: readonly UploadTargetOption[];
  readonly documentsPartial: boolean;
}

export function UploadManyForm({ projectUid, documents, documentsPartial }: UploadManyFormProps) {
  const [files, setFiles] = useState<readonly ManyFile[]>([]);
  const upload = useUploadMany(projectUid);
  return (
    <UploadManyView
      projectUid={projectUid}
      files={files}
      outcomes={upload.outcomes}
      documents={documents}
      documentsPartial={documentsPartial}
      sending={upload.sending}
      onChoose={(chosen) => {
        upload.reset();
        setFiles(chosen.map((file, index) => ({ id: String(index), file, precheck: precheckUploadFile(file), target: NEW_DOCUMENT })));
      }}
      onTarget={(id, target) => setFiles((list) => list.map((item) => item.id === id ? { ...item, target } : item))}
      onSend={() => { void upload.send(files); }}
    />
  );
}
