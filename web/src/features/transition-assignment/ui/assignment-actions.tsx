'use client';

/**
 * The moves one viewer is offered on one assignment (`W61-DISPATCHER-01`).
 *
 * `moves` comes from `movesFor` (entity `assignment`), which mirrors the server's rule; the
 * server still decides every move. A return asks for its reason first; a reassignment asks for
 * the new expert (the list an administrator's screen reads through `listUsers`); a
 * cancellation takes an optional reason. One request per press: the controls are disabled
 * while a move is in flight.
 */

import { useState } from 'react';

import type { Assignment, AssignmentTransitionKind } from '@/shared/api';
import { ErrorState } from '@/shared/ui';
import { ASSIGNMENT_MOVE_LABELS, assignmentFailure } from '@/entities/assignment';

import { useTransitionAssignment } from '../model/use-transition-assignment';
import styles from './assignment-actions.module.css';

/** An expert a reassignment may name: an active account holding `expert`. */
export interface ExpertOption {
  readonly userUid: string;
  readonly label: string;
}

export interface AssignmentActionsProps {
  readonly assignment: Assignment;
  readonly moves: readonly AssignmentTransitionKind[];
  /** Active experts, for a reassignment; omitted where no reassignment is offered. */
  readonly experts?: readonly ExpertOption[];
}

type Draft =
  | { readonly kind: 'returned'; readonly reason: string }
  | { readonly kind: 'cancelled'; readonly reason: string }
  | { readonly kind: 'reassigned'; readonly assignee: string; readonly reason: string };

export function AssignmentActions({ assignment, moves, experts = [] }: AssignmentActionsProps) {
  const move = useTransitionAssignment();
  const [draft, setDraft] = useState<Draft | null>(null);

  if (moves.length === 0) return null;

  const send = (kind: AssignmentTransitionKind, extra: { reason?: string; newAssigneeUserUid?: string } = {}) => {
    move.mutate(
      { assignmentUid: assignment.assignment_uid, kind, ...extra },
      { onSuccess: () => setDraft(null) },
    );
  };

  const candidates = experts.filter((expert) => expert.userUid !== assignment.assignee_user_uid || assignment.status === 'returned');

  return (
    <div className={styles.actions} data-assignment-actions={assignment.assignment_uid}>
      {draft === null ? (
        <div className={styles.buttons}>
          {moves.map((kind) => (
            <button
              key={kind}
              type="button"
              className={`am-button am-button--small${kind === 'started' || kind === 'completed' ? '' : ' am-button--quiet'}`}
              disabled={move.isPending}
              data-assignment-move={kind}
              onClick={() => {
                if (kind === 'started' || kind === 'completed') send(kind);
                else if (kind === 'reassigned') setDraft({ kind, assignee: '', reason: '' });
                else setDraft({ kind, reason: '' });
              }}
            >
              {ASSIGNMENT_MOVE_LABELS[kind]}
            </button>
          ))}
        </div>
      ) : (
        <form
          className={styles.draft}
          data-assignment-draft={draft.kind}
          onSubmit={(event) => {
            event.preventDefault();
            if (draft.kind === 'reassigned') {
              if (draft.assignee === '') return;
              send('reassigned', { newAssigneeUserUid: draft.assignee, reason: draft.reason });
            } else {
              if (draft.kind === 'returned' && draft.reason.trim() === '') return;
              send(draft.kind, { reason: draft.reason });
            }
          }}
        >
          {draft.kind === 'reassigned' ? (
            <label className={styles.field}>
              Новый ответственный
              <select
                value={draft.assignee}
                required
                onChange={(event) => setDraft({ ...draft, assignee: event.target.value })}
              >
                <option value="">Выберите эксперта</option>
                {candidates.map((expert) => (
                  <option key={expert.userUid} value={expert.userUid}>
                    {expert.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
          <label className={styles.field}>
            {draft.kind === 'returned' ? 'Причина возврата' : 'Причина (необязательно)'}
            <textarea
              value={draft.reason}
              maxLength={2000}
              rows={2}
              required={draft.kind === 'returned'}
              onChange={(event) => setDraft({ ...draft, reason: event.target.value })}
            />
          </label>
          <div className={styles.buttons}>
            <button type="submit" className="am-button am-button--small" disabled={move.isPending}>
              {ASSIGNMENT_MOVE_LABELS[draft.kind]}
            </button>
            <button
              type="button"
              className="am-button am-button--quiet am-button--small"
              disabled={move.isPending}
              onClick={() => setDraft(null)}
            >
              Не менять
            </button>
          </div>
        </form>
      )}
      {move.isError ? (() => {
        const failure = assignmentFailure(move.error);
        return (
          <div data-assignment-move-failure={failure.kind}>
            <ErrorState title="Действие не выполнено." detail={failure.detail} correlationId={failure.correlationId} />
          </div>
        );
      })() : null}
    </div>
  );
}
