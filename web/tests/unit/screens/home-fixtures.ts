/**
 * The reads of the home page at `/`, as `home.test.ts` seeds them -- shared with the styling census (`tests/unit/styles/screens.ts`), which
 * renders the loaded page for an expert and for an administrator. One set of fixtures, so the census draws exactly the states the page's own
 * test holds.
 */

import type { Assignment, AssignmentPage, DashboardSummary, Project, ProjectPage, RegistrationRequestPage, Role } from '@/shared/api';
import { RUN_STATE_VALUES, VERDICT_VALUES, queryKeys } from '@/shared/api';
import { PROJECT_SECTIONS } from '@/entities/project';
import { RECENT_PROJECT_LIMIT } from '@/widgets/home-tiles';
import { MY_TASKS_LIMIT } from '@/widgets/my-tasks';

import { sectionAudit } from '../dashboard/audit-counts';
import { newClient } from './harness';

export const LABEL = 'Петрова А. С.';
/** The longest name form: a 60-letter last name in one word, a space, and the initials. */
export const LONGEST_LABEL = `${'Ж'.repeat(60)} И. О.`;

export const EXPERT: readonly Role[] = ['expert'];
export const ADMIN: readonly Role[] = ['expert', 'admin'];

export const ULID_STEM = '01J9ZQ8K7NHVXW3T2R5M6P4Q8';

/** Seven projects, newest first, as `listProjects` answers. */
export const PROJECTS: readonly Project[] = 'ABCDEFG'.split('').map((letter, index) => ({
  project_uid: `prj_${ULID_STEM}${letter}`,
  name: `Проект номер ${7 - index}`,
  created_at: `2026-09-${String(20 - index).padStart(2, '0')}T08:00:00.000Z`,
  document_count: index,
}));

export const NO_NEXT = { next_cursor: null } as const;

export function projectPage(items: readonly Project[]): ProjectPage {
  return { items: [...items], page: NO_NEXT };
}

export function summary(over: Partial<DashboardSummary> = {}): DashboardSummary {
  return {
    documents_by_project: [
      { project_uid: PROJECTS[0]!.project_uid, name: 'Проект номер 7', document_count: 2 },
      { project_uid: PROJECTS[1]!.project_uid, name: 'Проект номер 6', document_count: 3 },
    ],
    findings_by_verdict: VERDICT_VALUES.map((verdict, index) => ({ verdict, count: index + 4 })),
    run_activity: {
      by_state: RUN_STATE_VALUES.map((state, index) => ({ state, count: index })),
    },
    section_breakdown: [
      ...PROJECT_SECTIONS.map((section, index) => ({
        section: section.code,
        document_count: index,
        ...sectionAudit(index),
      })),
      { document_count: 5, ...sectionAudit(5) },
    ],
    awaiting_decision_findings: 11,
    ...over,
  };
}

/** A pending request whose every personal field is a word this file then looks for. */
export const APPLICANT = {
  created_user_uid: null,
  decided_at: null,
  decided_by: null,
  display_label: 'Секретова З. Я.',
  first_name: 'Зоя',
  last_name: 'Секретова',
  login: 'applicant@example.org',
  middle_name: 'Яковлевна',
  rejection_reason: 'Причина-которой-тут-не-место',
  request_id: `reg_${ULID_STEM}A`,
  status: 'pending',
  submitted_at: '2026-10-01T10:00:00.000Z',
} as const;

export function registrationPage(pendingTotal: number): RegistrationRequestPage {
  return { items: pendingTotal > 0 ? [APPLICANT] : [], page: NO_NEXT, pending_total: pendingTotal };
}

export const KEYS = {
  projects: queryKeys.projects.list(undefined, RECENT_PROJECT_LIMIT),
  summary: queryKeys.dashboard.summary(),
  registrations: queryKeys.registrations.list({ status: 'pending', limit: 1 }),
  assignments: queryKeys.assignments.list({ mine: true, limit: MY_TASKS_LIMIT }),
} as const;

/** `W61-DISPATCHER-01`: the expert's own work, one row per status, as `listAssignments` answers. */
export function assignment(letter: string, status: Assignment['status'], over: Partial<Assignment> = {}): Assignment {
  return {
    assignment_uid: `asg_${ULID_STEM}${letter}`,
    project_uid: PROJECTS[0]!.project_uid,
    project_name: 'Проект номер 7',
    document_uid: null,
    document_title: null,
    assignee_user_uid: `usr_${ULID_STEM}A`,
    assignee_label: 'Петрова А. С.',
    created_by_user_uid: `usr_${ULID_STEM}B`,
    created_by_label: 'Иванов И. И.',
    note: null,
    status,
    status_reason: null,
    created_at: '2026-10-20T08:00:00.000Z',
    updated_at: '2026-10-20T09:00:00.000Z',
    ...over,
  };
}

export const MY_WORK: AssignmentPage = {
  items: [
    assignment('A', 'assigned', { note: 'Проверить армирование до пятницы' }),
    assignment('B', 'in_progress', { document_uid: `doc_${ULID_STEM}B`, document_title: 'КЖ-1' }),
    assignment('C', 'returned', { status_reason: 'Не мой раздел' }),
    assignment('D', 'done'),
    assignment('E', 'cancelled'),
  ],
  page: NO_NEXT,
  total: 5,
  overview: [
    { status: 'assigned', count: 1 }, { status: 'in_progress', count: 1 }, { status: 'done', count: 1 },
    { status: 'returned', count: 1 }, { status: 'cancelled', count: 1 },
  ],
};

/** A client in which every read the home page makes has answered. */
export function loaded(over: { projects?: ProjectPage; summary?: DashboardSummary; pending?: number } = {}) {
  const client = newClient();
  client.setQueryData(KEYS.projects, over.projects ?? projectPage(PROJECTS.slice(0, 5)));
  client.setQueryData(KEYS.summary, over.summary ?? summary());
  client.setQueryData(KEYS.registrations, registrationPage(over.pending ?? 3));
  client.setQueryData(KEYS.assignments, MY_WORK);
  return client;
}
