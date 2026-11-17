'use client';

/**
 * `UIP-S13-02`: the line over the queue's list, the original's «4 / 4» with its bar and the total «✓ N ✗ M». The figures are
 * {@link queueProgress}'s, from the overview; a queue with no job, or a page with no overview, draws nothing.
 */

import type { ExecutionQueueStateCount } from '@/shared/api';

import { queueProgress } from '../model/progress';

import styles from './execution-queue.module.css';

export interface QueueProgressProps {
  readonly overview: readonly ExecutionQueueStateCount[] | undefined;
}

export function QueueProgress({ overview }: QueueProgressProps) {
  const progress = queueProgress(overview);
  if (progress === null) return null;
  return (
    <p className={styles.progress} data-queue-progress={`${progress.ended}/${progress.total}`}>
      <span className={styles.progressCount} data-queue-progress-count="">{`${progress.ended} / ${progress.total}`}</span>
      <progress className={styles.progressBar} value={progress.ended} max={progress.total} aria-label="Ход очереди" />
      <span title="Завершены без ошибок" data-queue-progress-ok={progress.succeeded}>{`✓ ${progress.succeeded}`}</span>
      <span title="Завершены с ошибкой" data-queue-progress-failed={progress.failed}>{`✗ ${progress.failed}`}</span>
    </p>
  );
}
