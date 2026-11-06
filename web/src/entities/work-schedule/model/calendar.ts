/**
 * The calendar arithmetic of «График работ» (`UI-PARITY-P0P`): months as `YYYY-MM`, days as ISO dates, both read as
 * calendar values and never as instants, so no time zone of the browser moves a day. The days off and the facts come
 * from the server; this only names, counts and shifts them.
 */

import type { WorkScheduleDoneDocument, WorkScheduleEngineer } from '@/shared/api';

const MONTHS = [
  'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь',
] as const;
const WEEKDAYS = ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'] as const;

const MONTH_PATTERN = /^(\d{4})-(0[1-9]|1[0-2])$/;
const DAY_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;

function pad(value: number): string {
  return String(value).padStart(2, '0');
}

function utcDate(day: string): Date {
  const match = DAY_PATTERN.exec(day);
  if (match === null) throw new Error(`Не дата: ${day}`);
  return new Date(Date.UTC(Number(match[1]), Number(match[2]) - 1, Number(match[3])));
}

function isoOf(date: Date): string {
  return `${date.getUTCFullYear()}-${pad(date.getUTCMonth() + 1)}-${pad(date.getUTCDate())}`;
}

/** Today's calendar day where the browser is, as `YYYY-MM-DD`. */
export function todayIso(now: Date = new Date()): string {
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

/** The month of a day, `YYYY-MM`. */
export function monthOf(day: string): string {
  return day.slice(0, 7);
}

/** A `?month=` value, or `null` when it is not one. */
export function parseMonth(value: string | null | undefined): string | null {
  return value !== null && value !== undefined && MONTH_PATTERN.test(value) ? value : null;
}

/** A `?start=` value, or `null` when it is not a day. */
export function parseDay(value: string | null | undefined): string | null {
  if (value === null || value === undefined || !DAY_PATTERN.test(value)) return null;
  return isoOf(utcDate(value)) === value ? value : null;
}

export function shiftMonth(month: string, by: number): string {
  const [year, number] = month.split('-').map(Number) as [number, number];
  const index = year * 12 + (number - 1) + by;
  return `${Math.floor(index / 12)}-${pad((index % 12) + 1)}`;
}

/** «Ноябрь 2026». */
export function monthLabel(month: string): string {
  const [year, number] = month.split('-').map(Number) as [number, number];
  return `${MONTHS[number - 1]} ${year}`;
}

export function addDays(day: string, by: number): string {
  const date = utcDate(day);
  date.setUTCDate(date.getUTCDate() + by);
  return isoOf(date);
}

/** The Monday on or before a day: «Календарь запаса» opens on a week's start. */
export function weekStart(day: string): string {
  const shift = (utcDate(day).getUTCDay() + 6) % 7;
  return addDays(day, -shift);
}

export function dayOfMonth(day: string): number {
  return utcDate(day).getUTCDate();
}

/** «Пн» … «Вс». */
export function weekdayLabel(day: string): string {
  return WEEKDAYS[utcDate(day).getUTCDay()] as string;
}

/** «6 нояб.». */
export function shortDayLabel(day: string): string {
  return utcDate(day).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', timeZone: 'UTC' });
}

/** The fact against the plan, a whole percent; a plan of 0 has none (`R-152a`: the plan moves only this figure). */
export function planPercent(fact: number, plan: number): number | null {
  return plan > 0 ? Math.round((fact / plan) * 100) : null;
}

/** «ok» at the plan or over it, «warn» from half of it, «low» below. */
export function percentTone(percent: number | null): 'ok' | 'warn' | 'low' | 'none' {
  if (percent === null) return 'none';
  if (percent >= 100) return 'ok';
  return percent >= 50 ? 'warn' : 'low';
}

export interface ScheduleTotals {
  readonly engineers: number;
  readonly fact: number;
  readonly plan: number;
  readonly remaining: number;
  readonly percent: number | null;
}

export function scheduleTotals(engineers: readonly WorkScheduleEngineer[]): ScheduleTotals {
  const fact = engineers.reduce((sum, engineer) => sum + engineer.fact, 0);
  const plan = engineers.reduce((sum, engineer) => sum + engineer.plan, 0);
  return {
    engineers: engineers.length,
    fact,
    plan,
    remaining: engineers.reduce((sum, engineer) => sum + Math.max(0, engineer.plan - engineer.fact), 0),
    percent: planPercent(fact, plan),
  };
}

/** An engineer's done documents by day. */
export function doneByDay(engineer: WorkScheduleEngineer): ReadonlyMap<string, readonly WorkScheduleDoneDocument[]> {
  const days = new Map<string, WorkScheduleDoneDocument[]>();
  for (const item of engineer.done) {
    const list = days.get(item.day);
    if (list === undefined) days.set(item.day, [item]);
    else list.push(item);
  }
  return days;
}

/** «ИИ» from «Иванов Иван». */
export function initialsOf(label: string): string {
  const letters = label
    .split(/\s+/)
    .filter((part) => part !== '')
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');
  return letters === '' ? '·' : letters;
}
