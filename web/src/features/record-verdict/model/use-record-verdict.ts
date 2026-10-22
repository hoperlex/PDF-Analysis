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
 * on every retry. `intentRef` holds the key for the intent currently in flight, and
 * `resolveIntentKey` reuses it when the user presses the same button again after a failure
 * and mints a new one when they press a different one. Retrying with a fresh key would
 * append a second event to a ledger that has no delete.
 *
 * The request itself is built by `buildVerdictRequest`: an accept of a finding that carries
 * a proposed severity is sent with the severity the expert chose, and is REFUSED, not sent,
 * when they have not chosen one. The refusal is state, not a ref, so the screen re-renders
 * with it. It is filed under the finding it was raised for, so it cannot follow the reviewer
 * to the next finding.
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
  Severity,
} from '@/shared/api';
import { appendDecision, newIdempotencyKey } from '@/shared/api';

import type { VerdictIntent, VerdictRefusal } from './verdict-request';
import { buildVerdictRequest } from './verdict-request';

export type { VerdictIntent } from './verdict-request';

/**
 * The severity facts of the observation being judged. `proposed` is the model's proposal as
 * the API served it; `decided` is what the expert chose. Both are absent on a legacy finding.
 */
export interface VerdictSeverity {
  readonly proposed?: Severity | undefined;
  readonly decided?: Severity | undefined;
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
  readonly isPending: boolean;
  readonly error: unknown;
  /** Set when the browser refused to send, rather than when the server refused. */
  readonly refusal: VerdictRefusal | null;
  readonly result: AppendDecisionResponse | null;
  readonly reset: () => void;
}

export function useRecordVerdict({ findingUid, runId }: RecordVerdictArgs): RecordVerdictApi {
  const queryClient = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);
  const [refused, setRefused] = useState<{
    readonly findingUid: FindingUid;
    readonly refusal: VerdictRefusal;
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
      // The intent completed. The next press is a new command and mints a new key.
      intentRef.current = null;
      for (const queryKey of decisionCacheKeys(findingUid, runId)) {
        void queryClient.invalidateQueries({ queryKey });
      }
    },
  });

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
      mutation.mutate(checked.request);
    },
    isPending: mutation.isPending,
    error: mutation.error,
    refusal: refused !== null && refused.findingUid === findingUid ? refused.refusal : null,
    result: mutation.data ?? null,
    reset: () => {
      // Only the mutation result is cleared. `intentRef` deliberately survives: the user
      // dismissing an error has not changed what they asked for, and the retry after it
      // must carry the same key.
      setRefused(null);
      mutation.reset();
    },
  };
}
