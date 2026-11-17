/**
 * «Счётчик» of «Выполнено» (`UIP-S14-02`): the column after «План» in the plan and fact table that says how many decisions of
 * the month an engineer accepted and rejected and what share was accepted — the server's two figures, the share counted here
 * as a whole percent — and «—» where nothing was decided. The total row adds the engineers up and counts the share of the sums.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { WorkScheduleEngineer, WorkScheduleMonth } from '@/shared/api';
import { NO_ENGINEER_FILTER, acceptedPercent, scheduleTotals } from '@/entities/work-schedule';
import type { WorkScheduleMode } from '@/widgets/work-schedule-month';
import { WorkScheduleMonthView } from '@/widgets/work-schedule-month';

import { newClient, renderScreen } from '../screens/harness';
import { EXPERT_A, EXPERT_B, monthFixture } from './fixtures';

const noop = () => undefined;

function view(
  schedule: WorkScheduleMonth = monthFixture(),
  initialMode: WorkScheduleMode = 'view',
  filter = NO_ENGINEER_FILTER,
): string {
  return renderScreen(newClient(), createElement(WorkScheduleMonthView, {
    schedule, admin: true, onMonth: noop, today: '2026-11-03', initialMode,
    filter, onEngineer: noop, overdue: { kind: 'ready', count: 0 },
  }));
}

/** The plan and fact table as rows of the visible text of their cells. */
function statsRows(html: string): string[][] {
  const table = /<table[^>]*data-schedule-stats[\s\S]*?<\/table>/.exec(html)?.[0] ?? '';
  return [...table.matchAll(/<tr[\s\S]*?<\/tr>/g)].map((row) =>
    [...row[0].matchAll(/<t[hd][^>]*>([\s\S]*?)<\/t[hd]>/g)].map((cell) => (cell[1] ?? '').replace(/<[^>]*>/g, '').trim()),
  );
}

function withDecisions(engineer: WorkScheduleEngineer, accepted: number, rejected: number): WorkScheduleEngineer {
  return { ...engineer, accepted_count: accepted, rejected_count: rejected };
}

function monthOf(...counts: readonly (readonly [number, number])[]): WorkScheduleMonth {
  const month = monthFixture();
  const [first, second] = month.engineers as [WorkScheduleEngineer, WorkScheduleEngineer];
  const [a, b] = counts;
  return {
    ...month,
    engineers: [
      withDecisions(first, a?.[0] ?? 0, a?.[1] ?? 0),
      withDecisions(second, b?.[0] ?? 0, b?.[1] ?? 0),
    ],
  };
}

describe('the share of accepted decisions', () => {
  it('is a whole percent of the decisions that stand, accepted and rejected together', () => {
    expect(acceptedPercent(9, 3)).toBe(75);
    expect(acceptedPercent(1, 2)).toBe(33);
    expect(acceptedPercent(2, 1)).toBe(67);
    expect(acceptedPercent(5, 0)).toBe(100);
  });

  it('is 0 % when everything was rejected, and has none when nothing was decided', () => {
    expect(acceptedPercent(0, 4)).toBe(0);
    expect(acceptedPercent(0, 0)).toBeNull();
  });
});

describe('the totals of the month', () => {
  it('add the engineers\' decisions up and count the share of the sums, not the mean of the shares', () => {
    const month = monthOf([9, 3], [1, 3]);
    const totals = scheduleTotals(month.engineers);
    expect(totals.accepted).toBe(10);
    expect(totals.rejected).toBe(6);
    // 10 of 16 is 63 %; the mean of 75 % and 25 % would be 50 %.
    expect(totals.acceptedPercent).toBe(63);
  });

  it('have no share while nobody decided anything', () => {
    const totals = scheduleTotals(monthOf([0, 0], [0, 0]).engineers);
    expect(totals).toMatchObject({ accepted: 0, rejected: 0, acceptedPercent: null });
  });
});

describe('«Счётчик» in the plan and fact table', () => {
  it('stands after «План» and before «Выполнение», and names its three figures', () => {
    const [head] = statsRows(view());
    expect(head).toEqual(['Инженер', 'Факт', 'Осталось', 'План', 'Счётчик: принято / отклонено / % принятых', 'Выполнение']);
  });

  it('says in the header what is counted: the decisions of the month, remarks and optimisations together', () => {
    const header = /<th[^>]*title="([^"]*)"[^>]*>\s*Счётчик/.exec(view())?.[1] ?? '';
    expect(header).toContain('Решения эксперта за месяц');
    expect(header).toContain('замечания и оптимизации вместе');
    expect(header).toContain('перенесённые из прошлой версии и снятые не входят');
  });

  it('shows accepted / rejected / the share for an engineer, «—» for one who decided nothing, and the sums in the total', () => {
    const rows = statsRows(view());
    expect(rows[1]).toEqual(['Иванова Анна', '5', '7', '12', '9 / 3 / 75%', '42%']);
    expect(rows[2]?.[0]).toBe('Петров Борис');
    expect(rows[2]?.[4]).toBe('—');
    expect(rows[3]).toEqual(['Всего по инженерам (2)', '5', '27', '32', '9 / 3 / 75%', '16%']);
  });

  it('marks a counter without decisions, so a missing figure is not read as 0 / 0 / 0 %', () => {
    const html = view();
    expect(html).toContain('data-schedule-counter="none">—</span>');
    expect(html).not.toContain('0 / 0');
  });

  it('shows 0 % for an engineer who rejected everything, which is a result and not a gap', () => {
    const rows = statsRows(view(monthOf([0, 4], [0, 0])));
    expect(rows[1]?.[4]).toBe('0 / 4 / 0%');
    expect(rows[3]?.[4]).toBe('0 / 4 / 0%');
  });

  it('gives the total «—» when nobody decided anything', () => {
    const rows = statsRows(view(monthOf([0, 0], [0, 0])));
    expect(rows.slice(1).map((row) => row[4])).toEqual(['—', '—', '—']);
  });

  it('counts the chosen engineer alone in the total, as the rows and the tiles do', () => {
    const rows = statsRows(view(monthOf([9, 3], [1, 3]), 'view', { uid: EXPERT_B, unknown: false }));
    expect(rows[1]).toEqual(['Петров Борис', '0', '20', '20', '1 / 3 / 25%', '0%']);
    expect(rows[2]).toEqual(['Всего по инженерам (1)', '0', '20', '20', '1 / 3 / 25%', '0%']);
    expect(rows.flat().join(' ')).not.toContain(EXPERT_A);
  });

  it('stays beside the plan\'s inputs in the mode that edits the plan', () => {
    const html = view(monthFixture(), 'plan');
    expect(html).toContain('aria-label="План: Иванова Анна"');
    const rows = statsRows(html);
    expect(rows[0]).toContain('Счётчик: принято / отклонено / % принятых');
    expect(rows[1]?.[4]).toBe('9 / 3 / 75%');
    expect(rows[3]?.[4]).toBe('9 / 3 / 75%');
  });

  it('is drawn for an expert\'s own row as well', () => {
    const month = monthFixture();
    const [own] = month.engineers as [WorkScheduleEngineer];
    const html = renderScreen(newClient(), createElement(WorkScheduleMonthView, {
      schedule: { ...month, engineers: [own] }, admin: false, onMonth: noop, today: '2026-11-03',
      filter: NO_ENGINEER_FILTER, onEngineer: noop, overdue: { kind: 'ready', count: 0 },
    }));
    expect(statsRows(html)[1]?.[4]).toBe('9 / 3 / 75%');
  });
});
