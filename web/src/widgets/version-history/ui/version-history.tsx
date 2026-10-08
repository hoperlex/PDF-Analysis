'use client';

import { useEffect, useRef } from 'react';

import type { ReleaseEntry, ReleaseList } from '@/shared/api';
import { UnknownReleaseKindError, releaseDate, releaseKindLabel, useProductVersion, useReleases } from '@/entities/release';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';

import styles from './version-history.module.css';

interface HistoryViewProps {
  readonly version: string | null;
  readonly listing: ReleaseList | null;
  readonly loading: boolean;
  readonly error: Error | null;
  readonly onClose: () => void;
  readonly onRetry: () => void;
}

function ReleaseCard({ entry }: { readonly entry: ReleaseEntry }) {
  return (
    <article className={styles.card} data-release-version={entry.version}>
      <h3>{entry.title}</h3>
      <p className={styles.meta}>Версия {entry.version} · {releaseDate(entry.date)}</p>
      <ul className={styles.items}>
        {entry.items.map((item, index) => (
          <li key={`${entry.version}-${index}`} className={styles.item}>
            <span className={styles[item.kind]}>{releaseKindLabel(item.kind)}</span>
            <p className={styles.where}>{item.where}</p>
            <p className={styles.text}>{item.text}</p>
          </li>
        ))}
      </ul>
    </article>
  );
}

/** Pure view for contrast and language checks; authored paths stay historical text. */
export function VersionHistoryView({ version, listing, loading, error, onClose, onRetry }: HistoryViewProps) {
  const current = listing?.items.filter((item) => !item.is_archive) ?? [];
  const archive = listing?.items.filter((item) => item.is_archive) ?? [];
  return (
    <div className={styles.overlay} data-version-history="">
      <button type="button" className={styles.backdrop} aria-label="Закрыть историю версий" onClick={onClose} />
      <aside className={styles.panel} role="dialog" aria-modal="true" aria-label="История версий">
        <div className={styles.heading}>
          <h2>История версий</h2>
          <button type="button" className="am-button" autoFocus onClick={onClose}>Закрыть</button>
        </div>
        {version !== null ? <p>Текущая версия: {version}</p> : null}
        <div className={styles.legend} aria-label="Обозначения изменений">
          <span className={styles.new}>Новое</span>
          <span className={styles.improved}>Улучшено</span>
          <span className={styles.fixed}>Исправлено</span>
        </div>
        {loading ? <LoadingState what="истории версий" /> : null}
        {error !== null ? (
          <ErrorState
            title={error instanceof UnknownReleaseKindError ? 'Неизвестная категория изменения' : 'История версий недоступна'}
            detail={error instanceof UnknownReleaseKindError ? error.message : 'Повторите запрос позже.'}
            onRetry={onRetry}
          />
        ) : null}
        {!loading && error === null && listing !== null && listing.items.length === 0 ? (
          <EmptyState title="История версий пока пуста" />
        ) : null}
        {!loading && error === null ? (
          <>
            <div className={styles.feed}>{current.map((entry) => <ReleaseCard key={entry.version} entry={entry} />)}</div>
            {archive.length > 0 ? (
              <details className={styles.archive}>
                <summary>Архив ({archive.length})</summary>
                {archive.map((entry) => <ReleaseCard key={entry.version} entry={entry} />)}
              </details>
            ) : null}
          </>
        ) : null}
      </aside>
    </div>
  );
}

export function VersionHistory({ onClose }: { readonly onClose: () => void }) {
  const closeRef = useRef(onClose);
  closeRef.current = onClose;
  const releases = useReleases(true);
  const version = useProductVersion(true);
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeRef.current();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);
  return (
    <VersionHistoryView
      version={version.data?.product_version ?? null}
      listing={releases.data ?? null}
      loading={releases.isPending || version.isPending}
      error={releases.error ?? version.error}
      onClose={onClose}
      onRetry={() => { void releases.refetch(); void version.refetch(); }}
    />
  );
}
