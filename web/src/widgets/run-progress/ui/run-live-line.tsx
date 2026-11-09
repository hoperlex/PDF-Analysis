'use client';

/** @jsxRuntime automatic */

/**
 * The open run's live line, as the original's banner states it (`UI-A-65`, `RUN-SCREEN-01a`): which stage the run is on, the window or
 * batch inside it when the extended review exposes one, the model, the server and how long it has been going —
 * «Сейчас: Анализ блоков · окно 2 из 5 · Opus 5.5 · adm1.hlab.kz · в этапе 12 m 3 s». A run that is still in the queue has no stage
 * to be on: the line says what it waits for in the words of `runWaitingSentence`, and the group's precise reason follows it
 * (`GroupWaitDetail`, drawn by the caller).
 *
 * Shown only while the run is open. The clock is the browser's, read after mount so a server render and the first client render say
 * the same thing, and again with each poll; against a skewed clock the elapsed time reads «—» rather than a negative span
 * (`elapsedMs`). The server's estimated finish is the header's (`RunHeader`), read from the same clock.
 */

import { useEffect, useState } from 'react';

import type { RunStatus } from '@/shared/api';
import { elapsedMs, formatElapsed, liveProgressText } from '@/entities/audit-run';
import type { LiveProgress, RunChip } from '@/entities/audit-run';

import styles from './run-progress.module.css';

/**
 * The browser's clock, stamped when a poll brings a new reading (`status` is a new object then), not on a timer of its own: this slice
 * schedules no interval (`tests/unit/run/polling.test.ts`), the reading is only as fresh as the last poll, and «идёт» is the time up to
 * that reading. `null` before the first stamp, so a server render shows no time at all.
 */
export function useRunClock(status: RunStatus): number | null {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
  }, [status]);
  return now;
}

export interface RunLiveLineViewProps {
  /** The chip the run is on; `null` when every chip has started and none is running. */
  readonly chip: RunChip | null;
  /** The window or batch that is running, when the extended review says one. */
  readonly progress?: LiveProgress | null | undefined;
  /** The run's model: the short name for the eye and the full pin for the tooltip. `null` for a chip that calls none, or no model. */
  readonly model?: { readonly short: string; readonly pin: string } | null | undefined;
  /** The executor's display name; `null` when the reading carries none or the reader may not see servers. */
  readonly server?: string | null | undefined;
  /** The time already formatted; «—» before the clock is read. */
  readonly elapsed: string;
  /** What the time counts: the chip's own time, or the run's when the chip has no start. */
  readonly elapsedOf?: 'chip' | 'run' | undefined;
}

export function RunLiveLineView({ chip, progress = null, model = null, server = null, elapsed, elapsedOf = 'run' }: RunLiveLineViewProps) {
  const showProgress = progress !== null && chip !== null && chip.stages.length === 0;
  return (
    <p className={styles.live} role="status" data-run-live={chip === null ? 'between' : chip.definition.id}>
      <span className={styles.pulse} aria-hidden="true" />
      <span>
        {chip === null ? 'Все этапы начаты' : <>Сейчас: <strong>{chip.definition.full}</strong></>}
        {showProgress ? <> · <span data-run-live-progress={progress.kind}>{liveProgressText(progress)}</span></> : null}
        {model === null ? null : <> · <span data-run-live-model title={model.pin}>{model.short}</span></>}
        {server === null ? null : <> · <span data-run-live-server>{server}</span></>}
      </span>
      <span className={styles.liveElapsed}>
        {elapsedOf === 'chip' ? 'в этапе' : 'прогон идёт'} {elapsed}
      </span>
    </p>
  );
}

/** The elapsed time the line prints for a chip or, without a chip start, for the run; `—` before the clock is read. */
export function liveElapsed(
  status: Pick<RunStatus, 'created_at'>,
  chip: RunChip | null,
  now: number | null,
): { readonly text: string; readonly of: 'chip' | 'run' } {
  if (now === null) return { text: '—', of: 'run' };
  const nowIso = new Date(now).toISOString();
  if (chip !== null && chip.startedAt !== null) return { text: formatElapsed(elapsedMs(chip.startedAt, nowIso)), of: 'chip' };
  return { text: formatElapsed(elapsedMs(status.created_at, nowIso)), of: 'run' };
}

export interface RunWaitLineProps {
  /** `runWaitingSentence(...)`: why the run is in the queue. */
  readonly sentence: string;
  /** The model the run waits for, short and full; `null` when the reading names none. */
  readonly model?: { readonly short: string; readonly pin: string } | null | undefined;
}

/** The queued run's live line: no stage, the reason it waits. */
export function RunWaitLine({ sentence, model = null }: RunWaitLineProps) {
  return (
    <p className={styles.live} role="status" data-run-live="waiting">
      <span className={styles.pulse} aria-hidden="true" />
      <span>
        <span data-run-executor-waiting>{sentence}</span>
        {model === null ? null : <> · <span data-run-live-model title={model.pin}>{model.short}</span></>}
      </span>
    </p>
  );
}
