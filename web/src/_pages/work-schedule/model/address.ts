/**
 * What the address of «График работ» carries (`UI-PARITY-P0P`): the tab (`?tab=reserve`, «Выполнено» without it), the
 * month of «Выполнено» (`?month=YYYY-MM`), the first day of «Календарь запаса» (`?start=YYYY-MM-DD`) and the engineer
 * the rows are narrowed to (`?engineer=<user_uid>`, `D-319`; everyone without it). A reload or a pasted link opens the
 * same view.
 *
 * `UIP-S14-04`: «Выполнено» may open in the mode of the days off and the absences, `?mode=absences` — the way «Календарь
 * запаса» sends an administrator to mark a leave. The field is optional and only that value is read; the page applies it for
 * an administrator and drops it as soon as the reader moves on to another tab, month or period.
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

/** The modes «Выполнено» can be opened in through the address; there is one, «Выходные и отсутствия». */
export const SCHEDULE_MODES = ['absences'] as const;
export type ScheduleMode = (typeof SCHEDULE_MODES)[number];

export interface ScheduleAddress {
  readonly tab: ScheduleTab;
  readonly month: string;
  readonly start: string;
  /** The engineer the month and the reserve are narrowed to; `null` shows everyone. */
  readonly engineer: string | null;
  /** `?mode=absences`: «Выполнено» opens in «Выходные и отсутствия». Absent in the common case, so a seed need not carry it. */
  readonly mode?: ScheduleMode | undefined;
}

export function readScheduleAddress(
  query: {
    readonly tab?: string | undefined;
    readonly month?: string | undefined;
    readonly start?: string | undefined;
    readonly engineer?: string | undefined;
    readonly mode?: string | undefined;
  },
  today: string = todayIso(),
): ScheduleAddress {
  const mode = SCHEDULE_MODES.find((known) => known === query.mode);
  return {
    tab: query.tab === 'reserve' ? 'reserve' : 'completed',
    month: parseMonth(query.month) ?? monthOf(today),
    start: parseDay(query.start) ?? weekStart(today),
    engineer: parseEngineer(query.engineer),
    ...(mode === undefined ? {} : { mode }),
  };
}

/** «Отпуск / отсутствие» of «Календарь запаса»: «Выполнено», in the mode of the days off and the absences. */
export function openAbsences(address: ScheduleAddress): ScheduleAddress {
  return { ...address, tab: 'completed', mode: 'absences' };
}

/** The reader moved on: the way-in mode is spent. */
export function withoutMode(address: ScheduleAddress): ScheduleAddress {
  return { ...address, mode: undefined };
}

export function scheduleSearch({ tab, month, start, engineer, mode }: ScheduleAddress): string {
  const params = new URLSearchParams();
  if (tab === 'reserve') {
    params.set('tab', 'reserve');
    params.set('start', start);
  } else {
    params.set('month', month);
    if (mode !== undefined) params.set('mode', mode);
  }
  if (engineer !== null) params.set('engineer', engineer);
  return `?${params.toString()}`;
}
