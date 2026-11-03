/**
 * What a row of the execution queue says about waiting for an executor (`EXEC2-WEB-GROUPS-01`, over
 * `ExecutionQueueItem.binding_state` and `wait_reason`, ADR-0026 decisions 12 and 15).
 *
 * The queue row carries two members for a job whose Run was admitted by a rule or a group, and nothing
 * more: not the plan, not the connection. So the row says what it can say and no more. A `pending` job
 * has no connection yet — the group chooses one when the work is sent — and, when the reading says
 * why, it waits for a free unit, for a runner that is online, or for a new cost consent. A `bound`
 * job has been given its connection and model at dispatch; the row sends the reader to the run for
 * which ones, because the queue does not carry them and a row that guessed would name a connection
 * that was never read.
 *
 * Every other job — `frozen_at_start`, or a reading without the member: each job that existed before
 * groups — gets no sentence, and the queue draws exactly what it drew.
 */

import type { ExecutionQueueItem, RunQueueReason } from '@/shared/api';

import { QUEUE_REASON_LABELS, knownQueueReason } from './run-queue-reason';

export interface QueueItemWaitingReading {
  readonly binding: 'pending' | 'bound';
  /** Why a pending job waits, when the reading says and this screen knows the word. */
  readonly reason: RunQueueReason | null;
  readonly sentence: string;
}

const PENDING_TAIL = 'Подключение ещё не выбрано: его выберут при отправке в работу.';
const BOUND_SENTENCE =
  'Подключение и модель выбраны при отправке в работу. Какие именно, показано на странице прогона.';

export function queueItemWaiting(
  item: Pick<ExecutionQueueItem, 'state' | 'binding_state' | 'wait_reason'>,
): QueueItemWaitingReading | null {
  if (item.binding_state === 'bound') {
    return { binding: 'bound', reason: null, sentence: BOUND_SENTENCE };
  }
  if (item.binding_state !== 'pending' || item.state !== 'queued') return null;
  const reason = knownQueueReason(item.wait_reason);
  return {
    binding: 'pending',
    reason,
    sentence: reason === null
      ? `Ждёт отправки в работу. ${PENDING_TAIL}`
      : `${QUEUE_REASON_LABELS[reason]}. ${PENDING_TAIL}`,
  };
}
