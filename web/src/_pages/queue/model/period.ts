/**
 * The period the queue is narrowed to (`UI-PARITY-QUEUE-A` carries `createdFrom`; the original's task list offers
 * «Сегодня / 7 дней / 30 дней» beside its states, `distributed-feature.js` 173-182). A choice is turned into the instant
 * the period begins at the moment it is chosen and stays that instant, so the filter, its cursors and its cache key do
 * not slide under a person who is reading a page.
 */

export type QueuePeriod = 'all' | 'today' | 'week' | 'month';

export const QUEUE_PERIOD_OPTIONS: readonly { readonly value: QueuePeriod; readonly label: string }[] = [
  { value: 'all', label: 'За всё время' },
  { value: 'today', label: 'Сегодня' },
  { value: 'week', label: '7 дней' },
  { value: 'month', label: '30 дней' },
];

const DAY_MS = 24 * 60 * 60 * 1000;

export function isQueuePeriod(value: string): value is QueuePeriod {
  return QUEUE_PERIOD_OPTIONS.some((option) => option.value === value);
}

/**
 * The instant a period begins at, or `undefined` for «За всё время». «Сегодня» begins at the viewer's local midnight (the
 * day the viewer means); the other two count back whole days from `now`.
 */
export function queuePeriodStart(period: QueuePeriod, now: Date): string | undefined {
  switch (period) {
    case 'all': return undefined;
    case 'today': {
      const midnight = new Date(now.getTime());
      midnight.setHours(0, 0, 0, 0);
      return midnight.toISOString();
    }
    case 'week': return new Date(now.getTime() - 7 * DAY_MS).toISOString();
    case 'month': return new Date(now.getTime() - 30 * DAY_MS).toISOString();
  }
}
