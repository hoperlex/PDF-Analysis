'use client';

/**
 * «Обновлено ЧЧ:ММ:СС» for the queue and the journal, and the honest version of it.
 *
 * The time is the last SUCCESSFUL read (`dataUpdatedAt`), never the time of the last attempt,
 * so a screen whose reads keep failing cannot look fresh. When the last success is older than
 * the stale threshold of `OPERATIONAL_LIST_POLLING`, or the latest read failed, the line says
 * the data may be out of date and still names when it was last current.
 */

import { useEffect, useState } from 'react';

import { OPERATIONAL_LIST_STALE_MS, isOperationalListStale } from '@/shared/config';

import styles from './update-time.module.css';

export interface UpdateTimeProps {
  /** Epoch milliseconds of the last successful read, as React Query reports it; `0` for none. */
  readonly dataUpdatedAt: number;
  /** Whether the latest read failed. */
  readonly failed: boolean;
  /** The current time. Absent in the application, where it is read at render; tests fix it. */
  readonly now?: number | undefined;
}

function two(value: number): string {
  return String(value).padStart(2, '0');
}

/**
 * `ЧЧ:ММ:СС` in the viewer's local time. The line renders only once a read has succeeded, which
 * happens in the browser after hydration, so the local clock cannot mismatch a server render.
 */
export function updateTimeLabel(epochMs: number): string {
  const moment = new Date(epochMs);
  return `${two(moment.getHours())}:${two(moment.getMinutes())}:${two(moment.getSeconds())}`;
}

export function UpdateTime({ dataUpdatedAt, failed, now }: UpdateTimeProps) {
  const [, setTick] = useState(0);
  const clock = now ?? Date.now();
  const stale = isOperationalListStale({ dataUpdatedAt, failed, now: clock });

  // One shot, not a loop: re-render once when a fresh reading crosses the stale threshold,
  // so a screen that stops receiving reads (hidden tab, dead network) does not stay "fresh"
  // because nothing happened to redraw it. A new reading re-arms it through `dataUpdatedAt`.
  useEffect(() => {
    if (now !== undefined || dataUpdatedAt <= 0 || failed) return undefined;
    const wait = dataUpdatedAt + OPERATIONAL_LIST_STALE_MS - Date.now();
    if (wait < 0) return undefined;
    const timer = window.setTimeout(() => setTick((tick) => tick + 1), wait + 50);
    return () => window.clearTimeout(timer);
  }, [dataUpdatedAt, failed, now]);

  if (dataUpdatedAt <= 0) return null;
  const at = (
    <time dateTime={new Date(dataUpdatedAt).toISOString()}>{updateTimeLabel(dataUpdatedAt)}</time>
  );
  return stale ? (
    <p role="status" className={`am-note ${styles.stale}`} data-update-state="stale">
      <strong>Данные могли устареть:</strong> последнее обновление {at}
    </p>
  ) : (
    <p className={styles.fresh} data-update-state="fresh">Обновлено {at}</p>
  );
}
