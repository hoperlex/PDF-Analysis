/**
 * «График работ» fixtures (`UI-PARITY-P0P`): one November with weekends, an administrator's day off and working
 * Saturday, two experts (one on the default plan, absent two days, with three documents on one day), and a reserve with
 * every open status, a document and a project assignment, dated and «без даты».
 */

import type { WorkScheduleDay, WorkScheduleMonth, WorkScheduleReserve } from '@/shared/api';

const PROJECT = 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';
export const EXPERT_A = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8A';
export const EXPERT_B = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';

function documentUid(n: number): string {
  return `doc_01J9ZQ8K7NHVXW3T2R5M6P4Q${String(n).padStart(2, '0')}`;
}

export function assignmentUid(n: number): string {
  return `asg_01J9ZQ8K7NHVXW3T2R5M6P4Q${String(n).padStart(2, '0')}`;
}

function november(): WorkScheduleDay[] {
  const days: WorkScheduleDay[] = [];
  for (let n = 1; n <= 30; n += 1) {
    const day = `2026-11-${String(n).padStart(2, '0')}`;
    const weekday = new Date(Date.UTC(2026, 10, n)).getUTCDay();
    let entry: WorkScheduleDay = { day, day_off: weekday === 0 || weekday === 6 };
    if (n === 4) entry = { day, day_off: true, override: 'day_off' };
    if (n === 14) entry = { day, day_off: false, override: 'workday' };
    days.push(entry);
  }
  return days;
}

export function monthFixture(): WorkScheduleMonth {
  const done = (day: string, n: number, title: string) => ({
    day, project_uid: PROJECT, project_name: 'Жилой дом, корпус 2', document_uid: documentUid(n), document_title: title,
  });
  return {
    month: '2026-11',
    settings: { default_monthly_plan: 20, time_zone: 'Europe/Moscow' },
    days: november(),
    engineers: [
      {
        user_uid: EXPERT_A,
        label: 'Иванова Анна',
        plan: 12,
        plan_is_default: false,
        fact: 5,
        done: [
          done('2026-11-02', 1, 'АР Раздел 3'),
          done('2026-11-03', 2, 'КР Раздел 4'),
          done('2026-11-03', 3, 'ИОС1 Электроснабжение'),
          done('2026-11-03', 4, 'ИОС2 Водоснабжение'),
          done('2026-11-05', 5, 'ПОС Раздел 7'),
        ],
        absences: ['2026-11-10', '2026-11-11'],
      },
      { user_uid: EXPERT_B, label: 'Петров Борис', plan: 20, plan_is_default: true, fact: 0, done: [], absences: [] },
    ],
  };
}

export function reserveFixture(): WorkScheduleReserve {
  const days = november().slice(1, 15);
  return {
    start: '2026-11-02',
    days,
    engineers: [
      {
        user_uid: EXPERT_A,
        label: 'Иванова Анна',
        items: [
          { assignment_uid: assignmentUid(1), status: 'assigned', project_uid: PROJECT, project_name: 'Жилой дом, корпус 2', document_uid: documentUid(6), document_title: 'АР Раздел 3', planned_on: '2026-11-03' },
          { assignment_uid: assignmentUid(2), status: 'in_progress', project_uid: PROJECT, project_name: 'Жилой дом, корпус 2', planned_on: '2026-11-03' },
          { assignment_uid: assignmentUid(3), status: 'returned', project_uid: PROJECT, project_name: 'Школа на 550 мест' },
        ],
      },
      { user_uid: EXPERT_B, label: 'Петров Борис', items: [] },
    ],
  };
}
