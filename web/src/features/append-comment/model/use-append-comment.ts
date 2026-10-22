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
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import type { IntentRecord } from '@/entities/expert-decision';
import { decisionCacheKeys, resolveIntentKey } from '@/entities/expert-decision';
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

export interface AppendCommentArgs {
  readonly findingUid: FindingUid;
  readonly runId: RunId;
}

export interface AppendCommentApi {
  readonly append: (raw: string, observationId: FindingObservationId) => void;
  readonly isPending: boolean;
  readonly error: unknown;
  /** Set when the browser refused to send, rather than when the server refused. */
  readonly refusal: CommentRefusal | null;
  readonly result: AppendDecisionResponse | null;
  readonly reset: () => void;
}

export function useAppendComment({ findingUid, runId }: AppendCommentArgs): AppendCommentApi {
  const queryClient = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);
  // STATE, not a ref: an empty comment sends nothing, so nothing else in this hook would
  // render the page, and a write to a ref schedules no render -- the refusal sentence would
  // wait for some unrelated render to appear. Filed under the finding it was raised for, as
  // `useRecordVerdict` does, because the hook outlives a change of selected finding.
  const [refused, setRefused] = useState<{
    readonly findingUid: FindingUid;
    readonly refusal: CommentRefusal;
  } | null>(null);

  const mutation = useMutation({
    mutationFn: async (request: AppendDecisionRequest) => {
      const intent = resolveIntentKey(intentRef.current, request, newIdempotencyKey);
      intentRef.current = intent;
      const response = await appendDecision({
        path: { finding_uid: findingUid },
        body: request,
        idempotencyKey: intent.idempotencyKey,
      });
      return response.data;
    },
    onSuccess: () => {
      intentRef.current = null;
      for (const queryKey of decisionCacheKeys(findingUid, runId)) {
        void queryClient.invalidateQueries({ queryKey });
      }
    },
  });

  return {
    append: (raw, observationId) => {
      const checked = checkComment(raw);
      if (checked.kind === 'refused') {
        setRefused({ findingUid, refusal: checked.refusal });
        return;
      }
      setRefused(null);
      mutation.mutate({
        event_type: 'comment',
        finding_observation_id: observationId,
        comment: checked.comment,
      });
    },
    isPending: mutation.isPending,
    error: mutation.error,
    refusal: refused !== null && refused.findingUid === findingUid ? refused.refusal : null,
    result: mutation.data ?? null,
    reset: () => {
      setRefused(null);
      mutation.reset();
    },
  };
}
