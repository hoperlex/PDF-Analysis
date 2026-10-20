/**
 * How an assignment reads in Russian, and which moves a viewer is offered (`W61-DISPATCHER-01`).
 *
 * **The offer mirrors the server's rule and decides nothing.** The API refuses every move on
 * its own evidence (`auditmanager.dispatch`); these functions only choose which buttons to
 * draw, so a button is never offered for a move the server is certain to refuse:
 *
 *   - `started` from `assigned`, `completed` from `in_progress`, `returned` from either — the
 *     current assignee, holding `expert`;
 *   - `reassigned` from `assigned`, `in_progress` or `returned`, `cancelled` from the same —
 *     an administrator.
 */

import type {
  Assignment,
  AssignmentEventKind,
  AssignmentStatus,
  AssignmentTransitionKind,
  Role,
} from '@/shared/api';

export const ASSIGNMENT_STATUS_LABELS: Readonly<Record<AssignmentStatus, string>> = {
  assigned: 'Назначено',
  in_progress: 'В работе',
  done: 'Выполнено',
  returned: 'Возвращено',
  cancelled: 'Отменено',
};

export const ASSIGNMENT_EVENT_LABELS: Readonly<Record<AssignmentEventKind, string>> = {
  assigned: 'Назначено',
  started: 'Взято в работу',
  completed: 'Выполнено',
  returned: 'Возвращено',
  reassigned: 'Переназначено',
  cancelled: 'Отменено',
};

/** The button text of each move. */
export const ASSIGNMENT_MOVE_LABELS: Readonly<Record<AssignmentTransitionKind, string>> = {
  started: 'Взять в работу',
  completed: 'Отметить выполненным',
  returned: 'Вернуть',
  reassigned: 'Переназначить',
  cancelled: 'Отменить',
};

/** Not terminal: work still in hand or awaiting an administrator. */
export const OPEN_ASSIGNMENT_STATUSES: readonly AssignmentStatus[] = ['assigned', 'in_progress', 'returned'];

export function isOpenAssignment(status: AssignmentStatus): boolean {
  return OPEN_ASSIGNMENT_STATUSES.includes(status);
}

const ASSIGNEE_MOVES: Readonly<Record<AssignmentStatus, readonly AssignmentTransitionKind[]>> = {
  assigned: ['started', 'returned'],
  in_progress: ['completed', 'returned'],
  returned: [],
  done: [],
  cancelled: [],
};

const ADMIN_MOVES: Readonly<Record<AssignmentStatus, readonly AssignmentTransitionKind[]>> = {
  assigned: ['reassigned', 'cancelled'],
  in_progress: ['reassigned', 'cancelled'],
  returned: ['reassigned', 'cancelled'],
  done: [],
  cancelled: [],
};

/**
 * The moves to offer on `assignment`. `viewerIsAssignee` is whether the viewer is the current
 * assignee — known for sure on «Мои задачи», which lists only the viewer's own work, and from
 * `getMe` on the dispatcher's screen; `null` while it is not known, which offers no assignee
 * move.
 */
export function movesFor(
  assignment: Pick<Assignment, 'status'>,
  roles: readonly Role[],
  viewerIsAssignee: boolean | null,
): readonly AssignmentTransitionKind[] {
  const moves: AssignmentTransitionKind[] = [];
  if (viewerIsAssignee === true && roles.includes('expert')) moves.push(...ASSIGNEE_MOVES[assignment.status]);
  if (roles.includes('admin')) moves.push(...ADMIN_MOVES[assignment.status]);
  return moves;
}

/** Whether this role set may create assignments — the API's `createAssignment` register. */
export function canAssignWork(roles: readonly Role[]): boolean {
  return roles.includes('admin');
}

/** What the assignment covers, in words: the project, and the document when there is one. */
export function assignmentScope(assignment: Pick<Assignment, 'project_name' | 'document_title'>): string {
  return assignment.document_title === null
    ? `Проект «${assignment.project_name}»`
    : `Документ «${assignment.document_title}» проекта «${assignment.project_name}»`;
}
