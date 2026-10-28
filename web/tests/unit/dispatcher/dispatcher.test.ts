/**
 * «Диспетчер» on the web side (`W61-DISPATCHER-01`): which moves a viewer is offered, what a
 * refusal says, who may be named as an assignee, and what the dispatcher's screen draws for
 * an administrator and for an expert.
 *
 * The offer mirrors the server's rule (`auditmanager.dispatch.policy`), cell by cell against
 * an independent statement of it below; the server still decides every move.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { DispatcherPage, expertOptions } from '@/_pages/dispatcher';
import type { Account, Assignment, AssignmentPage, AssignmentStatus, ErrorEnvelope, Role } from '@/shared/api';
import { ASSIGNMENT_STATUS_VALUES, ApiError, queryKeys } from '@/shared/api';
import {
  ASSIGNMENT_PAGE_LIMIT,
  ASSIGNMENT_STATUS_LABELS,
  assignmentFailure,
  assignmentScope,
  canAssignWork,
  isOpenAssignment,
  movesFor,
} from '@/entities/assignment';
import { USER_PAGE_LIMIT } from '@/entities/user';
import { AssignmentRows } from '@/widgets/assignment-board';

import { newClient, renderScreen } from '../screens/harness';

const ME = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8A';
const OTHER = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8B';

function assignment(status: AssignmentStatus, over: Partial<Assignment> = {}): Assignment {
  return {
    assignment_uid: `asg_01J9ZQ8K7NHVXW3T2R5M6P4Q8${status.length}`,
    project_uid: 'prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8A',
    project_name: 'Школа',
    document_uid: null,
    document_title: null,
    assignee_user_uid: ME,
    assignee_label: 'Петрова А. С.',
    created_by_user_uid: OTHER,
    created_by_label: 'Иванов И. И.',
    note: null,
    status,
    status_reason: null,
    created_at: '2026-10-20T08:00:00Z',
    updated_at: '2026-10-20T09:00:00Z',
    ...over,
  };
}

/** The server's table, restated: (status) -> the assignee's moves, the administrator's moves. */
const INTENDED: Record<AssignmentStatus, { assignee: string[]; admin: string[] }> = {
  assigned: { assignee: ['started', 'returned'], admin: ['reassigned', 'cancelled'] },
  in_progress: { assignee: ['completed', 'returned'], admin: ['reassigned', 'cancelled'] },
  returned: { assignee: [], admin: ['reassigned', 'cancelled'] },
  done: { assignee: [], admin: [] },
  cancelled: { assignee: [], admin: [] },
};

describe('the moves offered mirror the server table', () => {
  for (const status of ASSIGNMENT_STATUS_VALUES) {
    it(`${status}: the assignee expert, an administrator, both, neither`, () => {
      const row = assignment(status);
      expect([...movesFor(row, ['expert'], true)]).toEqual(INTENDED[status].assignee);
      expect([...movesFor(row, ['admin'], false)]).toEqual(INTENDED[status].admin);
      expect([...movesFor(row, ['admin', 'expert'], true)]).toEqual([
        ...INTENDED[status].assignee,
        ...INTENDED[status].admin,
      ]);
      // Not the assignee, or not known to be, or an assignee without `expert`: no assignee move.
      expect([...movesFor(row, ['expert'], false)]).toEqual([]);
      expect([...movesFor(row, ['expert'], null)]).toEqual([]);
      expect([...movesFor(row, ['admin'], true)]).toEqual(INTENDED[status].admin);
      expect([...movesFor(row, [], true)]).toEqual([]);
    });
  }

  it('open is exactly the non-terminal statuses, and only admin assigns', () => {
    expect(ASSIGNMENT_STATUS_VALUES.filter(isOpenAssignment)).toEqual(['assigned', 'in_progress', 'returned']);
    expect(canAssignWork(['admin'])).toBe(true);
    expect(canAssignWork(['expert'])).toBe(false);
    expect(Object.keys(ASSIGNMENT_STATUS_LABELS).sort()).toEqual([...ASSIGNMENT_STATUS_VALUES].sort());
  });

  it('names the scope: the project, or the document of the project', () => {
    expect(assignmentScope(assignment('assigned'))).toBe('Проект «Школа»');
    expect(assignmentScope(assignment('assigned', { document_title: 'КЖ-1' }))).toBe('Документ «КЖ-1» проекта «Школа»');
  });
});

function refusal(code: ErrorEnvelope['error_code'], details: NonNullable<ErrorEnvelope['details']>): ApiError {
  return new ApiError(409, {
    contract_version: '1.11.0',
    error_code: code,
    message: 'raw server message',
    correlation_id: 'cid-dispatch-1',
    retryable: false,
    details,
  }, 'cid-dispatch-1');
}

describe('what a refusal says', () => {
  it('reads the closed detail values the contract registers', () => {
    expect(assignmentFailure(refusal('conflict', { conflict_reason: 'assignment_open' })).kind).toBe('assignment_open');
    expect(assignmentFailure(refusal('validation_failed', { field: 'assignee_user_uid', constraint: 'active_expert_required' })).kind)
      .toBe('active_expert_required');
    expect(assignmentFailure(refusal('validation_failed', { field: 'new_assignee_user_uid', constraint: 'differs_from_current_assignee' })).kind)
      .toBe('differs_from_current_assignee');
    expect(assignmentFailure(refusal('permission_denied', { required_capability: 'assignment:assignee' })).kind).toBe('assignee_only');
    const state = assignmentFailure(refusal('state_transition_not_allowed', { machine: 'work_assignment' }));
    expect(state.kind).toBe('state_transition_not_allowed');
    expect(state.detail).not.toContain('raw server message');
    expect(state.correlationId).toBe('cid-dispatch-1');
  });
});

function account(roles: Role[], over: Partial<Account> = {}): Account {
  return {
    user_uid: OTHER,
    login: 'expert@example.test',
    display_label: 'Экспертова Д. Д.',
    last_name: 'Экспертова',
    first_name: 'Дарья',
    middle_name: null,
    roles,
    profile_complete: true,
    is_default_credential: false,
    archived_at: null,
    ...over,
  };
}

describe('who a creation or reassignment may name', () => {
  it('active accounts holding expert, by their label', () => {
    expect(
      expertOptions([
        account(['expert']),
        account(['admin'], { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8C' }),
        account(['expert'], { user_uid: 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8D', archived_at: '2026-10-01T00:00:00Z' }),
        account(['admin', 'expert'], { user_uid: ME, display_label: 'Петрова А. С.' }),
      ]),
    ).toEqual([
      { userUid: OTHER, label: 'Экспертова Д. Д.' },
      { userUid: ME, label: 'Петрова А. С.' },
    ]);
  });
});

describe('the dispatcher screen', () => {
  const page: AssignmentPage = {
    items: [assignment('assigned'), assignment('returned', { assignee_user_uid: OTHER, assignee_label: 'Экспертова Д. Д.', status_reason: 'Не мой раздел' })],
    page: { next_cursor: null },
  };

  function seeded(roles: Role[]) {
    const client = newClient();
    client.setQueryData(queryKeys.assignments.list({ limit: ASSIGNMENT_PAGE_LIMIT }), page);
    client.setQueryData(queryKeys.account.me(), account(roles, { user_uid: ME }));
    client.setQueryData(queryKeys.users.list({ includeArchived: false, limit: USER_PAGE_LIMIT }), {
      items: [account(['expert'])],
      page: { next_cursor: null },
    });
    return client;
  }

  it('an administrator gets the creation form, every row and the administrator\'s moves', () => {
    const markup = renderScreen(seeded(['admin']), createElement(DispatcherPage, { roles: ['admin'] }));
    expect(markup).toContain('data-create-assignment=""');
    expect(markup).toContain('Только мои');
    expect(markup).toContain('data-assignment-move="reassigned"');
    expect(markup).toContain('data-assignment-move="cancelled"');
    expect(markup).not.toContain('data-assignment-move="started"');
    expect(markup).toContain('Причина: Не мой раздел');
  });

  it('an expert gets no form, and the assignee\'s moves only on their own row', () => {
    const markup = renderScreen(seeded(['expert']), createElement(DispatcherPage, { roles: ['expert'] }));
    expect(markup).not.toContain('data-create-assignment=""');
    expect(markup).not.toContain('Только мои');
    expect(markup).toContain('data-assignment-move="started"');
    expect(markup).not.toContain('data-assignment-move="reassigned"');
  });

  it('the rows link the project and the document', () => {
    const markup = renderScreen(
      newClient(),
      createElement(AssignmentRows, {
        items: [assignment('in_progress', { document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8A', document_title: 'КЖ-1' })],
        roles: ['expert'],
        viewerUid: ME,
        experts: [],
      }),
    );
    expect(markup).toContain('href="/projects/prj_01J9ZQ8K7NHVXW3T2R5M6P4Q8A/documents/doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8A"');
    expect(markup).toContain('data-assignment-move="completed"');
  });
});
