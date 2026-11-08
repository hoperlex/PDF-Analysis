'use client';

import { usePathname } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import type { ReleaseList } from '@/shared/api';
import { checkWebVersion, hasErrorCode, shouldShowUpdate, VersionCheckError } from '@/shared/api';
import { getWebBuildId, MissingConfigurationError, NEXT_PARAM, safeReturnPath, SIGN_IN_SCREEN } from '@/shared/config';
import type { SessionEndReason } from '@/shared/lib';
import { SESSION_END_REASON_PARAM } from '@/shared/lib';
import { useReleases } from '@/entities/release';
import { useMarkReleaseNotesRead } from '@/features/mark-release-notes-read';

import styles from './release-notices.module.css';

const LATER_PREFIX = 'dismissed-update:';

export function MarkFaultView() {
  return <p className={`${styles.notice} ${styles.markFault}`} role="alert">Не удалось сохранить отметку о прочтении.</p>;
}

/**
 * The notices are strips in the page's own flow, above the screen they belong to, in the manner of the original's
 * `live-banner` and `queue-interrupted-banner`: one line, a coloured edge, buttons at the right. They are not floating
 * cards. The «Что нового» card used to be fixed at the lower left and covered about 450 px of a 780 px screen, so a
 * press under it landed on the card; a strip in the flow covers nothing and scrolls away with the page.
 */
export function UpdateBannerView({ onUpdate, onLater }: { readonly onUpdate: () => void; readonly onLater: () => void }) {
  return (
    <aside className={styles.notice} role="status" data-update-banner="">
      <p className={styles.text}>
        <strong>Доступна новая версия.</strong> Обновите страницу, чтобы увидеть изменения.
      </p>
      <div className={styles.actions}>
        <button type="button" className="am-button am-button--small" onClick={onUpdate}>Обновить <span aria-hidden="true">↗</span></button>
        <button type="button" className="am-button am-button--quiet am-button--small" onClick={onLater}>Позже</button>
      </div>
    </aside>
  );
}

/**
 * One line while closed: the name, the version, the first change and «Показать все». A native `<details>` opens the
 * whole list in place, so the strip needs no state of its own and the full text is in the markup either way. «Закрыть»
 * marks the notes read, as before.
 */
export function WhatsNewView({ listing, newest, onClose }: {
  readonly listing: ReleaseList;
  readonly newest: string;
  readonly onClose: () => void;
}) {
  const entries = listing.items.filter((item) => listing.whats_new.includes(item.version));
  const total = entries.reduce((sum, entry) => sum + entry.items.length, 0);
  const first = entries[0]?.items[0]?.text ?? null;
  return (
    <aside className={styles.notice} role="region" aria-label="Что нового" data-whats-new="">
      <details className={styles.details}>
        <summary className={styles.summary}>
          <strong>Что нового</strong>
          <span className={styles.version}>версия {newest}</span>
          {first === null ? null : <span className={styles.first}>{first}</span>}
          <span className={styles.toggle}>
            <span className={styles.whenClosed}>Показать все ({total})</span>
            <span className={styles.whenOpen}>Свернуть</span>
          </span>
        </summary>
        <div className={styles.body}>
          {entries.map((entry) => (
            <section key={entry.version}>
              <h3>{entry.title} · {entry.version}</h3>
              <ul>{entry.items.map((item, index) => <li key={`${entry.version}-${index}`}>{item.text}</li>)}</ul>
            </section>
          ))}
        </div>
      </details>
      <div className={styles.actions}>
        <button type="button" className="am-button am-button--small" onClick={onClose}>Закрыть</button>
      </div>
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

/**
 * Why this tier sends a browser to sign-in: the API answered an authenticated request with `401`.
 * That is the closed list's `ended` (`@/shared/lib/session-end-reason`): the register still held the credential as
 * live and the API no longer accepts it, and a `401` cannot say more. Typed against the list, so a word outside it
 * does not compile.
 */
const REFUSED_BY_API: SessionEndReason = 'ended';

/** The part of `window.location` the sign-in address is built from. */
export interface HereOnTheScreen {
  readonly pathname: string;
  readonly search: string;
}

/**
 * The address a `401` sends the browser to: `/login?next=<where it was>&reason=ended`.
 *
 * The same shape the server guard builds (`screen-lock.ts`, decision 1): `next` first, the reason after it and never
 * instead of it. `next` is the page the browser is on, with its query and without its fragment, passed through the
 * registry's one validator — a value it refuses is dropped, and the sign-in screen itself is never a `next`.
 */
export function signInAfterRefusal(here: HereOnTheScreen): string {
  const next = here.pathname === SIGN_IN_SCREEN ? null : safeReturnPath(`${here.pathname}${here.search}`);
  const query = [
    ...(next === null ? [] : [`${NEXT_PARAM}=${encodeURIComponent(next)}`]),
    `${SESSION_END_REASON_PARAM}=${REFUSED_BY_API}`,
  ].join('&');
  return `${SIGN_IN_SCREEN}?${query}`;
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
        window.location.assign(signInAfterRefusal(window.location));
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
      window.location.assign(signInAfterRefusal(window.location));
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

  const bannerShown = showBanner && available !== null;
  const whatsNewShown = showWhatsNew && newest !== null && releases.data !== undefined;
  if (!bannerShown && !whatsNewShown && !markFault) return null;
  return (
    <div className={styles.notices}>
      {bannerShown && available !== null ? (
        <UpdateBannerView
          onUpdate={() => window.location.reload()}
          onLater={() => {
            sessionStorage.setItem(`${LATER_PREFIX}${available}`, available);
            setLater(available);
          }}
        />
      ) : null}
      {whatsNewShown && newest !== null && releases.data !== undefined ? (
        <WhatsNewView listing={releases.data} newest={newest} onClose={closeWhatsNew} />
      ) : null}
      {markFault ? <MarkFaultView /> : null}
    </div>
  );
}
