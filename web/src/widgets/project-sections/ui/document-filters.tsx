'use client';

/**
 * «Показать архивные» and the tag filter (`R-151a`, `R-151e`), the controls above a list of documents, shared by the
 * project page and the section page. The tags offered are the project's whole catalogue, never the tags of one page
 * of documents; the state they change lives in the screen, which keys its reads by it.
 */

import type { ProjectUid } from '@/shared/api';
import { useDocumentTags } from '@/entities/document-version';

import styles from './project-sections.module.css';

export interface ArchivedToggleProps {
  readonly checked: boolean;
  readonly onChange: (checked: boolean) => void;
}

export function ArchivedToggle({ checked, onChange }: ArchivedToggleProps) {
  return (
    <label className={styles.archivedToggle}>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />{' '}
      Показать архивные
    </label>
  );
}

export interface TagFilterProps {
  readonly projectUid: ProjectUid;
  readonly tag: string | null;
  readonly onTag: (tag: string | null) => void;
}

export function TagFilter({ projectUid, tag, onTag }: TagFilterProps) {
  const tags = useDocumentTags(projectUid);
  const items = tags.data?.items ?? [];
  if (items.length === 0) return null;
  return (
    <div className={styles.tagFilter} role="group" aria-label="Отбор по метке" data-tag-filter={tag ?? ''}>
      <span className={styles.tagFilterLabel}>Метки:</span>
      <button type="button" className="am-button am-button--quiet am-button--small" aria-pressed={tag === null} onClick={() => onTag(null)}>
        Все
      </button>
      {items.map((item) => (
        <button
          key={item.tag}
          type="button"
          className="am-button am-button--quiet am-button--small"
          aria-pressed={tag === item.tag}
          onClick={() => onTag(item.tag)}
        >
          {item.tag} <span className={styles.tagCount}>{item.document_count}</span>
        </button>
      ))}
    </div>
  );
}
