'use client';

/**
 * What is actually wrong when work admitted on a group waits for a runner, and that the wait ends (`EXEC2-FOLLOWUP-01`, `R-149`).
 *
 * Drawn under the sentence a Run or a comparison job already has for «раннер не в сети». It reads the group's capacity through
 * `useGroupWaitDetail` (the component holds no fetch of its own) and draws nothing unless the work waits for a runner on a
 * group; then it says why no connection can take it — «агент офлайн», «проверка связи не пройдена», «ревизия подключения
 * изменилась — группу нужно пересобрать», … — and when the wait ends if nothing changes. When the capacity cannot be read it
 * says only that the reason could not be specified, and still says that the wait ends: that is true whatever the cause.
 */

import type { ExecutorGroupId, RunQueueReason } from '@/shared/api';

import { offlineWaitEndSentence } from '../model/wait-detail';
import { useGroupWaitDetail } from '../api/use-group-wait-detail';

export const WAIT_DETAIL_UNAVAILABLE = 'Причину не удалось уточнить: состояние группы не прочиталось.';

export interface GroupWaitDetailProps {
  readonly groupId: ExecutorGroupId | undefined;
  readonly waitReason: RunQueueReason | null;
  /** When the work began waiting for this reason, if the reading says. */
  readonly waitingSince?: string | undefined;
}

export function GroupWaitDetail({ groupId, waitReason, waitingSince }: GroupWaitDetailProps) {
  const reading = useGroupWaitDetail({ groupId, waitReason });
  if (reading.kind === 'none') return null;
  const ends = offlineWaitEndSentence(waitingSince);
  if (reading.kind === 'unavailable') {
    return (
      <p role="status" data-wait-detail="unavailable">
        {WAIT_DETAIL_UNAVAILABLE} {ends}
      </p>
    );
  }
  return (
    <p role="status" data-wait-detail="causes" data-wait-causes={reading.detail.causes.map((cause) => cause.issue).join(' ')}>
      {reading.detail.sentence} {ends}
    </p>
  );
}
