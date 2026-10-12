'use client';

import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { ReleaseList } from '@/shared/api';
import { checkWebVersion, hasErrorCode, shouldShowUpdate, VersionCheckError } from '@/shared/api';
import { getWebBuildId, MissingConfigurationError, SIGN_IN_SCREEN } from '@/shared/config';
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

/**
 * This build's identifier, or `null` when the bundle carries none.
 *
 * `C-29`: `getWebBuildId` throws on a missing identifier, and called during render that took
 * every page of the frame down. Here a missing identifier only disables the update banner —
 * there is nothing to compare the served build with — and the effect below says so once on
 * the console. Any other fault is still thrown.
 */
export function bundleBuildId(): string | null {
  try {
    return getWebBuildId();
  } catch (error) {
    if (error instanceof MissingConfigurationError) return null;
    throw error;
  }
}

/** The two reads a trigger may start. */
export interface NoticeReads {
  readonly version: () => void;
  readonly releases: () => void;
}

/**
 * The route trigger. `C-29`: on mount only the version is read — `useReleases` is already
 * fetching the list, and a mount-time `refetch()` was a second `listReleases` for the same
 * render. A later route change re-reads both (`W52-PLAN.md` §3.5).
 */
export function readOnRoute(previous: string | null, current: string | null, reads: NoticeReads): void {
  reads.version();
  if (previous !== current) reads.releases();
}

/** What {@link listenForTabReturn} needs of `document`. */
export interface TabDocument {
  readonly visibilityState: DocumentVisibilityState;
  addEventListener(type: 'visibilitychange', listener: () => void): void;
  removeEventListener(type: 'visibilitychange', listener: () => void): void;
}

/**
 * The tab-return trigger: ONE listener. `C-29`: `focus` and `visibilitychange` both fire on a
 * single return to the tab, and listening to both read `/bff/version` and `listReleases`
 * twice each time. `visibilitychange` to visible is the one that also covers a tab switch.
 * Returns the detach.
 */
export function listenForTabReturn(target: TabDocument, reads: NoticeReads): () => void {
  const onVisible = () => {
    if (target.visibilityState !== 'visible') return;
    reads.version();
    reads.releases();
  };
  target.addEventListener('visibilitychange', onVisible);
  return () => target.removeEventListener('visibilitychange', onVisible);
}

export function ReleaseNotices() {
  const buildId = bundleBuildId();
  const pathname = usePathname();
  const releases = useReleases(true);
  const mark = useMarkReleaseNotesRead();
  const [available, setAvailable] = useState<string | null>(null);
  const [closedVersion, setClosedVersion] = useState<string | null>(null);
  const [later, setLater] = useState<string | null>(null);
  const [markFault, setMarkFault] = useState(false);
  const refetch = releases.refetch;
  const routeSeen = useRef<string | null | undefined>(undefined);

  const checkVersion = useCallback(async () => {
    if (buildId === null) return;
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
  }, [buildId]);

  const reads = useMemo<NoticeReads>(() => ({
    version: () => { void checkVersion(); },
    releases: () => { void refetch(); },
  }), [checkVersion, refetch]);

  useEffect(() => {
    if (buildId === null) {
      console.error('NEXT_PUBLIC_WEB_BUILD_ID is missing from this build: the update banner is disabled.');
    }
  }, [buildId]);

  // The first read of the list and every re-read land here, so a lapsed session is sent to
  // sign-in whichever trigger found it.
  useEffect(() => {
    if (hasErrorCode(releases.error, 'authentication_required')) {
      window.location.assign(SIGN_IN_SCREEN);
    }
  }, [releases.error]);

  useEffect(() => {
    const previous = routeSeen.current === undefined ? pathname : routeSeen.current;
    routeSeen.current = pathname;
    readOnRoute(previous, pathname, reads);
  }, [pathname, reads]);

  useEffect(() => listenForTabReturn(document, reads), [reads]);

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
