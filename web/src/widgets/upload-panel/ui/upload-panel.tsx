'use client';

/**
 * Upload one AR PDF into a project.
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

import type { DocumentVersion, ProjectUid } from '@/shared/api';
import { PC01_UPLOAD_ENVELOPE, UPLOAD_ENVELOPE_RULES } from '@/entities/document-version';
import { UploadDocumentForm } from '@/features/upload-document';

export interface UploadPanelProps {
  readonly projectUid: ProjectUid;
  /** Called with the published version. The screen decides where that leads. */
  readonly onUploaded?: ((version: DocumentVersion) => void) | undefined;
}

export function UploadPanel({ projectUid, onUploaded }: UploadPanelProps) {
  return (
    <section>
      <h2>Загрузка</h2>

      <div className="am-state" role="note">
        <p className="am-state__title">Что принимается</p>
        <div className="am-state__detail">
          <ul>
            {UPLOAD_ENVELOPE_RULES.map((rule) => (
              <li key={rule}>{rule}</li>
            ))}
          </ul>
          <p>
            Файл за пределами этих ограничений отклоняется с указанием причины на экране.
            Текст не восстанавливается оптическим распознаванием, а частично читаемый
            документ никогда не принимается молча. Ограничения:{' '}
            {PC01_UPLOAD_ENVELOPE.maxBytesLabel} и {PC01_UPLOAD_ENVELOPE.maxPages} страниц.
          </p>
          <p>
            Опубликованная версия неизменяема: здесь ничто её не редактирует и не заменяет.
            Повторная загрузка публикует второй документ, и оба остаются адресуемыми.
          </p>
        </div>
      </div>

      <UploadDocumentForm
        projectUid={projectUid}
        {...(onUploaded === undefined ? {} : { onUploaded })}
      />
    </section>
  );
}
