'use client';

import { useEffect, useRef } from 'react';

import type { ReleaseEntry, ReleaseList } from '@/shared/api';
import { isKnownReleaseKind, releaseDate, releaseKindLabel, useProductVersion, useReleases } from '@/entities/release';
import { EmptyState, ErrorState, Icon, LoadingState } from '@/shared/ui';

import styles from './version-history.module.css';

interface HistoryViewProps {
  readonly version: string | null;
  readonly listing: ReleaseList | null;
  readonly loading: boolean;
  readonly error: Error | null;
  readonly onClose: () => void;
  readonly onRetry: () => void;
}

/** One release as a node on the timeline: the version and date, the title, then its items. */
function ReleaseCard({ entry }: { readonly entry: ReleaseEntry }) {
  return (
    <article className={styles.card} data-release-version={entry.version}>
      <p className={styles.meta}>
        <span className={styles.version}>{entry.version}</span>
        <span aria-hidden="true"> — </span>
        <time dateTime={entry.date}>{releaseDate(entry.date)}</time>
      </p>
      <h3 className={styles.title}>{entry.title}</h3>
      <ul className={styles.items}>
        {entry.items.map((item, index) => (
          <li key={`${entry.version}-${index}`} className={styles.item}>
            {/*
              * The kind is a coloured dot, as the legend above says; its label stays in the markup
              * for a screen reader and as the dot's tooltip. `C-29`: an unknown kind gets the
              * generic label and the neutral dot; its raw value is not echoed into the markup.
              */}
            <p className={styles.where}>
              <span
                className={isKnownReleaseKind(item.kind) ? `${styles.dot} ${styles[item.kind]}` : styles.dot}
                title={releaseKindLabel(item.kind)}
                aria-hidden="true"
              />
              <span className={styles.kindLabel}>{releaseKindLabel(item.kind)}</span>
              {item.where}
            </p>
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
        <header className={styles.heading}>
          <button type="button" className={styles.close} autoFocus onClick={onClose}>
            <Icon name="reject" size={20} label="Закрыть" />
          </button>
          <h2>История версий</h2>
        </header>
        <div className={styles.body}>
          {version !== null ? <p className={styles.current}>Текущая версия: {version}</p> : null}
          <ul className={styles.legend} aria-label="Обозначения изменений">
            <li><span className={`${styles.dot} ${styles.new}`} aria-hidden="true" />Новое</li>
            <li><span className={`${styles.dot} ${styles.improved}`} aria-hidden="true" />Улучшено</li>
            <li><span className={`${styles.dot} ${styles.fixed}`} aria-hidden="true" />Исправлено</li>
          </ul>
          {loading ? <LoadingState what="истории версий" /> : null}
          {error !== null ? (
            <ErrorState
              title="История версий недоступна"
              detail="Повторите запрос позже."
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
                  <div className={styles.feed}>{archive.map((entry) => <ReleaseCard key={entry.version} entry={entry} />)}</div>
                </details>
              ) : null}
            </>
          ) : null}
        </div>
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
