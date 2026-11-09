/** Words of the knowledge base's rows, shared by the events view and the table (`UI-B-34`). */

import type { DecisionEventType } from '@/shared/api';

/** Event labels, the same four `DecisionHistory` uses. */
export const EVENT_TYPE_LABELS: Readonly<Record<DecisionEventType, string>> = {
  accept: 'приём',
  reject: 'отклонение',
  comment: 'комментарий',
  revoke: 'отзыв',
};

/** The count of decisions on one finding, said in words: a lone digit beside a timestamp reads as an ordinal. */
export function decisionCountWords(count: number): string {
  return count === 1 ? 'одно решение по находке' : `решений по находке: ${count}`;
}
