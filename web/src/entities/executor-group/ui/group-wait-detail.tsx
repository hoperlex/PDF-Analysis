'use client';

/**
 * What is actually wrong when work admitted on a group waits for a runner, and that the wait ends (`EXEC2-FOLLOWUP-01`, `R-149`).
 *
 * Drawn under the sentence a Run or a comparison job already has for «раннер не в сети». It reads the group's capacity through
 * `useGroupWaitDetail` (the component holds no fetch of its own) and draws nothing unless the work waits for a runner on a
 * group; then it says why no connection can take it — «агент офлайн», «проверка связи не пройдена», «ревизия подключения
 * изменилась — группу нужно пересобрать», … — or that the work was accepted on a previous revision of the group, which the new one will
 * not serve; and that the wait ends after the offline limit (30 minutes unless the stand sets another). When the capacity cannot be read
 * it says only that the reason could not be specified, and still says that the wait ends: that is true whatever the cause.
 *
 * The promise that the wait ends is made only of work that is queued or running (`ends`): work that is paused is not counting down.
 */

import type { ExecutorGroupId, RunQueueReason } from '@/shared/api';

import { OFFLINE_WAIT_END_SENTENCE } from '../model/wait-detail';
import { useGroupWaitDetail } from '../api/use-group-wait-detail';

export const WAIT_DETAIL_UNAVAILABLE = 'Причину не удалось уточнить: состояние группы не прочиталось.';

export interface GroupWaitDetailProps {
  readonly groupId: ExecutorGroupId | undefined;
  /** The revision of the group the work froze (`planned.executor_group_revision_id`), if the reading says. */
  readonly revisionId?: string | undefined;
  readonly waitReason: RunQueueReason | null;
  /** Whether the wait is counting down to its end: the work is queued or running. A paused one is not. */
  readonly ends?: boolean | undefined;
}

export function GroupWaitDetail({ groupId, revisionId, waitReason, ends = true }: GroupWaitDetailProps) {
  const reading = useGroupWaitDetail({ groupId, revisionId, waitReason });
  if (reading.kind === 'none') return null;
  const end = ends ? ` ${OFFLINE_WAIT_END_SENTENCE}` : '';
  if (reading.kind === 'unavailable') {
    return (
      <p role="status" data-wait-detail="unavailable">
        {WAIT_DETAIL_UNAVAILABLE}
        {end}
      </p>
    );
  }
  return (
    <p
      role="status"
      data-wait-detail={reading.detail.revision === 'previous' ? 'previous-revision' : 'causes'}
      data-wait-causes={reading.detail.causes.map((cause) => cause.issue).join(' ')}
    >
      {reading.detail.sentence}
      {end}
    </p>
  );
}
