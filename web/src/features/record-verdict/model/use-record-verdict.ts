'use client';

/**
 * Record an accept or a reject.
 *
 * The write is `appendDecision`, which appends an event and never updates one. So this
 * feature has no "change the verdict" path and no optimistic overwrite: it appends, the
 * server answers with its own `current_verdict`, and the three cache entries of
 * `decisionCacheKeys` are invalidated so every panel re-reads the projection rather than
 * each keeping a guess.
 *
 * The idempotency key is the delicate part. §4.3 of the seam: one key per intent, reused
 * on every retry. `intentsRef` holds, for each finding, the key of the intent last sent for
 * it, and `resolveIntentKey` reuses it when the user presses the same button again after a
 * failure and mints a new one when they press a different one. Retrying with a fresh key
 * would append a second event to a ledger that has no delete. The holder is per finding
 * because the hook outlives a change of selection and another finding can be pressed while
 * this one is still out: one slot for the whole hook would be overwritten by that press (the
 * retry here would mint a new key) and emptied by the other finding's success (the retry
 * there would).
 *
 * The request itself is built by `buildVerdictRequest`: an accept of a finding that carries
 * a proposed severity is sent with the severity the expert chose, and is REFUSED, not sent,
 * when they have not chosen one. The refusal is state, not a ref, so the screen re-renders
 * with it. It is filed under the finding it was raised for, so it cannot follow the reviewer
 * to the next finding.
 *
 * The hook is bound to one finding but lives at page level, so it outlives a change of
 * selection, and everything it reports about the LAST press is kept with the finding the press
 * was raised for (`WEB-HOOKS-PER-FINDING-01`): the mutation's variables are the press, the
 * finding and the request together, and `error`, `isPending` and `pendingIntent` are reported
 * only to that finding, `result` only to the finding whose event it carries (the server's own
 * `event.finding_uid`). A failure of A is therefore not shown on B, A's request in flight does
 * not disable B, and both are still there when the reviewer returns to A. The hook reports the
 * LAST press only: a press on B replaces the report about A (A's request still completes and
 * still refreshes A's caches).
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
  Severity,
} from '@/shared/api';
import { appendDecision, newIdempotencyKey } from '@/shared/api';

import type { VerdictIntent, VerdictRefusal } from './verdict-request';
import { buildVerdictRequest, verdictIntentOf } from './verdict-request';

export type { VerdictIntent } from './verdict-request';

/**
 * The severity facts of the observation being judged. `proposed` is the model's proposal as
 * the API served it; `decided` is what the expert chose. Both are absent on a legacy finding.
 */
export interface VerdictSeverity {
  readonly proposed?: Severity | undefined;
  readonly decided?: Severity | undefined;
}

/** One press: the finding it was raised for, and what was asked of the ledger. */
interface VerdictPress {
  readonly findingUid: FindingUid;
  readonly request: AppendDecisionRequest;
}

export interface RecordVerdictArgs {
  readonly findingUid: FindingUid;
  readonly runId: RunId;
}

export interface RecordVerdictApi {
  readonly record: (
    intent: VerdictIntent,
    observationId: FindingObservationId,
    severity?: VerdictSeverity,
  ) => void;
  /** A verdict for the bound finding is in flight; another finding's request is not reported. */
  readonly isPending: boolean;
  /** The failure of the last press, only while the bound finding is the one it was raised for. */
  readonly error: unknown;
  /**
   * Which verdict is in flight for the bound finding, read from the pending request; nothing
   * when none is.
   */
  readonly pendingIntent: VerdictIntent | null;
  /** Set when the browser refused to send, rather than when the server refused. */
  readonly refusal: VerdictRefusal | null;
  /**
   * Forget the browser's refusal and nothing else: the mutation, its error and its key are
   * untouched. The refusal answers the previous press, and goes when the expert makes the
   * choice it asked for.
   */
  readonly clearRefusal: () => void;
  /** The server's answer to the last press, only while the finding it answers is the bound one. */
  readonly result: AppendDecisionResponse | null;
  readonly reset: () => void;
}

export function useRecordVerdict({ findingUid, runId }: RecordVerdictArgs): RecordVerdictApi {
  const queryClient = useQueryClient();
  const intentsRef = useRef(new Map<FindingUid, IntentRecord>());
  const [refused, setRefused] = useState<{
    readonly findingUid: FindingUid;
    readonly refusal: VerdictRefusal;
  } | null>(null);

  const mutation = useMutation<AppendDecisionResponse, Error, VerdictPress>({
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
      // The intent completed. The next press is a new command and mints a new key -- unless
      // the slot already holds a different intent of this finding, pressed meanwhile, whose
      // retry must keep its own key.
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
    record: (intent, observationId, severity) => {
      const checked = buildVerdictRequest({
        intent,
        observationId,
        proposedSeverity: severity?.proposed,
        decidedSeverity: severity?.decided,
      });
      if (checked.kind === 'refused') {
        setRefused({ findingUid, refusal: checked.refusal });
        return;
      }
      setRefused(null);
      mutation.mutate({ findingUid, request: checked.request });
    },
    isPending: lastPressWasHere && mutation.isPending,
    pendingIntent:
      lastPressWasHere && mutation.isPending ? verdictIntentOf(press.request) : null,
    error: lastPressWasHere ? mutation.error : null,
    refusal: refused !== null && refused.findingUid === findingUid ? refused.refusal : null,
    clearRefusal: () => {
      setRefused(null);
    },
    result:
      mutation.data !== undefined && mutation.data.event.finding_uid === findingUid
        ? mutation.data
        : null,
    reset: () => {
      // Only the mutation result is cleared, and only when it is this finding's: what is
      // held for another finding is not on this screen to be dismissed. `intentsRef`
      // deliberately survives: the user dismissing an error has not changed what they asked
      // for, and the retry after it must carry the same key.
      setRefused(null);
      if (lastPressWasHere) mutation.reset();
    },
  };
}
