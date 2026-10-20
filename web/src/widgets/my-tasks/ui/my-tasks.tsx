'use client';

/**
 * «Мои задачи» — the expert's open work on the home screen (`W61-DISPATCHER-01`).
 *
 * It reads `listAssignments` with `mine=true` — the server answers only the work currently
 * given to this account — and shows what is still open: «Назначено» and «В работе» with their
 * moves (take it, complete it, give it back with a reason), and «Возвращено» as a line that
 * waits for an administrator. Every row links to the project or the document. Because the
 * list is the viewer's own by the server's rule, the assignee's moves are offered on every
 * row; the server still decides each one.
 */

import Link from 'next/link';

import type { Assignment, Role } from '@/shared/api';
import { routes } from '@/shared/lib';
import { ErrorState, LoadingState } from '@/shared/ui';
import {
  AssignmentStatusLabel,
  assignmentFailure,
  assignmentScope,
  isOpenAssignment,
  movesFor,
  useAssignments,
} from '@/entities/assignment';
import { AssignmentActions } from '@/features/transition-assignment';

import styles from './my-tasks.module.css';

/** The block's own page: the newest open work first, a screenful at most. */
export const MY_TASKS_LIMIT = 50;

export interface MyTasksViewProps {
  readonly items: readonly Assignment[];
  readonly roles: readonly Role[];
}

function href(assignment: Assignment): string {
  return assignment.document_uid === null
    ? routes.project(assignment.project_uid)
    : routes.document(assignment.project_uid, assignment.document_uid);
}

/** The open rows of a page already in hand. Rendered by the static harness. */
export function MyTasksView({ items, roles }: MyTasksViewProps) {
  const open = items.filter((assignment) => isOpenAssignment(assignment.status));
  if (open.length === 0) {
    return (
      <p className="am-note" data-my-tasks="none">
        Открытых задач нет.
      </p>
    );
  }
  return (
    <ul className={styles.list} data-my-tasks={open.length}>
      {open.map((assignment) => (
        <li key={assignment.assignment_uid} className={styles.item} data-my-task={assignment.assignment_uid}>
          <div className={styles.head}>
            <Link href={href(assignment)}>{assignmentScope(assignment)}</Link>
            <AssignmentStatusLabel status={assignment.status} />
          </div>
          {assignment.note === null ? null : <p className={styles.text}>{assignment.note}</p>}
          {assignment.status === 'returned' ? (
            <p className={styles.text}>Возвращено вами; ждёт решения администратора.</p>
          ) : null}
          <AssignmentActions assignment={assignment} moves={movesFor(assignment, roles, true)} />
        </li>
      ))}
    </ul>
  );
}

export interface MyTasksProps {
  readonly roles: readonly Role[];
  /** The «Диспетчер» screen, where the whole list lives. */
  readonly listHref: string;
}

export function MyTasks({ roles, listHref }: MyTasksProps) {
  const query = useAssignments({ mine: true, limit: MY_TASKS_LIMIT });
  let body;
  if (query.isPending) {
    body = <LoadingState what="ваши задачи" />;
  } else if (query.isError) {
    const failure = assignmentFailure(query.error);
    body = (
      <div data-my-tasks-failure={failure.kind}>
        <ErrorState
          title="Задачи не загружены."
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={() => void query.refetch()}
        />
      </div>
    );
  } else {
    body = <MyTasksView items={query.data.items} roles={roles} />;
  }
  return (
    <section className="am-section" data-home-block="my-tasks">
      <h2>Мои задачи</h2>
      {body}
      <p className={styles.more}>
        <Link href={listHref}>Все назначения</Link>
      </p>
    </section>
  );
}
