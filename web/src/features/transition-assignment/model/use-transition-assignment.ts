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
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { Assignment, AssignmentTransitionKind } from '@/shared/api';
import { queryKeys, transitionAssignment } from '@/shared/api';

export interface AssignmentMove {
  readonly assignmentUid: string;
  readonly kind: AssignmentTransitionKind;
  readonly reason?: string;
  readonly newAssigneeUserUid?: string;
}

export function useTransitionAssignment() {
  const client = useQueryClient();
  return useMutation<Assignment, unknown, AssignmentMove>({
    mutationFn: async ({ assignmentUid, kind, reason, newAssigneeUserUid }) =>
      (
        await transitionAssignment({
          path: { assignment_uid: assignmentUid },
          body: {
            kind,
            ...(reason === undefined || reason.trim() === '' ? {} : { reason: reason.trim() }),
            ...(newAssigneeUserUid === undefined ? {} : { new_assignee_user_uid: newAssigneeUserUid }),
          },
        })
      ).data,
    retry: false,
    onSettled: () => {
      void client.invalidateQueries({ queryKey: queryKeys.assignments.all() });
    },
  });
}
