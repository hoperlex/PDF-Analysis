'use client';

/**
 * «Диспетчер» — the list of assignments with its filters, moves and history
 * (`W61-DISPATCHER-01`).
 *
 * What the list holds is the server's decision: an administrator reads every assignment and may
 * narrow to «Только мои»; an expert reads only the work currently given to them, so the
 * checkbox is not drawn for them. The moves offered on each row are `movesFor`'s, from the
 * session's roles and whether the viewer is that row's assignee (`viewerUid`, from `getMe`;
 * `null` while unknown offers no assignee move). The server decides every move again.
 */

import Link from 'next/link';
import { useState } from 'react';

import type { Assignment, AssignmentStatus, Role } from '@/shared/api';
import { ASSIGNMENT_STATUS_VALUES } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { EmptyState, ErrorState, LoadingState } from '@/shared/ui';
import {
  ASSIGNMENT_PAGE_LIMIT,
  ASSIGNMENT_STATUS_LABELS,
  AssignmentStatusLabel,
  assignmentFailure,
  assignmentScope,
  movesFor,
  useAssignments,
} from '@/entities/assignment';
import type { ExpertOption } from '@/features/transition-assignment';
import { AssignmentActions } from '@/features/transition-assignment';

import { AssignmentHistory } from './assignment-history';
import styles from './assignment-board.module.css';

export interface AssignmentBoardProps {
  readonly roles: readonly Role[];
  /** The viewer's own account identity, or `null` while it is not known. */
  readonly viewerUid: string | null;
  /** Active experts, for an administrator's reassignment. */
  readonly experts: readonly ExpertOption[];
}

export interface AssignmentRowsProps extends AssignmentBoardProps {
  readonly items: readonly Assignment[];
}

function ScopeLink({ assignment }: { readonly assignment: Assignment }) {
  const href =
    assignment.document_uid === null
      ? routes.project(assignment.project_uid)
      : routes.document(assignment.project_uid, assignment.document_uid);
  return <Link href={href}>{assignmentScope(assignment)}</Link>;
}

/** The rows, from a page already in hand. Rendered by the static harness. */
export function AssignmentRows({ items, roles, viewerUid, experts }: AssignmentRowsProps) {
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div className={styles.tableWrap}>
      <table className={styles.table} data-assignment-board="">
        <thead>
          <tr>
            <th scope="col">Работа</th>
            <th scope="col">Исполнитель</th>
            <th scope="col">Состояние</th>
            <th scope="col">Обновлено</th>
            <th scope="col">Действия</th>
          </tr>
        </thead>
        <tbody>
          {items.map((assignment) => {
            const viewerIsAssignee = viewerUid === null ? null : viewerUid === assignment.assignee_user_uid;
            return (
              <tr key={assignment.assignment_uid} data-assignment={assignment.assignment_uid}>
                <td>
                  <ScopeLink assignment={assignment} />
                  {assignment.note === null ? null : <p className={styles.note}>{assignment.note}</p>}
                  <p className={styles.meta}>Назначил: {assignment.created_by_label}</p>
                </td>
                <td>{assignment.assignee_label}</td>
                <td>
                  <AssignmentStatusLabel status={assignment.status} />
                  {assignment.status_reason === null ? null : (
                    <p className={styles.note}>Причина: {assignment.status_reason}</p>
                  )}
                </td>
                <td>{formatInstant(assignment.updated_at)}</td>
                <td>
                  <AssignmentActions
                    assignment={assignment}
                    moves={movesFor(assignment, roles, viewerIsAssignee)}
                    experts={experts}
                  />
                  <button
                    type="button"
                    className="am-button am-button--quiet am-button--small"
                    data-assignment-history-toggle={assignment.assignment_uid}
                    onClick={() => setOpen(open === assignment.assignment_uid ? null : assignment.assignment_uid)}
                  >
                    {open === assignment.assignment_uid ? 'Скрыть историю' : 'История'}
                  </button>
                  {open === assignment.assignment_uid ? <AssignmentHistory assignmentUid={assignment.assignment_uid} /> : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function AssignmentBoard({ roles, viewerUid, experts }: AssignmentBoardProps) {
  const admin = roles.includes('admin');
  const [status, setStatus] = useState<AssignmentStatus | ''>('');
  const [mine, setMine] = useState(false);
  const [cursor, setCursor] = useState<string | undefined>();
  const query = useAssignments({
    limit: ASSIGNMENT_PAGE_LIMIT,
    ...(status === '' ? {} : { status }),
    ...(admin && mine ? { mine: true } : {}),
    ...(cursor === undefined ? {} : { cursor }),
  });

  return (
    <div>
      <div className={styles.filters}>
        <label className={styles.filter}>
          Состояние{' '}
          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value as AssignmentStatus | '');
              setCursor(undefined);
            }}
          >
            <option value="">Все</option>
            {ASSIGNMENT_STATUS_VALUES.map((value) => (
              <option key={value} value={value}>
                {ASSIGNMENT_STATUS_LABELS[value]}
              </option>
            ))}
          </select>
        </label>
        {admin ? (
          <label className={styles.filter}>
            <input
              type="checkbox"
              checked={mine}
              onChange={(event) => {
                setMine(event.target.checked);
                setCursor(undefined);
              }}
            />{' '}
            Только мои
          </label>
        ) : null}
      </div>
      {query.isPending ? <LoadingState what="назначения" /> : null}
      {query.isError ? (() => {
        const failure = assignmentFailure(query.error);
        return (
          <div data-assignment-board-failure={failure.kind}>
            <ErrorState
              title="Назначения не загружены."
              detail={failure.detail}
              correlationId={failure.correlationId}
              onRetry={() => void query.refetch()}
            />
          </div>
        );
      })() : null}
      {query.isSuccess ? (
        query.data.items.length === 0 ? (
          <EmptyState
            title="Назначений нет."
            detail={admin ? 'Назначьте работу эксперту формой выше.' : 'Вам пока ничего не назначено.'}
          />
        ) : (
          <>
            <AssignmentRows items={query.data.items} roles={roles} viewerUid={viewerUid} experts={experts} />
            <div className="am-pager">
              {cursor === undefined ? null : (
                <button className="am-button am-button--quiet am-button--small" type="button" onClick={() => setCursor(undefined)}>
                  В начало
                </button>
              )}
              {query.data.page.next_cursor ? (
                <button
                  className="am-button am-button--quiet am-button--small"
                  type="button"
                  onClick={() => setCursor(query.data.page.next_cursor ?? undefined)}
                >
                  Дальше
                </button>
              ) : null}
            </div>
          </>
        )
      ) : null}
    </div>
  );
}
