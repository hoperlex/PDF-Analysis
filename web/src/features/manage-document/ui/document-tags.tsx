'use client';

/**
 * A document's free tags on its page (`R-151e`): chips with «×», and a field that adds one. Each change sends the whole
 * new set (`setDocumentTags`); there is no order and no group, as the owner ruled instead of the original's folders.
 * {@link DocumentTagsView} is pure markup; {@link DocumentTags} connects it. A reader who may not act sees the chips only.
 */

import { useState } from 'react';

import type { DocumentUid, ProjectUid } from '@/shared/api';
import { failureMessage } from '@/shared/api';

import { cleanTag, tagProblem, useSetDocumentTags } from '../model/use-manage-document';
import styles from './document-lifecycle.module.css';

export interface DocumentTagsViewProps {
  readonly tags: readonly string[];
  readonly mayEdit: boolean;
  readonly draft: string;
  readonly busy: boolean;
  readonly error: string | null;
  readonly onDraft: (value: string) => void;
  readonly onAdd: () => void;
  readonly onRemove: (tag: string) => void;
}

export function DocumentTagsView({ tags, mayEdit, draft, busy, error, onDraft, onAdd, onRemove }: DocumentTagsViewProps) {
  const problem = draft.trim() === '' ? null : tagProblem(draft, tags);
  return (
    <div className={styles.row} data-document-tags={tags.length}>
      <span className={styles.label}>Метки:</span>
      {tags.length === 0 ? <span className={styles.none}>нет</span> : tags.map((tag) => (
        <span key={tag} className={styles.tag}>
          {tag}
          {mayEdit ? (
            <button type="button" className={styles.tagRemove} aria-label={`Убрать метку «${tag}»`} disabled={busy} onClick={() => onRemove(tag)}>
              ×
            </button>
          ) : null}
        </span>
      ))}
      {mayEdit ? (
        <form
          className={styles.row}
          onSubmit={(event) => {
            event.preventDefault();
            if (draft.trim() !== '' && problem === null) onAdd();
          }}
        >
          <input
            type="text"
            aria-label="Новая метка"
            placeholder="Новая метка"
            value={draft}
            maxLength={40}
            disabled={busy}
            onChange={(event) => onDraft(event.target.value)}
          />
          <button type="submit" className="am-button am-button--quiet am-button--small" disabled={busy || draft.trim() === '' || problem !== null}>
            Добавить
          </button>
          {problem === null ? null : <span className={styles.error}>{problem}</span>}
        </form>
      ) : null}
      {error === null ? null : <span className={styles.error} role="alert">{error}</span>}
    </div>
  );
}

export interface DocumentTagsProps {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly tags: readonly string[];
  readonly mayEdit: boolean;
}

export function DocumentTags({ projectUid, documentUid, tags, mayEdit }: DocumentTagsProps) {
  const save = useSetDocumentTags({ projectUid, documentUid });
  const [draft, setDraft] = useState('');
  return (
    <DocumentTagsView
      tags={tags}
      mayEdit={mayEdit}
      draft={draft}
      busy={save.isPending}
      error={save.isError ? failureMessage(save.error).detail : null}
      onDraft={(value) => { save.reset(); setDraft(value); }}
      onAdd={() => save.mutate({ tags: [...tags, cleanTag(draft)] }, { onSuccess: () => setDraft('') })}
      onRemove={(tag) => save.mutate({ tags: tags.filter((known) => known !== tag) })}
    />
  );
}
