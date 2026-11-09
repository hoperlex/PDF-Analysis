/**
 * What «Очередь» keeps in its address: the state the list is narrowed to and the period (`?state=failed&period=week`).
 *
 * The original's counters and tiles open its task list already narrowed (`distributed-feature.js`), and a link has to be able to do the
 * same here: «Исполнители» sends «задачи с ошибкой» to `?state=failed`, a reload keeps the filter, and a pasted link opens the same
 * list. The route reads the address on the server (`app/queue/page.tsx`), so the first read of the queue is already the filtered one
 * and no unfiltered request precedes it.
 *
 * **A group** (`D-370`, contract 1.43.0): `?group=errors` lists every job of one of the original's three groups
 * («Активные», «Завершённые», «Ошибки») — the server lists a set of states at once (`state_group`). A state and a group are two ways
 * to say one filter, and the server refuses both, so an address holds one: a link naming both reads as the state, and writing one
 * drops the other.
 *
 * Pure: a query string in, a query string out. A value outside the closed set (a state the contract does not have, a period this
 * screen does not offer) is dropped and never echoed, as the other screens' addresses are; «Все состояния» and «За всё время» are the
 * absent parameter, so an address that narrows nothing is the plain `/queue`.
 */

import { QUEUE_STATE_GROUPS, QUEUE_STATE_OPTIONS } from '@/entities/execution';
import type { ExecutionQueueState, ExecutionQueueStateGroup } from '@/entities/execution';

import { isQueuePeriod } from './period';
import type { QueuePeriod } from './period';

export const QUEUE_STATE_PARAM = 'state';
export const QUEUE_GROUP_PARAM = 'group';
export const QUEUE_PERIOD_PARAM = 'period';

export interface QueueAddress {
  /** The state the list is narrowed to; `''` is every state. */
  readonly state: ExecutionQueueState | '';
  /** `D-370`: the group of states the list is narrowed to; absent for none. Never together with a state. */
  readonly group?: ExecutionQueueStateGroup | undefined;
  readonly period: QueuePeriod;
}

export const EMPTY_QUEUE_ADDRESS: QueueAddress = { state: '', period: 'all' };

type Params = Pick<URLSearchParams, 'get' | 'toString'>;

export function isQueueState(value: unknown): value is ExecutionQueueState {
  return typeof value === 'string' && QUEUE_STATE_OPTIONS.some((option) => option.value === value);
}

export function isQueueGroup(value: unknown): value is ExecutionQueueStateGroup {
  return typeof value === 'string' && QUEUE_STATE_GROUPS.some((group) => group.key === value);
}

export function readQueueAddress(params: Params): QueueAddress {
  const state = params.get(QUEUE_STATE_PARAM);
  const group = params.get(QUEUE_GROUP_PARAM);
  const period = params.get(QUEUE_PERIOD_PARAM);
  const read: QueueAddress = {
    state: isQueueState(state) ? state : '',
    period: period !== null && isQueuePeriod(period) ? period : 'all',
  };
  // A state wins over a group: the two together are the one thing the server refuses.
  return read.state === '' && isQueueGroup(group) ? { ...read, group } : read;
}

/** The query after the reader narrows the list. A parameter that is not this screen's is carried through. */
export function writeQueueAddress(params: Params, next: QueueAddress): URLSearchParams {
  const written = new URLSearchParams(params.toString());
  if (next.state === '') written.delete(QUEUE_STATE_PARAM);
  else written.set(QUEUE_STATE_PARAM, next.state);
  if (next.group === undefined || next.state !== '') written.delete(QUEUE_GROUP_PARAM);
  else written.set(QUEUE_GROUP_PARAM, next.group);
  if (next.period === 'all') written.delete(QUEUE_PERIOD_PARAM);
  else written.set(QUEUE_PERIOD_PARAM, next.period);
  return written;
}
