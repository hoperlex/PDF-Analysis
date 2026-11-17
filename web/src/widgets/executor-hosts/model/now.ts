/**
 * What a card says a server is doing now (`UIP-S15-03`, `Г12-B`): the stage as a word and the time as a duration.
 *
 * The widget reads both neighbours the line needs: the layout names the stage (`rowOfStageKey`, `STAGE_ROW_LABELS` of
 * `stage-layout`), the queue's wording says how long (`queueAgeLabel` of `execution`). The `executor-host` entity reads neither, so
 * this is the place where the two meet.
 */

import { queueAgeLabel } from '@/entities/execution';
import { STAGE_ROW_LABELS, rowOfStageKey } from '@/entities/stage-layout';

/**
 * The word of a stage, or `null`. A stage the layout has no row for (the preparation, the merge, the quote check) and one the
 * server did not name get no word: the code is never put on the screen in its place.
 */
export function stageWordOf(stageKey: string | null): string | null {
  if (stageKey === null) return null;
  const row = rowOfStageKey(stageKey);
  return row === null ? null : STAGE_ROW_LABELS[row];
}

/** «21 мин» since `since` as of the last read, or `null` when there is no reading to measure against. */
export function workAgeOf(since: string, asOf: number | null): string | null {
  const label = queueAgeLabel(since, asOf);
  return label === '—' ? null : label;
}
