'use client';

/**
 * «Исполнение» of an accepted finding (`R-151g`): what the designer did with it, as the original's SU-10 badge says,
 * chosen by the expert. Shown only for an accepted finding; the choice is sent at once, and «—» clears it.
 */

import type { FindingExecutionStatus, FindingUid, RunId } from '@/shared/api';
import { failureMessage } from '@/shared/api';
import { EXECUTION_STATUS_LABELS, EXECUTION_STATUS_ORDER } from '@/entities/finding';

import { useSetExecutionStatus } from '../model/use-set-execution-status';
import styles from './execution-status-control.module.css';

export interface ExecutionStatusControlViewProps {
  readonly status: FindingExecutionStatus | null;
  readonly busy: boolean;
  readonly error: string | null;
  readonly onChange: (status: FindingExecutionStatus | null) => void;
}

export function ExecutionStatusControlView({ status, busy, error, onChange }: ExecutionStatusControlViewProps) {
  return (
    <div className={styles.control} data-execution-status={status ?? 'none'}>
      <label className={styles.field}>
        <span>Исполнение проектировщиком</span>
        <select
          value={status ?? ''}
          disabled={busy}
          onChange={(event) => onChange(event.target.value === '' ? null : event.target.value as FindingExecutionStatus)}
        >
          <option value="">—</option>
          {EXECUTION_STATUS_ORDER.map((value) => (
            <option key={value} value={value}>{EXECUTION_STATUS_LABELS[value]}</option>
          ))}
        </select>
      </label>
      {error === null ? null : <p className={styles.error} role="alert">{error}</p>}
    </div>
  );
}

export interface ExecutionStatusControlProps {
  readonly findingUid: FindingUid;
  readonly runId: RunId;
  readonly status: FindingExecutionStatus | null;
}

export function ExecutionStatusControl({ findingUid, runId, status }: ExecutionStatusControlProps) {
  const save = useSetExecutionStatus({ findingUid, runId });
  const shown = save.isSuccess ? (save.data.status ?? null) : status;
  return (
    <ExecutionStatusControlView
      status={shown}
      busy={save.isPending}
      error={save.isError ? failureMessage(save.error).detail : null}
      onChange={(next) => save.mutate({ status: next })}
    />
  );
}
