'use client';

/**
 * Rename and archive on the document's own page (`R-151a`).
 *
 * {@link DocumentLifecycleView} is pure markup; {@link DocumentLifecycle} connects it. Renaming is an inline field with
 * «Сохранить»; archiving is confirmed in place («В архив?» — «Да, в архив»), never by a native `confirm`, and says what
 * it does: the document leaves the lists, nothing of it is deleted, and it can be brought back.
 */

import { useState } from 'react';

import type { DocumentUid, ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api';

import { titleProblem, useRenameDocument, useSetDocumentArchived } from '../model/use-manage-document';
import styles from './document-lifecycle.module.css';

export interface DocumentLifecycleViewProps {
  readonly title: string;
  readonly archived: boolean;
  readonly draft: string | null;
  readonly asking: boolean;
  readonly busy: boolean;
  readonly error: string | null;
  readonly onEdit: () => void;
  readonly onDraft: (value: string) => void;
  readonly onSave: () => void;
  readonly onCancelEdit: () => void;
  readonly onAsk: () => void;
  readonly onConfirm: () => void;
  readonly onCancelAsk: () => void;
}

export function DocumentLifecycleView({
  title, archived, draft, asking, busy, error,
  onEdit, onDraft, onSave, onCancelEdit, onAsk, onConfirm, onCancelAsk,
}: DocumentLifecycleViewProps) {
  const problem = draft === null ? null : titleProblem(draft);
  return (
    <div className={styles.lifecycle} data-document-lifecycle={archived ? 'archived' : 'in-use'}>
      {archived ? (
        <p className={styles.archived} role="status">
          Документ в архиве: его нет в списках проекта. Версии, прогоны и решения сохранены.
        </p>
      ) : null}
      {draft === null ? (
        <div className={styles.row}>
          <button type="button" className="am-button am-button--quiet am-button--small" disabled={busy} onClick={onEdit}>
            Переименовать
          </button>
          {asking ? (
            <span className={styles.confirm} role="group" aria-label={archived ? 'Вернуть из архива?' : 'Убрать в архив?'}>
              <span>{archived ? 'Вернуть документ в списки?' : 'Убрать документ в архив? Ничего не удаляется.'}</span>
              <button type="button" className="am-button am-button--small" disabled={busy} onClick={onConfirm}>
                {archived ? 'Да, вернуть' : 'Да, в архив'}
              </button>
              <button type="button" className="am-button am-button--quiet am-button--small" disabled={busy} onClick={onCancelAsk}>
                Отмена
              </button>
            </span>
          ) : (
            <button type="button" className="am-button am-button--quiet am-button--small" disabled={busy} onClick={onAsk}>
              {archived ? 'Вернуть из архива' : 'В архив'}
            </button>
          )}
        </div>
      ) : (
        <form
          className={styles.row}
          onSubmit={(event) => {
            event.preventDefault();
            if (problem === null) onSave();
          }}
        >
          <label className={styles.field}>
            <span>Название документа</span>
            <input type="text" value={draft} maxLength={400} disabled={busy} onChange={(event) => onDraft(event.target.value)} />
          </label>
          <button type="submit" className="am-button am-button--small" disabled={busy || problem !== null || draft.trim() === title}>
            Сохранить
          </button>
          <button type="button" className="am-button am-button--quiet am-button--small" disabled={busy} onClick={onCancelEdit}>
            Отмена
          </button>
          {problem === null ? null : <span className={styles.error}>{problem}</span>}
        </form>
      )}
      {error === null ? null : <p className={styles.error} role="alert">{error}</p>}
    </div>
  );
}

export interface DocumentLifecycleProps {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly title: string;
  readonly archived: boolean;
}

export function DocumentLifecycle({ projectUid, documentUid, title, archived }: DocumentLifecycleProps) {
  const address = { projectUid, documentUid };
  const archive = useSetDocumentArchived(address);
  const rename = useRenameDocument(address);
  const [draft, setDraft] = useState<string | null>(null);
  const [asking, setAsking] = useState(false);
  const failed = archive.error ?? rename.error;
  return (
    <DocumentLifecycleView
      title={title}
      archived={archived}
      draft={draft}
      asking={asking}
      busy={archive.isPending || rename.isPending}
      error={failed === null || failed === undefined ? null : failureMessage(failed).detail}
      onEdit={() => { rename.reset(); setDraft(title); }}
      onDraft={setDraft}
      onSave={() => {
        if (draft === null) return;
        rename.mutate({ displayTitle: draft.trim() }, { onSuccess: () => setDraft(null) });
      }}
      onCancelEdit={() => { rename.reset(); setDraft(null); }}
      onAsk={() => { archive.reset(); setAsking(true); }}
      onConfirm={() => archive.mutate({ archived: !archived }, { onSuccess: () => setAsking(false) })}
      onCancelAsk={() => setAsking(false)}
    />
  );
}
