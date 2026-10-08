'use client';

import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import type { ReleaseList } from '@/shared/api';
import { checkWebVersion, hasErrorCode, shouldShowUpdate, VersionCheckError } from '@/shared/api';
import { getWebBuildId, SIGN_IN_SCREEN } from '@/shared/config';
import { useReleases } from '@/entities/release';
import { useMarkReleaseNotesRead } from '@/features/mark-release-notes-read';

import styles from './release-notices.module.css';

const LATER_PREFIX = 'dismissed-update:';

export function MarkFaultView() {
  return <p className={styles.markFault} role="alert">Не удалось сохранить отметку о прочтении.</p>;
}

export function UpdateBannerView({ onUpdate, onLater }: { readonly onUpdate: () => void; readonly onLater: () => void }) {
  return (
    <aside className={styles.banner} role="status" data-update-banner="">
      <span>Доступна новая версия</span>
      <button type="button" className="am-button" onClick={onUpdate}>Обновить</button>
      <button type="button" className="am-button" onClick={onLater}>Позже</button>
    </aside>
  );
}

export function WhatsNewView({ listing, newest, onClose }: {
  readonly listing: ReleaseList;
  readonly newest: string;
  readonly onClose: () => void;
}) {
  return (
    <aside className={styles.whatsNew} role="dialog" aria-label="Что нового" aria-modal="false" data-whats-new="">
      <h2>Что нового</h2>
      <p>Версия {newest}</p>
      {listing.items.filter((item) => listing.whats_new.includes(item.version)).map((entry) => (
        <section key={entry.version}>
          <h3>{entry.title} · {entry.version}</h3>
          <ul>{entry.items.map((item, index) => <li key={`${entry.version}-${index}`}>{item.text}</li>)}</ul>
        </section>
      ))}
      <button type="button" className="am-button" onClick={onClose}>Закрыть</button>
    </aside>
  );
}

/** Browser-only child so server-rendered frame instruments stay request-free. */
export function ReleaseNoticesGate() {
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  return mounted ? <ReleaseNotices /> : null;
}

function ReleaseNotices() {
  const buildId = getWebBuildId();
  const pathname = usePathname();
  const releases = useReleases(true);
  const mark = useMarkReleaseNotesRead();
  const [available, setAvailable] = useState<string | null>(null);
  const [closedVersion, setClosedVersion] = useState<string | null>(null);
  const [later, setLater] = useState<string | null>(null);
  const [markFault, setMarkFault] = useState(false);
  const refetch = releases.refetch;

  const check = useCallback(async () => {
    try {
      const reading = await checkWebVersion();
      setAvailable(reading.changed ? reading.available : null);
      setLater(sessionStorage.getItem(`${LATER_PREFIX}${reading.available}`));
    } catch (error) {
      setAvailable(null);
      if (error instanceof VersionCheckError && error.status === 401) {
        window.location.assign(SIGN_IN_SCREEN);
      }
    }
    const answer = await refetch();
    if (hasErrorCode(answer.error, 'authentication_required')) {
      window.location.assign(SIGN_IN_SCREEN);
    }
  }, [refetch]);

  useEffect(() => {
    void check();
    const onFocus = () => { void check(); };
    const onVisible = () => { if (document.visibilityState === 'visible') void check(); };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisible);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, [pathname, check]);

  const newest = releases.data?.whats_new[0] ?? null;
  const showWhatsNew = newest !== null && newest !== closedVersion;
  const showBanner = shouldShowUpdate(buildId, available, later);

  const closeWhatsNew = () => {
    if (newest === null) return;
    setClosedVersion(newest);
    mark.mutate(newest, { onError: () => setMarkFault(true), onSuccess: () => setMarkFault(false) });
  };

  return (
    <>
      {showBanner && available !== null ? (
        <UpdateBannerView
          onUpdate={() => window.location.reload()}
          onLater={() => {
            sessionStorage.setItem(`${LATER_PREFIX}${available}`, available);
            setLater(available);
          }}
        />
      ) : null}
      {showWhatsNew && newest !== null && releases.data !== undefined ? (
        <WhatsNewView listing={releases.data} newest={newest} onClose={closeWhatsNew} />
      ) : null}
      {markFault ? <MarkFaultView /> : null}
    </>
  );
}
