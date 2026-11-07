'use client';

/** @jsxRuntime automatic */

/**
 * `UI-A-65`: the original's live banner, reduced to what the reading can state — which stage the run has not
 * reached yet, and how long the run has been going. Shown only while the run is open; a terminal reading has
 * its own duration among the figures. The clock is the browser's, read after mount so a server render and the
 * first client render say the same thing, and again with each poll; against a skewed clock the elapsed time reads «—» rather than a
 * negative span (`elapsedMs`).
 *
 * `UI-B-45` (contract 1.40.0): the line also carries the run's estimated finish, «ожидаемое завершение ~ЧЧ:ММ», when the
 * reading has one -- the server's estimate, the same the queue shows (`RunStatus.estimated_finish_at`), never computed
 * here and absent for a run without enough similar history. It is worded with the same clock reading as the elapsed time,
 * so it appears after mount, and once the instant is behind that reading the line says «дольше обычного» rather than
 * keep promising a time that has passed.
 */

import { useEffect, useState } from 'react';

import type { RunStatus } from '@/shared/api';
import { runStageLabel } from '@/shared/ui';
import { elapsedMs, formatElapsed, runFinishEstimate } from '@/entities/audit-run';
import type { RunFinishEstimate, StageRow } from '@/entities/audit-run';
import { formatInstant } from '@/shared/lib';

import styles from './run-progress.module.css';

/** The first scheduled stage the run has not reported: the one it is on, or about to start. */
export function liveStageOf(rows: readonly StageRow[]): StageRow | null {
  return rows.find((row) => row.expected && row.status === null) ?? null;
}

export interface RunLiveLineViewProps {
  readonly stage: StageRow | null;
  /** The time since the run was created, already formatted; «—» before the clock is read. */
  readonly elapsed: string;
  /** The server's estimate, worded; `null` or absent when the run has none or the clock is not yet read. */
  readonly finish?: RunFinishEstimate | null | undefined;
}

export function RunLiveLineView({ stage, elapsed, finish = null }: RunLiveLineViewProps) {
  return (
    <p className={styles.live} role="status" data-run-live={stage === null ? 'between' : stage.stageId}>
      <span className={styles.pulse} aria-hidden="true" />
      <span>
        {stage === null ? 'Все этапы начаты' : <>Сейчас: <strong>{runStageLabel(stage.stageId)}</strong></>}
      </span>
      <span className={styles.liveElapsed}>
        {finish === null ? null : (
          <>
            <span data-run-eta={finish.iso} data-run-eta-late={finish.late ? '' : undefined}>
              ожидаемое завершение <time dateTime={finish.iso} title={formatInstant(finish.iso)}>~{finish.clock}</time>
              {finish.late ? ' · дольше обычного' : null}
            </span>
            {' · '}
          </>
        )}
        идёт {elapsed}
      </span>
    </p>
  );
}

/**
 * The elapsed time is stamped with the browser's clock each time the poll brings a new reading (`status` is a new
 * object then), not on a timer of its own: this slice schedules no interval (`tests/unit/run/polling.test.ts`), the
 * reading is only as fresh as the last poll, and the line says «идёт» for the time up to that reading.
 */
export function RunLiveLine({
  status,
  rows,
}: {
  readonly status: Pick<RunStatus, 'created_at' | 'estimated_finish_at'>;
  readonly rows: readonly StageRow[];
}) {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    setNow(Date.now());
  }, [status]);
  const elapsed = now === null ? '—' : formatElapsed(elapsedMs(status.created_at, new Date(now).toISOString()));
  return <RunLiveLineView stage={liveStageOf(rows)} elapsed={elapsed} finish={runFinishEstimate(status, now)} />;
}
