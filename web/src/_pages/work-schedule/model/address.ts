/**
 * What the address of «График работ» carries (`UI-PARITY-P0P`): the tab (`?tab=reserve`, «Выполнено» without it), the
 * month of «Выполнено» (`?month=YYYY-MM`) and the first day of «Календарь запаса» (`?start=YYYY-MM-DD`). A reload or a
 * pasted link opens the same view.
 */

import { monthOf, parseDay, parseMonth, todayIso, weekStart } from '@/entities/work-schedule';

export const SCHEDULE_TABS = ['completed', 'reserve'] as const;
export type ScheduleTab = (typeof SCHEDULE_TABS)[number];

export const SCHEDULE_TAB_LABELS: Readonly<Record<ScheduleTab, string>> = {
  completed: 'Выполнено',
  reserve: 'Календарь запаса',
};

/** The reserve's length: four weeks, as the original's default period. */
export const RESERVE_DAYS = 28;

export interface ScheduleAddress {
  readonly tab: ScheduleTab;
  readonly month: string;
  readonly start: string;
}

export function readScheduleAddress(
  query: { readonly tab?: string | undefined; readonly month?: string | undefined; readonly start?: string | undefined },
  today: string = todayIso(),
): ScheduleAddress {
  return {
    tab: query.tab === 'reserve' ? 'reserve' : 'completed',
    month: parseMonth(query.month) ?? monthOf(today),
    start: parseDay(query.start) ?? weekStart(today),
  };
}

export function scheduleSearch({ tab, month, start }: ScheduleAddress): string {
  const params = new URLSearchParams();
  if (tab === 'reserve') {
    params.set('tab', 'reserve');
    params.set('start', start);
  } else {
    params.set('month', month);
  }
  return `?${params.toString()}`;
}
