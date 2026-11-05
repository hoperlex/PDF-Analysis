/**
 * `UI-B-50`: the queue shows a job's state as a coloured badge, as the original's row colours do, with the
 * same tones the run badge uses (`am-badge--pending|active|ok|degraded|failed|inert`). The label is the
 * queue's own word for the state; nothing is renamed.
 */

import type { ExecutionQueueItem } from '@/shared/api';

import { jobStateLabel } from '../model/presentation';

type JobState = ExecutionQueueItem['state'];

/** The tone of a job state. A state the screen does not know is the inert tone, labelled by its code. */
export function jobStateTone(state: JobState | string): string {
  switch (state) {
    case 'queued':
    case 'retry_wait':
      return 'pending';
    case 'leased':
    case 'running':
      return 'active';
    case 'succeeded':
      return 'ok';
    case 'failed':
    case 'dead_letter':
      return 'failed';
    default:
      return 'inert';
  }
}

export function JobStateBadge({ state }: { readonly state: JobState }) {
  return (
    <span className={`am-badge am-badge--${jobStateTone(state)}`} data-job-state={state}>
      <span className="am-badge__label">{jobStateLabel(state) ?? state}</span>
    </span>
  );
}
