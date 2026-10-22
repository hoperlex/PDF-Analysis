'use client';

/**
 * One assignment's history, oldest event first (`W61-DISPATCHER-01`): what happened, who did it
 * and when, the reason and the new assignee where an event carries one. Read on demand.
 */

import type { AssignmentEvent } from '@/shared/api';
import { formatInstant } from '@/shared/lib';
import { ErrorState, LoadingState } from '@/shared/ui';
import { ASSIGNMENT_EVENT_LABELS, assignmentFailure, useAssignment } from '@/entities/assignment';

import styles from './assignment-board.module.css';

export function AssignmentHistoryView({ history }: { readonly history: readonly AssignmentEvent[] }) {
  return (
    <ol className={styles.history} data-assignment-history="">
      {history.map((event) => (
        <li key={event.event_id} data-assignment-event={event.kind}>
          <strong>{ASSIGNMENT_EVENT_LABELS[event.kind]}</strong> — {event.actor_label},{' '}
          {formatInstant(event.occurred_at)}
          {event.new_assignee_label === null ? null : <>; новый ответственный: {event.new_assignee_label}</>}
          {event.reason === null ? null : <>; причина: {event.reason}</>}
        </li>
      ))}
    </ol>
  );
}

export function AssignmentHistory({ assignmentUid }: { readonly assignmentUid: string }) {
  const detail = useAssignment(assignmentUid);
  if (detail.isPending) return <LoadingState what="историю назначения" />;
  if (detail.isError) {
    const failure = assignmentFailure(detail.error);
    return (
      <div data-assignment-history-failure={failure.kind}>
        <ErrorState
          title="История назначения не загружена."
          detail={failure.detail}
          correlationId={failure.correlationId}
          onRetry={() => void detail.refetch()}
        />
      </div>
    );
  }
  return <AssignmentHistoryView history={detail.data.history} />;
}
