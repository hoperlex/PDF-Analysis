/**
 * The waiting line of one execution-queue row (`EXEC2-WEB-GROUPS-01`): why a job admitted by a rule or a
 * group is not running, or that it has been given its connection. Draws nothing for any other job, so a
 * queue of jobs that existed before groups is drawn as it always was. The words are
 * `queueItemWaiting`'s; the machine values are in `data-queue-binding` and `data-queue-wait-reason`.
 */

import type { ExecutionQueueItem } from '@/shared/api';

import { queueItemWaiting } from '../model/queue-item-waiting';

export interface QueueItemWaitingProps {
  readonly item: Pick<ExecutionQueueItem, 'state' | 'binding_state' | 'wait_reason'>;
}

export function QueueItemWaiting({ item }: QueueItemWaitingProps) {
  const waiting = queueItemWaiting(item);
  if (waiting === null) return null;
  return (
    <p role="status" data-queue-binding={waiting.binding} data-queue-wait-reason={waiting.reason ?? undefined}>
      {waiting.sentence}
    </p>
  );
}
