'use client';

/**
 * The precise reason work admitted on a group waits for a runner (`EXEC2-FOLLOWUP-01`, ruling `R-149`).
 *
 * A Run or a comparison AI job that waits with `runner_offline` carries one word for every case in which no member of its
 * group can take it. This hook reads the capacity of that group (`getExecutorGroupCapacity`, through
 * `useExecutorGroupCapacity`: the same key under the `execution` root, so a command on a group or the «Обновить» of the
 * «Исполнители» screen refreshes it) **only while the work waits for a runner**, and `groupWaitDetail` turns what each member
 * reports into a sentence. For any other reason, for work that is not waiting, and for work with no group, nothing is read:
 * the read is `enabled` only for a `runner_offline` wait on a named group.
 *
 * The capacity describes the group's **current** revision, and the work waits on the revision it froze: `revisionId` is that one
 * (`planned.executor_group_revision_id`), and `groupWaitDetail` says so when the two differ instead of describing members that will
 * not serve the work.
 *
 * It is a read, not a poll. The work's own status refreshes on the screens that show it, and the capacity is read again on
 * a return to the tab; a stale answer is at worst the sentence that was true a moment ago, and a reading that no longer
 * explains the wait (some member became eligible) explains nothing at all.
 */

import type { ExecutorGroupId, RunQueueReason } from '@/shared/api';

import { groupWaitDetail } from '../model/wait-detail';
import type { GroupWaitExplanation } from '../model/wait-detail';
import { useExecutorGroupCapacity } from './use-executor-groups';

export interface GroupWaitReadingInput {
  /** The group the work was admitted on; `undefined` for work with none. */
  readonly groupId: ExecutorGroupId | undefined;
  /** The revision of that group the work froze; `undefined` when the reading does not say. */
  readonly revisionId?: string | undefined;
  /** The stored reason the work waits, or `null` when it does not. */
  readonly waitReason: RunQueueReason | null;
}

export type GroupWaitReading =
  /** Nothing to explain: the work does not wait for a runner, or the capacity is not read yet. */
  | { readonly kind: 'none' }
  /** The capacity could not be read; the screen says so and keeps the sentence it already had. */
  | { readonly kind: 'unavailable' }
  /** The read says why no member can take the work (or that it waits on a previous revision). */
  | { readonly kind: 'detail'; readonly detail: GroupWaitExplanation };

/** The reading is wanted only for a wait for a runner on a named group. */
export function wantsGroupWaitDetail(input: Pick<GroupWaitReadingInput, 'groupId' | 'waitReason'>): boolean {
  return input.groupId !== undefined && input.waitReason === 'runner_offline';
}

export function useGroupWaitDetail(input: GroupWaitReadingInput): GroupWaitReading {
  const wanted = wantsGroupWaitDetail(input);
  // A disabled query reads nothing; the key only has to be a valid one.
  const capacity = useExecutorGroupCapacity(input.groupId ?? '', wanted);
  if (!wanted) return { kind: 'none' };
  if (capacity.isError) return { kind: 'unavailable' };
  if (capacity.data === undefined) return { kind: 'none' };
  const detail = groupWaitDetail(capacity.data, input.revisionId);
  return detail === null ? { kind: 'none' } : { kind: 'detail', detail };
}
