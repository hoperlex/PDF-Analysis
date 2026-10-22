'use client';

/**
 * `createAssignment` (`W61-DISPATCHER-01`): an administrator gives a project, or one document
 * of it, to an expert.
 *
 * **No idempotency key, and none is needed.** One open assignment per scope: an exact repeat
 * (same expert and note) answers the open assignment, and anything else on that scope is `409
 * conflict` (`assignment_open`). `retry: false`; a success or a refusal invalidates
 * `assignments.all()`.
 *
 * **One request in flight per intent** (`WEB-FOLLOWUPS-02`, `D-195`). Without a key the second
 * press of a double press was a second `POST` whose answer was a replay or an
 * `assignment_open` refusal, and the form showed the later one. A press that finds the same
 * intent (project, document, expert, note) in flight now joins the request already sent; the
 * gate reopens when it settles, so a deliberate press afterwards is a new request.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import type { Assignment } from '@/shared/api';
import { createAssignment, queryKeys } from '@/shared/api';

export interface NewAssignment {
  readonly projectUid: string;
  readonly documentUid: string | null;
  readonly assigneeUserUid: string;
  readonly note: string;
}

/** What makes two presses one intent: the same scope, expert and trimmed note. */
export function assignmentIntent({
  projectUid,
  documentUid,
  assigneeUserUid,
  note,
}: NewAssignment): string {
  return JSON.stringify([projectUid, documentUid, assigneeUserUid, note.trim()]);
}

export function useCreateAssignment() {
  const client = useQueryClient();
  const flightRef = useRef<{
    readonly intent: string;
    readonly promise: Promise<Assignment>;
  } | null>(null);

  const send = async ({ projectUid, documentUid, assigneeUserUid, note }: NewAssignment) =>
    (
      await createAssignment({
        body: {
          project_uid: projectUid,
          assignee_user_uid: assigneeUserUid,
          ...(documentUid === null ? {} : { document_uid: documentUid }),
          ...(note.trim() === '' ? {} : { note: note.trim() }),
        },
      })
    ).data;

  return useMutation<Assignment, unknown, NewAssignment>({
    mutationFn: (command) => {
      const intent = assignmentIntent(command);
      const held = flightRef.current;
      if (held !== null && held.intent === intent) return held.promise;
      const promise: Promise<Assignment> = send(command).finally(() => {
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
