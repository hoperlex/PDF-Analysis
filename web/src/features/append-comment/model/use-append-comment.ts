'use client';

/**
 * Append a comment to a finding's ledger.
 *
 * A separate feature from `record-verdict` and not a mode of it, because it is a different
 * intent with a different consequence: a comment carries `verdict: null`, so it moves
 * `latest_comment` and `decision_recorded_at` and leaves `current_verdict` exactly where
 * the last accept or reject put it (`P02_SEAMS.md` §5.4). The screen this session exists
 * to produce requires appending a comment after a verdict **without overwriting history**,
 * and the way this UI guarantees that is by having no code path that could: there is one
 * write operation, it appends, and this feature never sends an `event_type` that carries a
 * verdict.
 *
 * Same idempotency rule as the verdict feature, and it matters more here: the comment text
 * is part of the intent signature, so retrying the same comment reuses its key while
 * editing the text and sending again is a second, genuinely different comment.
 *
 * The hook is bound to one finding but lives at page level, so it outlives a change of
 * selection, and what it reports about the LAST press is kept with the finding the press was
 * raised for (`WEB-HOOKS-PER-FINDING-01`): the mutation's variables are the finding and the
 * request together, `error`, `isPending` and `result` are reported only to that finding, and
 * the idempotency key is held per finding, so a comment on another finding neither takes this
 * finding's key nor empties it. The hook reports the LAST press only: a press on another
 * finding replaces the report about this one (its request still completes and still refreshes
 * its caches).
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import type { IntentRecord } from '@/entities/expert-decision';
import { decisionCacheKeys, intentSignature, resolveIntentKey } from '@/entities/expert-decision';
import type {
  AppendDecisionRequest,
  AppendDecisionResponse,
  FindingObservationId,
  FindingUid,
  RunId,
} from '@/shared/api';
import { appendDecision, newIdempotencyKey } from '@/shared/api';

import type { CommentRefusal } from './comment-text';
import { checkComment } from './comment-text';

/** One press: the finding it was raised for, and what was asked of the ledger. */
interface CommentPress {
  readonly findingUid: FindingUid;
  readonly request: AppendDecisionRequest;
}

export interface AppendCommentArgs {
  readonly findingUid: FindingUid;
  readonly runId: RunId;
}

export interface AppendCommentApi {
  readonly append: (raw: string, observationId: FindingObservationId) => void;
  /** A comment for the bound finding is in flight; another finding's request is not reported. */
  readonly isPending: boolean;
  /** The failure of the last press, only while the bound finding is the one it was raised for. */
  readonly error: unknown;
  /** Set when the browser refused to send, rather than when the server refused. */
  readonly refusal: CommentRefusal | null;
  /** The server's answer to the last press, only while the finding it answers is the bound one. */
  readonly result: AppendDecisionResponse | null;
  readonly reset: () => void;
}

export function useAppendComment({ findingUid, runId }: AppendCommentArgs): AppendCommentApi {
  const queryClient = useQueryClient();
  const intentsRef = useRef(new Map<FindingUid, IntentRecord>());
  // STATE, not a ref: an empty comment sends nothing, so nothing else in this hook would
  // render the page, and a write to a ref schedules no render -- the refusal sentence would
  // wait for some unrelated render to appear. Filed under the finding it was raised for, as
  // `useRecordVerdict` does, because the hook outlives a change of selected finding.
  const [refused, setRefused] = useState<{
    readonly findingUid: FindingUid;
    readonly refusal: CommentRefusal;
  } | null>(null);

  const mutation = useMutation<AppendDecisionResponse, Error, CommentPress>({
    mutationFn: async ({ findingUid: pressedOn, request }) => {
      const intent = resolveIntentKey(
        intentsRef.current.get(pressedOn) ?? null,
        request,
        newIdempotencyKey,
      );
      intentsRef.current.set(pressedOn, intent);
      const response = await appendDecision({
        path: { finding_uid: pressedOn },
        body: request,
        idempotencyKey: intent.idempotencyKey,
      });
      return response.data;
    },
    // The finding comes from the press, not from the render that happens to be current: while
    // a request is out the observer rewrites the callbacks with the latest render's, and by
    // then the hook can be bound to another finding.
    onSuccess: (_data, { findingUid: pressedOn, request }) => {
      // Only the intent that completed is forgotten: a different comment of this finding,
      // sent meanwhile, keeps the key its retry needs.
      if (intentsRef.current.get(pressedOn)?.signature === intentSignature(request)) {
        intentsRef.current.delete(pressedOn);
      }
      for (const queryKey of decisionCacheKeys(pressedOn, runId)) {
        void queryClient.invalidateQueries({ queryKey });
      }
    },
  });

  const press = mutation.variables;
  const lastPressWasHere = press !== undefined && press.findingUid === findingUid;

  return {
    append: (raw, observationId) => {
      const checked = checkComment(raw);
      if (checked.kind === 'refused') {
        setRefused({ findingUid, refusal: checked.refusal });
        return;
      }
      setRefused(null);
      mutation.mutate({
        findingUid,
        request: {
          event_type: 'comment',
          finding_observation_id: observationId,
          comment: checked.comment,
        },
      });
    },
    isPending: lastPressWasHere && mutation.isPending,
    error: lastPressWasHere ? mutation.error : null,
    refusal: refused !== null && refused.findingUid === findingUid ? refused.refusal : null,
    result:
      mutation.data !== undefined && mutation.data.event.finding_uid === findingUid
        ? mutation.data
        : null,
    reset: () => {
      // Only this finding's mutation state is dismissed; what is held for another finding is
      // not on this screen.
      setRefused(null);
      if (lastPressWasHere) mutation.reset();
    },
  };
}
