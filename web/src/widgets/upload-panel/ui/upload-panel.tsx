'use client';

/**
 * Upload one portal bundle (a ZIP archive holding an AR PDF with its block list and
 * recognised text) into a project.
 *
 * The accepted envelope is on screen **before** the file picker, not only in the
 * rejection that follows a bad choice. Every line of it names a refusal the server can
 * return, so a later `validation_failed` reads as the rule that was already stated rather
 * than as an arbitrary "no".
 *
 * **What this widget no longer does, and why.** It used to hold the published version in
 * React state, render it, and offer the Start-run control beside it — so a project opened
 * in a fresh tab said *"No version published in this session"* over a project full of
 * published work, and the run control existed only for a user who had just uploaded.
 * `W15-RUN` measured that sentence in a real browser and `D-16` is the row it opened. The
 * version now has an address of its own: this widget reports the upload and the screen
 * navigates there, where the version is read back from the server and the runs are listed.
 *
 * A session that keeps the only copy of what it just created is the defect, not the
 * feature.
 */

import type { ReactNode } from 'react';

import type { DocumentUid, DocumentVersion, ProjectUid } from '@/shared/api';
import { PC01_UPLOAD_ENVELOPE, UPLOAD_ENVELOPE_RULES } from '@/entities/document-version';
import { UploadDocumentForm, UploadDocumentVersionForm } from '@/features/upload-document';

export interface UploadPanelProps {
  readonly projectUid: ProjectUid;
  /** Called with the published version. The screen decides where that leads. */
  readonly onUploaded?: ((version: DocumentVersion) => void) | undefined;
}

export function UploadPanel({ projectUid, onUploaded }: UploadPanelProps) {
  return (
    <section className="am-section">
      <h2>Загрузка</h2>

      <EnvelopeNote>
        <p>
          Опубликованная версия неизменяема: здесь ничто её не редактирует и не заменяет.
          Повторная загрузка публикует второй документ, и оба остаются адресуемыми.
        </p>
      </EnvelopeNote>

      <UploadDocumentForm
        projectUid={projectUid}
        {...(onUploaded === undefined ? {} : { onUploaded })}
      />
    </section>
  );
}

export interface UploadVersionPanelProps {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  /** Called with the new version. The screen decides where that leads. */
  readonly onUploaded?: ((version: DocumentVersion) => void) | undefined;
}

/**
 * Upload the next version of one document (`W59-VERSION-UPLOAD-01`): the same envelope,
 * stated before the picker in the same words, and what a further version does and does not
 * carry over.
 */
export function UploadVersionPanel({ projectUid, documentUid, onUploaded }: UploadVersionPanelProps) {
  return (
    <section className="am-section">
      <h2>Новая версия</h2>

      <EnvelopeNote>
        <p>
          Новая версия получает следующий номер и становится текущей версией документа.
          Прежние версии, их стадия и раздел, прогоны, замечания и решения не меняются.
          Новая версия ничего не наследует: название остаётся названием документа, а стадию и
          раздел новой версии подтверждает эксперт.
        </p>
      </EnvelopeNote>

      <UploadDocumentVersionForm
        projectUid={projectUid}
        documentUid={documentUid}
        {...(onUploaded === undefined ? {} : { onUploaded })}
      />
    </section>
  );
}

/** The accepted envelope, before the picker; `children` closes it with what the upload does. */
function EnvelopeNote({ children }: { readonly children: ReactNode }) {
  return (
    <div className="am-state" role="note">
      <p className="am-state__title">Что принимается</p>
      <div className="am-state__detail">
        <ul>
          {UPLOAD_ENVELOPE_RULES.map((rule) => (
            <li key={rule}>{rule}</li>
          ))}
        </ul>
        <p>
          Комплект получают из портала распознавания: он выгружает PDF вместе с файлами
          блоков и распознанного текста одним ZIP-архивом. Файл за пределами этих
          ограничений отклоняется с указанием причины на экране. Текст не
          восстанавливается оптическим распознаванием, а частично читаемый документ
          никогда не принимается молча. Ограничения: {PC01_UPLOAD_ENVELOPE.maxBytesLabel}{' '}
          и {PC01_UPLOAD_ENVELOPE.maxPages} страниц.
        </p>
        {children}
      </div>
    </div>
  );
}
