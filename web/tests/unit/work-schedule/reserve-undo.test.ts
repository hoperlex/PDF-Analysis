/**
 * «Отменить последнее действие» of «Календарь запаса» (the original's undo, `D-319`): the moves that put a move back are
 * read from the calendar the move was made from, so the undo restores both the day and, for a reassignment, the engineer.
 */

import { describe, expect, it } from 'vitest';

import type { WorkScheduleReserveItem } from '@/shared/api';
import { inverseMoves } from '@/widgets/reserve-calendar';

const item = (uid: string, plannedOn?: string): WorkScheduleReserveItem => ({
  assignment_uid: uid as WorkScheduleReserveItem['assignment_uid'], project_name: 'Школа № 7', project_uid: 'prj_1' as WorkScheduleReserveItem['project_uid'],
  status: 'assigned', ...(plannedOn === undefined ? {} : { planned_on: plannedOn }),
});

describe('the inverse of a move', () => {
  const standing = new Map([
    ['asg_a', { item: item('asg_a', '2026-11-09'), engineerUid: 'usr_ann' }],
    ['asg_b', { item: item('asg_b'), engineerUid: 'usr_bob' }],
  ]);

  it('puts a moved assignment back on its day', () => {
    expect(inverseMoves([{ assignmentUid: 'asg_a', plannedOn: '2026-11-12' }], standing))
      .toEqual([{ assignmentUid: 'asg_a', plannedOn: '2026-11-09' }]);
  });

  it('puts an assignment that had no date back to «без даты»', () => {
    expect(inverseMoves([{ assignmentUid: 'asg_b', plannedOn: '2026-11-12' }], standing))
      .toEqual([{ assignmentUid: 'asg_b', plannedOn: null }]);
  });

  it('puts a reassigned assignment back with its engineer, and restores no engineer it did not change', () => {
    expect(inverseMoves([
      { assignmentUid: 'asg_a', plannedOn: '2026-11-09', assigneeUserUid: 'usr_bob' },
      { assignmentUid: 'asg_b', plannedOn: '2026-11-10' },
    ], standing)).toEqual([
      { assignmentUid: 'asg_a', plannedOn: '2026-11-09', assigneeUserUid: 'usr_ann' },
      { assignmentUid: 'asg_b', plannedOn: null },
    ]);
  });

  it('leaves out an assignment the calendar did not hold', () => {
    expect(inverseMoves([{ assignmentUid: 'asg_gone', plannedOn: '2026-11-12' }], standing)).toEqual([]);
  });
});
