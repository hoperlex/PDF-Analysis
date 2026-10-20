'use client';

/**
 * `createAssignment` (`W61-DISPATCHER-01`): an administrator gives a project, or one document
 * of it, to an expert.
 *
 * **No idempotency key, and none is needed.** One open assignment per scope: an exact repeat
 * (same expert and note) answers the open assignment, and anything else on that scope is `409
 * conflict` (`assignment_open`). `retry: false`; a success or a refusal invalidates
 * `assignments.all()`.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { Assignment } from '@/shared/api';
import { createAssignment, queryKeys } from '@/shared/api';

export interface NewAssignment {
  readonly projectUid: string;
  readonly documentUid: string | null;
  readonly assigneeUserUid: string;
  readonly note: string;
}

export function useCreateAssignment() {
  const client = useQueryClient();
  return useMutation<Assignment, unknown, NewAssignment>({
    mutationFn: async ({ projectUid, documentUid, assigneeUserUid, note }) =>
      (
        await createAssignment({
          body: {
            project_uid: projectUid,
            assignee_user_uid: assigneeUserUid,
            ...(documentUid === null ? {} : { document_uid: documentUid }),
            ...(note.trim() === '' ? {} : { note: note.trim() }),
          },
        })
      ).data,
    retry: false,
    onSettled: () => {
      void client.invalidateQueries({ queryKey: queryKeys.assignments.all() });
    },
  });
}
