/**
 * The links «Обзор» of «Исполнители» makes into «Очередь» that carry a filter (second UX pass; the original's counters open its task list
 * narrowed to the state they count).
 *
 * Only the states that are ONE state of the queue: «Ошибка» is `failed` and «Остановлена после повторов» is `dead_letter`, so the list a
 * link opens holds exactly what its words say. The tiles' «Выполняется» (`leased` and `running`) and «В очереди» (`queued` and
 * `retry_wait`) are two states each and the queue's filter takes one, so they stay links to the whole queue rather than to a list
 * that would disagree with the figure beside it.
 *
 * The parameter is `state` (`_pages/queue/model/address.ts` reads it; `tests/unit/workers/overview-queue-links.test.ts` holds that the
 * two agree, because a widget cannot import a page).
 */

import type { ExecutionQueueState } from '@/entities/execution';
import { routes } from '@/shared/lib';

export type FilteredQueueState = Extract<ExecutionQueueState, 'failed' | 'dead_letter'>;

export function queueStateHref(state: FilteredQueueState): string {
  return `${routes.queue()}?state=${state}`;
}
