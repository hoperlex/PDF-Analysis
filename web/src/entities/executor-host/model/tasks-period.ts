/**
 * The period of the completed tasks on the tab «Задачи» of «Диспетчер» (`UIP-S15-05`, `UIP-G-13`): «Сегодня», «Неделя», «Месяц».
 *
 * The edges are the reader's local midnights (the one clock of the screens): «Сегодня» is from this midnight to the next one,
 * «Неделя» the last seven calendar days with today, «Месяц» the last thirty. The server keeps the jobs accepted in
 * `[createdFrom, createdTo)`, both as instants. The range is taken when the period is chosen and held, so the filter, its
 * cursors and its cache key do not slide under a person who is reading a page.
 */

export type TasksPeriod = 'today' | 'week' | 'month';

export const TASKS_PERIODS: readonly { readonly value: TasksPeriod; readonly label: string }[] = [
  { value: 'today', label: 'Сегодня' },
  { value: 'week', label: 'Неделя' },
  { value: 'month', label: 'Месяц' },
];

export const DEFAULT_TASKS_PERIOD: TasksPeriod = 'today';

const DAYS_BACK: Readonly<Record<TasksPeriod, number>> = { today: 0, week: 6, month: 29 };

export interface TasksPeriodRange {
  /** The local midnight the period begins at, as an instant. */
  readonly createdFrom: string;
  /** The next local midnight after today, as an instant; not part of the period. */
  readonly createdTo: string;
}

/** A local midnight `days` calendar days from `now`'s day; the calendar carries the month and the zone's own change of clocks. */
function localMidnight(now: Date, days: number): Date {
  return new Date(now.getFullYear(), now.getMonth(), now.getDate() + days, 0, 0, 0, 0);
}

export function tasksPeriodRange(period: TasksPeriod, now: Date): TasksPeriodRange {
  return {
    createdFrom: localMidnight(now, -DAYS_BACK[period]).toISOString(),
    createdTo: localMidnight(now, 1).toISOString(),
  };
}
