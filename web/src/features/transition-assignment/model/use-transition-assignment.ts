'use client';

/**
 * `transitionAssignment` (`W61-DISPATCHER-01`): start, complete, return, reassign or cancel one
 * assignment.
 *
 * **No idempotency key, and none is needed.** A request equal to the assignment's latest event
 * answers it unchanged, and any other move the machine does not declare is `409
 * state_transition_not_allowed` and changes nothing. `retry: false` all the same: nothing here
 * repeats a write on its own.
 *
 * **What a success or a refusal changes.** Every key under `assignments` — the list's row, the
 * detail's history and the home screen's «Мои задачи» — so `assignments.all()` is invalidated
 * either way: after a refusal the screen reads what is actually stored.
 *
 * **One request in flight per intent** (`WEB-FOLLOWUPS-02`, `D-195`). A second press of the
 * same move on the same assignment before the first answer used to send a second `POST`,
 * answered unchanged or as `state_transition_not_allowed`, and the screen showed the later
 * answer. A press that finds the same move (assignment, kind, trimmed reason, new assignee)
 * in flight now joins the request already sent; the gate reopens when it settles. A different
 * move on the same assignment is a different intent and is sent.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import type { Assignment, AssignmentTransitionKind } from '@/shared/api';
import { queryKeys, transitionAssignment } from '@/shared/api';

export interface AssignmentMove {
  readonly assignmentUid: string;
  readonly kind: AssignmentTransitionKind;
  readonly reason?: string;
  readonly newAssigneeUserUid?: string;
}

/** What makes two presses one intent: the same assignment, move, trimmed reason and assignee. */
export function moveIntent({ assignmentUid, kind, reason, newAssigneeUserUid }: AssignmentMove): string {
  return JSON.stringify([assignmentUid, kind, reason?.trim() ?? '', newAssigneeUserUid ?? null]);
}

export function useTransitionAssignment() {
  const client = useQueryClient();
  const flightRef = useRef<{
    readonly intent: string;
    readonly promise: Promise<Assignment>;
  } | null>(null);

  const send = async ({ assignmentUid, kind, reason, newAssigneeUserUid }: AssignmentMove) =>
    (
      await transitionAssignment({
        path: { assignment_uid: assignmentUid },
        body: {
          kind,
          ...(reason === undefined || reason.trim() === '' ? {} : { reason: reason.trim() }),
          ...(newAssigneeUserUid === undefined ? {} : { new_assignee_user_uid: newAssigneeUserUid }),
        },
      })
    ).data;

  return useMutation<Assignment, unknown, AssignmentMove>({
    mutationFn: (move) => {
      const intent = moveIntent(move);
      const held = flightRef.current;
      if (held !== null && held.intent === intent) return held.promise;
      const promise: Promise<Assignment> = send(move).finally(() => {
        if (flightRef.current?.promise === promise) flightRef.current = null;
      });
      flightRef.current = { intent, promise };
      return promise;
    },
    retry: false,
    onSettled: () => {
      void client.invalidateQueries({ queryKey: queryKeys.assignments.all() });
    },
  });
}
