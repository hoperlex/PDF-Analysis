'use client';

/**
 * One dialog for starting several documents (`R-151c`): every chosen document with its estimate, the total, one
 * agreement for the batch, then each run's own outcome.
 *
 * {@link BatchStartPanelView} is pure markup; {@link BatchStartPanel} estimates on mount and starts on the reader's
 * agreement. The agreement names the sum of the runs' ceilings, the most the batch may spend; a document whose
 * estimate failed is listed with its reason and is not started. Nothing is confirmed by a native `confirm`.
 */

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';

import type { VersionUid } from '@/shared/api';
import { routes } from '@/shared/lib';
import { microsAsUsd } from '@/shared/ui';

import type { BatchEntry, BatchEstimate, BatchOutcome } from '../model/batch-start';
import { batchConsent, batchIsFree, batchTotals } from '../model/batch-start';
import { useBatchStart } from '../model/use-batch-start';
import styles from './start-run-control.module.css';

export interface BatchStartPanelViewProps {
  readonly projectUid: string;
  readonly entries: readonly BatchEntry[];
  readonly estimates: ReadonlyMap<VersionUid, BatchEstimate>;
  readonly outcomes: ReadonlyMap<VersionUid, BatchOutcome>;
  readonly estimating: boolean;
  readonly starting: boolean;
  readonly agreed: boolean;
  readonly onAgree: (value: boolean) => void;
  readonly onStart: () => void;
  readonly onClose: () => void;
}

const usd = (micros: number): string => `$${microsAsUsd(micros)}`;

function estimateLine(item: BatchEstimate | undefined): string {
  if (item === undefined || item.kind === 'pending') return 'оценивается…';
  if (item.kind === 'failed') return `оценки нет: ${item.text}`;
  if (item.estimate.billing === 'unmetered') return `${usd(0)} · без тарификации`;
  return `≈ ${usd(item.estimate.estimated_cost_micros)}, не более ${usd(batchConsent(item.estimate).ceiling_micros)}`;
}

export function BatchStartPanelView({
  projectUid, entries, estimates, outcomes, estimating, starting, agreed, onAgree, onStart, onClose,
}: BatchStartPanelViewProps) {
  const readings = entries.map((entry): BatchEstimate => estimates.get(entry.versionUid) ?? { kind: 'pending' });
  const totals = batchTotals(readings);
  // Nothing in the batch can be charged: the button is the agreement, there is no tick-box.
  const free = batchIsFree(readings);
  const settled = !estimating && totals.pending === 0;
  const startedAll = entries.every((entry) => {
    const ready = estimates.get(entry.versionUid)?.kind === 'ready';
    return !ready || outcomes.get(entry.versionUid)?.kind === 'started';
  }) && outcomes.size > 0;
  return (
    <section className={styles.batch} aria-label="Пакетный запуск аудита" data-batch-start={entries.length}>
      <h3 className={styles.batchTitle}>Запуск аудита: документов {entries.length}</h3>
      <ol className={styles.batchList}>
        {entries.map((entry) => {
          const outcome = outcomes.get(entry.versionUid);
          return (
            <li key={entry.versionUid} data-batch-version={entry.versionUid}>
              <span className={styles.batchName}>{entry.title}</span>{' '}
              <span className={styles.batchEstimate}>{estimateLine(estimates.get(entry.versionUid))}</span>
              {outcome === undefined ? null : outcome.kind === 'sending' ? (
                <span className={styles.batchEstimate}> · запускается…</span>
              ) : outcome.kind === 'started' ? (
                <span> · <Link href={routes.run(projectUid, outcome.run.run_id)}>прогон запущен</Link></span>
              ) : (
                <span className={styles.batchRefused} role="alert"> · не запущен: {outcome.text}</span>
              )}
            </li>
          );
        })}
      </ol>
      {settled ? (
        <p className={styles.batchTotal} data-batch-total="">
          Итого по {totals.ready} из {entries.length}: {free
            ? `${usd(0)} · без тарификации`
            : `≈ ${usd(totals.costMicros)}, не более ${usd(totals.ceilingMicros)}`}.
          {totals.failed > 0 ? ` Без оценки не запускается: ${totals.failed}.` : null}
        </p>
      ) : null}
      {settled && totals.ready > 0 && !startedAll && !free ? (
        <label className={styles.batchAgree}>
          <input type="checkbox" checked={agreed} disabled={starting} onChange={(event) => onAgree(event.target.checked)} />{' '}
          Согласен на расходы не более {usd(totals.ceilingMicros)} по {totals.ready} прогонам
        </label>
      ) : null}
      <div className={styles.batchActions}>
        {settled && totals.ready > 0 && !startedAll ? (
          <button type="button" className="am-button" disabled={(!agreed && !free) || starting} onClick={onStart}>
            {starting ? 'Запускается…' : `Запустить ${totals.ready}`}
          </button>
        ) : null}
        <button type="button" className="am-button am-button--quiet" disabled={starting} onClick={onClose}>
          {startedAll ? 'Готово' : 'Отмена'}
        </button>
      </div>
    </section>
  );
}

export interface BatchStartPanelProps {
  readonly projectUid: string;
  readonly entries: readonly BatchEntry[];
  readonly onClose: () => void;
}

/** The connected panel: estimates every entry once on mount, starts on agreement. */
export function BatchStartPanel({ projectUid, entries, onClose }: BatchStartPanelProps) {
  const batch = useBatchStart(entries);
  const [agreed, setAgreed] = useState(false);
  // The entries are fixed for the panel's life (a new selection mounts a new panel), so it estimates once.
  const estimated = useRef(false);
  useEffect(() => {
    if (estimated.current) return;
    estimated.current = true;
    void batch.estimate();
  }, [batch]);
  return (
    <BatchStartPanelView
      projectUid={projectUid}
      entries={entries}
      estimates={batch.estimates}
      outcomes={batch.outcomes}
      estimating={batch.estimating}
      starting={batch.starting}
      agreed={agreed}
      onAgree={setAgreed}
      onStart={() => { void batch.start(); }}
      onClose={onClose}
    />
  );
}
