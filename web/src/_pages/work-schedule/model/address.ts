/**
 * What the address of «График работ» carries (`UI-PARITY-P0P`): the tab (`?tab=reserve`, «Выполнено» without it), the
 * month of «Выполнено» (`?month=YYYY-MM`), the first day of «Календарь запаса» (`?start=YYYY-MM-DD`) and the engineer
 * the rows are narrowed to (`?engineer=<user_uid>`, `D-319`; everyone without it). A reload or a pasted link opens the
 * same view.
 */

import { monthOf, parseDay, parseEngineer, parseMonth, todayIso, weekStart } from '@/entities/work-schedule';

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
  /** The engineer the month and the reserve are narrowed to; `null` shows everyone. */
  readonly engineer: string | null;
}

export function readScheduleAddress(
  query: {
    readonly tab?: string | undefined;
    readonly month?: string | undefined;
    readonly start?: string | undefined;
    readonly engineer?: string | undefined;
  },
  today: string = todayIso(),
): ScheduleAddress {
  return {
    tab: query.tab === 'reserve' ? 'reserve' : 'completed',
    month: parseMonth(query.month) ?? monthOf(today),
    start: parseDay(query.start) ?? weekStart(today),
    engineer: parseEngineer(query.engineer),
  };
}

export function scheduleSearch({ tab, month, start, engineer }: ScheduleAddress): string {
  const params = new URLSearchParams();
  if (tab === 'reserve') {
    params.set('tab', 'reserve');
    params.set('start', start);
  } else {
    params.set('month', month);
  }
  if (engineer !== null) params.set('engineer', engineer);
  return `?${params.toString()}`;
}
