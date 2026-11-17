/**
 * The two buttons of «Календарь запаса» (`UIP-S14-04`): «Назначить работу», a link to «Назначения» with the engineer of the
 * choice «Инженер» when one is made, and «Отпуск / отсутствие», which opens «Выполнено» in the mode of the days off and the
 * absences through `?mode=absences`. An administrator sees them; an expert does not, and the mode is an administrator's.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { WorkSchedulePage, openAbsences, readScheduleAddress, scheduleSearch, withoutMode } from '@/_pages/work-schedule';
import type { ScheduleAddress } from '@/_pages/work-schedule';
import type { Role } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { NO_ENGINEER_FILTER } from '@/entities/work-schedule';
import { ReserveCalendarView } from '@/widgets/reserve-calendar';

import { newClient, renderScreen } from '../screens/harness';
import { EXPERT_A, EXPERT_B, monthFixture, reserveFixture } from './fixtures';

const TODAY = '2026-11-04';
const noop = () => undefined;

function page(roles: readonly Role[], address: Partial<ScheduleAddress>): string {
  const client = newClient();
  client.setQueryData(queryKeys.workSchedule.month('2026-11'), monthFixture());
  client.setQueryData(queryKeys.workSchedule.reserve('2026-11-02', 28), reserveFixture());
  client.setQueryData(queryKeys.workSchedule.reserve(TODAY, 1), reserveFixture());
  return renderScreen(client, createElement(WorkSchedulePage, {
    roles,
    today: TODAY,
    initial: { tab: 'reserve', month: '2026-11', start: '2026-11-02', engineer: null, ...address },
  }));
}

function reserve(admin: boolean, filter = NO_ENGINEER_FILTER, withCallback = true): string {
  return renderScreen(newClient(), createElement(ReserveCalendarView, {
    reserve: reserveFixture(), admin, onStart: noop, today: TODAY, filter, onEngineer: noop,
    ...(withCallback ? { onAbsences: noop } : {}),
  }));
}

/** The link, whatever order the framework writes its attributes in. */
const assignLink = (html: string): { href: string; text: string } | null => {
  const match = /<a ([^>]*data-reserve-assign=""[^>]*)>([\s\S]*?)<\/a>/.exec(html);
  if (match === null) return null;
  return { href: /href="([^"]*)"/.exec(match[1] ?? '')?.[1] ?? '', text: (match[2] ?? '').trim() };
};
const absencesButton = (html: string): string => /<button[^>]*data-reserve-absences=""[^>]*>[\s\S]*?<\/button>/.exec(html)?.[0] ?? '';

describe('the mode of the absences in the address', () => {
  it('is read from ?mode=absences and from nothing else', () => {
    expect(readScheduleAddress({ mode: 'absences' }, TODAY).mode).toBe('absences');
    for (const value of ['vacation', 'ABSENCES', 'plan', '', undefined]) {
      const read = readScheduleAddress({ mode: value }, TODAY);
      expect(read.mode).toBeUndefined();
      expect('mode' in read).toBe(false);
    }
  });

  it('rides next to the month on «Выполнено», and is never written for «Календарь запаса»', () => {
    const read = readScheduleAddress({ tab: 'completed', month: '2026-11', mode: 'absences', engineer: EXPERT_B }, TODAY);
    expect(scheduleSearch(read)).toBe(`?month=2026-11&mode=absences&engineer=${EXPERT_B}`);
    expect(scheduleSearch({ ...read, tab: 'reserve' })).toBe(`?tab=reserve&start=${read.start}&engineer=${EXPERT_B}`);
    expect(scheduleSearch(withoutMode(read))).toBe(`?month=2026-11&engineer=${EXPERT_B}`);
  });

  it('is opened from «Календарь запаса» on «Выполнено», keeping the engineer and the month', () => {
    const fromReserve = readScheduleAddress({ tab: 'reserve', start: '2026-11-02', month: '2026-10', engineer: EXPERT_A }, TODAY);
    const opened = openAbsences(fromReserve);
    expect(opened).toMatchObject({ tab: 'completed', mode: 'absences', engineer: EXPERT_A, month: '2026-10' });
    expect(scheduleSearch(opened)).toBe(`?month=2026-10&mode=absences&engineer=${EXPERT_A}`);
  });
});

describe('«Назначить работу» in the panel of «Календарь запаса»', () => {
  it('links «Назначения» for an administrator, with no engineer while none is chosen', () => {
    const link = assignLink(reserve(true));
    expect(link).toEqual({ href: '/dispatcher', text: 'Назначить работу' });
  });

  it('carries the engineer of the choice «Инженер» in the address', () => {
    expect(assignLink(reserve(true, { uid: EXPERT_B, unknown: false }))?.href).toBe(`/dispatcher?expert=${EXPERT_B}`);
  });

  it('carries nobody when the address named an engineer the read does not have', () => {
    expect(assignLink(reserve(true, { uid: null, unknown: true }))?.href).toBe('/dispatcher');
  });

  it('is drawn for an administrator even where nobody has answered «Отпуск / отсутствие»', () => {
    const html = reserve(true, NO_ENGINEER_FILTER, false);
    expect(assignLink(html)?.href).toBe('/dispatcher');
    expect(html).not.toContain('data-reserve-absences');
  });
});

describe('«Отпуск / отсутствие» in the panel of «Календарь запаса»', () => {
  it('is a button for an administrator, and no link: it moves the tab through the page\'s callback', () => {
    const button = absencesButton(reserve(true));
    expect(button).toContain('type="button"');
    expect(button).toContain('Отпуск / отсутствие');
    expect(reserve(true)).not.toMatch(/<a [^>]*>[^<]*Отпуск/);
  });

  it('sits in the same panel as the two buttons of the period, after them', () => {
    const html = reserve(true);
    const tools = html.indexOf('data-reserve-tools=""');
    expect(tools).toBeGreaterThan(html.indexOf('Начало периода'));
    expect(tools).toBeLessThan(html.indexOf('Очередь работ по инженерам и датам'));
    expect(html.indexOf('data-reserve-assign=""')).toBeLessThan(html.indexOf('data-reserve-absences=""'));
  });
});

describe('what an expert sees', () => {
  it('neither button, in the widget and on the page', () => {
    for (const html of [reserve(false), page(['expert'], { tab: 'reserve' })]) {
      expect(html).toContain('data-schedule-reserve=');
      expect(html).not.toContain('data-reserve-tools');
      expect(html).not.toContain('Назначить работу');
      expect(html).not.toContain('Отпуск / отсутствие');
    }
  });
});

describe('«Календарь запаса» on the page', () => {
  it('gives an administrator both buttons, and the link names the engineer the address narrowed to', () => {
    const html = page(['admin'], { tab: 'reserve', engineer: EXPERT_B });
    expect(assignLink(html)?.href).toBe(`/dispatcher?expert=${EXPERT_B}`);
    expect(absencesButton(html)).toContain('Отпуск / отсутствие');
    expect(assignLink(page(['admin'], { tab: 'reserve' }))?.href).toBe('/dispatcher');
  });
});

describe('«Выполнено» opened in the mode of the absences', () => {
  const calendarHint = 'data-schedule-hint="calendar"';

  it('opens an administrator in «Выходные и отсутствия», the button saying «Готово»', () => {
    const html = page(['admin'], { tab: 'completed', mode: 'absences' });
    expect(html).toContain(calendarHint);
    expect(html).toMatch(/aria-pressed="true"[^>]*>Готово<\/button>/);
    // the day headings are toggles in this mode, and the plan cannot be edited at the same time
    expect(html).toContain('title="Сделать выходным"');
    expect(html).toMatch(/<button[^>]*disabled=""[^>]*>Изменить план<\/button>/);
  });

  it('opens an administrator in the plain view without the mode', () => {
    const html = page(['admin'], { tab: 'completed' });
    expect(html).not.toContain(calendarHint);
    expect(html).toContain('>Выходные и отсутствия</button>');
  });

  it('drops the mode for an expert, who has no such mode and no button for it', () => {
    const html = page(['expert'], { tab: 'completed', mode: 'absences' });
    expect(html).toContain('data-schedule-month="2026-11"');
    expect(html).not.toContain(calendarHint);
    expect(html).not.toContain('Выходные и отсутствия');
    expect(html).not.toContain('title="Сделать выходным"');
  });

  it('does not touch the reserve tab, which has no such mode', () => {
    const html = page(['admin'], { tab: 'reserve', mode: 'absences' });
    expect(html).toContain('data-schedule-reserve=');
    expect(html).not.toContain(calendarHint);
  });
});
