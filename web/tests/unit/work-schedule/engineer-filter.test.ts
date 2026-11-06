/**
 * The engineer filter and «Просрочки» of «График работ» (`D-319`): which rows a filter leaves, what an address that names
 * an unknown engineer means, and which open assignments count as late — a planned date before today, never today's, never
 * one without a date.
 */

import { describe, expect, it } from 'vitest';

import { readScheduleAddress, scheduleSearch } from '@/_pages/work-schedule';
import type { WorkScheduleReserveEngineer, WorkScheduleReserveItem } from '@/shared/api';
import {
  NO_ENGINEER_FILTER,
  narrowEngineers,
  overdueCount,
  parseEngineer,
  resolveEngineerFilter,
} from '@/entities/work-schedule';

import { EXPERT_A, EXPERT_B, assignmentUid, monthFixture, reserveFixture } from './fixtures';

const TODAY = '2026-11-06';
const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

function item(n: number, plannedOn?: string): WorkScheduleReserveItem {
  return {
    assignment_uid: assignmentUid(n),
    status: 'assigned',
    project_uid: PROJECT,
    project_name: 'Жилой дом, корпус 2',
    ...(plannedOn === undefined ? {} : { planned_on: plannedOn }),
  };
}

function reserve(...rows: readonly (readonly [string, readonly WorkScheduleReserveItem[]])[]): WorkScheduleReserveEngineer[] {
  return rows.map(([uid, items]) => ({ user_uid: uid, label: uid, items: [...items] }));
}

describe('the engineer in the address', () => {
  it('is read only when it is an account identifier', () => {
    expect(parseEngineer(EXPERT_A)).toBe(EXPERT_A);
    expect(parseEngineer('')).toBeNull();
    expect(parseEngineer('Иванова Анна')).toBeNull();
    expect(parseEngineer('usr_short')).toBeNull();
    expect(parseEngineer(undefined)).toBeNull();
    expect(parseEngineer(null)).toBeNull();
  });

  it('rides next to the tab, the month and the start, and is left out when nobody is chosen', () => {
    const read = readScheduleAddress({ tab: 'reserve', start: '2026-11-02', engineer: EXPERT_B }, TODAY);
    expect(read).toEqual({ tab: 'reserve', month: '2026-11', start: '2026-11-02', engineer: EXPERT_B });
    expect(scheduleSearch(read)).toBe(`?tab=reserve&start=2026-11-02&engineer=${EXPERT_B}`);
    expect(scheduleSearch({ ...read, tab: 'completed' })).toBe(`?month=2026-11&engineer=${EXPERT_B}`);
    expect(scheduleSearch({ ...read, tab: 'completed', engineer: null })).toBe('?month=2026-11');
    expect(readScheduleAddress({ engineer: 'not-a-user' }, TODAY).engineer).toBeNull();
    expect(readScheduleAddress({}, TODAY).engineer).toBeNull();
  });
});

describe('the engineers a filter leaves', () => {
  const engineers = monthFixture().engineers;

  it('keeps everyone when nobody is chosen', () => {
    expect(narrowEngineers(engineers, NO_ENGINEER_FILTER)).toEqual(engineers);
    expect(resolveEngineerFilter(engineers, null)).toEqual(NO_ENGINEER_FILTER);
  });

  it('narrows to the chosen engineer, in the month and in the reserve alike', () => {
    const filter = resolveEngineerFilter(engineers, EXPERT_B);
    expect(filter).toEqual({ uid: EXPERT_B, unknown: false });
    expect(narrowEngineers(engineers, filter).map((engineer) => engineer.user_uid)).toEqual([EXPERT_B]);
    expect(narrowEngineers(reserveFixture().engineers, filter).map((engineer) => engineer.user_uid)).toEqual([EXPERT_B]);
  });

  it('shows everyone, and says so, when the address names an engineer the read does not carry', () => {
    const filter = resolveEngineerFilter(engineers, 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z');
    expect(filter).toEqual({ uid: null, unknown: true });
    expect(narrowEngineers(engineers, filter)).toEqual(engineers);
  });

  it('leaves an expert their own row: a read that carries one engineer cannot be widened', () => {
    const own = engineers.slice(0, 1);
    expect(narrowEngineers(own, resolveEngineerFilter(own, null))).toEqual(own);
    expect(resolveEngineerFilter(own, EXPERT_B).unknown).toBe(true);
  });
});

describe('«Просрочки»: open assignments planned before today', () => {
  it('counts a day before today and not today, tomorrow or an assignment without a date', () => {
    const rows = reserve([EXPERT_A, [
      item(1, '2026-11-05'),
      item(2, TODAY),
      item(3, '2026-11-07'),
      item(4),
    ]]);
    expect(overdueCount(rows, TODAY, NO_ENGINEER_FILTER)).toBe(1);
  });

  it('moves with the day: the same assignments are late a day later and not yet a day earlier', () => {
    const rows = reserve([EXPERT_A, [item(1, '2026-11-05'), item(2, TODAY)]]);
    expect(overdueCount(rows, '2026-11-05', NO_ENGINEER_FILTER)).toBe(0);
    expect(overdueCount(rows, TODAY, NO_ENGINEER_FILTER)).toBe(1);
    expect(overdueCount(rows, '2026-11-07', NO_ENGINEER_FILTER)).toBe(2);
  });

  it('reads dates as calendar days across a month and a year boundary', () => {
    const rows = reserve([EXPERT_A, [item(1, '2026-10-31'), item(2, '2025-12-31'), item(3, '2026-11-01')]]);
    expect(overdueCount(rows, '2026-11-01', NO_ENGINEER_FILTER)).toBe(2);
    expect(overdueCount(rows, '2026-01-01', NO_ENGINEER_FILTER)).toBe(1);
  });

  it('counts every status the reserve carries and every engineer when nobody is chosen', () => {
    const rows = reserve(
      [EXPERT_A, [{ ...item(1, '2026-10-01'), status: 'in_progress' }, { ...item(2, '2026-10-02'), status: 'returned' }]],
      [EXPERT_B, [item(3, '2026-10-03')]],
    );
    expect(overdueCount(rows, TODAY, NO_ENGINEER_FILTER)).toBe(3);
  });

  it('counts only the chosen engineer\'s with a filter, and all of them when the filter is unknown', () => {
    const rows = reserve(
      [EXPERT_A, [item(1, '2026-10-01'), item(2, '2026-10-02')]],
      [EXPERT_B, [item(3, '2026-10-03'), item(4)]],
    );
    expect(overdueCount(rows, TODAY, { uid: EXPERT_A, unknown: false })).toBe(2);
    expect(overdueCount(rows, TODAY, { uid: EXPERT_B, unknown: false })).toBe(1);
    expect(overdueCount(rows, TODAY, { uid: null, unknown: true })).toBe(3);
  });

  it('is zero for nobody and for engineers with no work', () => {
    expect(overdueCount([], TODAY, NO_ENGINEER_FILTER)).toBe(0);
    expect(overdueCount(reserve([EXPERT_A, []]), TODAY, NO_ENGINEER_FILTER)).toBe(0);
  });

  it('on the reserve fixture, whose dated work sits on 3 November, is late from the 4th', () => {
    const rows = reserveFixture().engineers;
    expect(overdueCount(rows, '2026-11-03', NO_ENGINEER_FILTER)).toBe(0);
    expect(overdueCount(rows, '2026-11-04', NO_ENGINEER_FILTER)).toBe(2);
  });
});
