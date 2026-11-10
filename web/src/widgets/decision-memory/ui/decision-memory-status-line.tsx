'use client';

/**
 * The administrator's one compact line over the memory (`D-495`, `getDecisionMemoryStatus`): how many cases and decisions it
 * holds, the `data_class` a case captured now gets, whether `training_use` is on, and the counts by standing and class. The
 * settings are changed by an operator tool and not by this screen, so there is nothing to press here.
 */

import type { DecisionMemoryStatus } from '@/shared/api';
import type { ErrorStateProps } from '@/shared/ui';
import { MEMORY_DATA_CLASS_LABELS, MEMORY_STATUS_LABELS, MEMORY_TRAINING_USE_LABELS } from '@/entities/decision-memory';

import styles from './decision-memory.module.css';

export interface DecisionMemoryStatusLineProps {
  readonly status: DecisionMemoryStatus | undefined;
  readonly error: ErrorStateProps | null;
}

export function DecisionMemoryStatusLine({ status, error }: DecisionMemoryStatusLineProps) {
  if (error !== null) {
    return (
      <p className={styles.statusLine} role="status" data-memory-status-line="failed">
        <span className={styles.statusKey}>Память</span>
        <span>Сводка не получена. {error.detail}</span>
        {error.correlationId === undefined || error.correlationId === null ? null : (
          <span className={styles.muted}>Идентификатор корреляции <code>{error.correlationId}</code></span>
        )}
      </p>
    );
  }
  if (status === undefined) return null;
  return (
    <p className={styles.statusLine} data-memory-status-line="" data-memory-data-class={status.data_class} data-memory-training-use={status.training_use}>
      <span className={styles.statusKey}>Память</span>
      <span>дел: <strong>{status.cases}</strong></span>
      <span>решений: <strong>{status.decisions}</strong></span>
      <span>новые дела записываются как: <strong>{MEMORY_DATA_CLASS_LABELS[status.data_class].toLowerCase()}</strong></span>
      <span>обучение на памяти: <strong>{MEMORY_TRAINING_USE_LABELS[status.training_use]}</strong></span>
      {status.by_status_and_class.length === 0 ? null : (
        <span className={styles.muted} data-memory-counts="">
          {status.by_status_and_class
            .map((row) => `${MEMORY_STATUS_LABELS[row.status].toLowerCase()}, ${MEMORY_DATA_CLASS_LABELS[row.data_class].toLowerCase()}: ${row.cases}`)
            .join(' · ')}
        </span>
      )}
    </p>
  );
}
