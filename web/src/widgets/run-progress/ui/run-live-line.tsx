'use client';

/** @jsxRuntime automatic */

/**
 * `UI-A-65`: the original's live banner, reduced to what the reading can state — which stage the run has not
 * reached yet, and how long the run has been going. Shown only while the run is open; a terminal reading has
 * its own duration among the figures. The clock is the browser's, read after mount so a server render and the
 * first client render say the same thing, and again with each poll; against a skewed clock the elapsed time reads «—» rather than a
 * negative span (`elapsedMs`).
 */

import { useEffect, useState } from 'react';

import type { RunStatus } from '@/shared/api';
import { runStageLabel } from '@/shared/ui';
import { elapsedMs, formatElapsed } from '@/entities/audit-run';
import type { StageRow } from '@/entities/audit-run';

import styles from './run-progress.module.css';

/** The first scheduled stage the run has not reported: the one it is on, or about to start. */
export function liveStageOf(rows: readonly StageRow[]): StageRow | null {
  return rows.find((row) => row.expected && row.status === null) ?? null;
}

export interface RunLiveLineViewProps {
  readonly stage: StageRow | null;
  /** The time since the run was created, already formatted; «—» before the clock is read. */
  readonly elapsed: string;
}

export function RunLiveLineView({ stage, elapsed }: RunLiveLineViewProps) {
  return (
    <p className={styles.live} role="status" data-run-live={stage === null ? 'between' : stage.stageId}>
      <span className={styles.pulse} aria-hidden="true" />
      <span>
        {stage === null ? 'Все этапы начаты' : <>Сейчас: <strong>{runStageLabel(stage.stageId)}</strong></>}
      </span>
      <span className={styles.liveElapsed}>идёт {elapsed}</span>
    </p>
  );
}

/**
 * The elapsed time is stamped with the browser's clock each time the poll brings a new reading (`status` is a new
 * object then), not on a timer of its own: this slice schedules no interval (`tests/unit/run/polling.test.ts`), the
 * reading is only as fresh as the last poll, and the line says «идёт» for the time up to that reading.
 */
export function RunLiveLine({ status, rows }: { readonly status: Pick<RunStatus, 'created_at'>; readonly rows: readonly StageRow[] }) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
  }, [status]);
  const elapsed = now === null ? '—' : formatElapsed(elapsedMs(status.created_at, new Date(now).toISOString()));
  return <RunLiveLineView stage={liveStageOf(rows)} elapsed={elapsed} />;
}
