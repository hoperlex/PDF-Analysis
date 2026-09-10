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
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

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

/** The two verdict-bearing events PC-01 offers. `revoke` has no PC-01 client (seam §10). */
export type VerdictIntent = 'accept' | 'reject';

export interface RecordVerdictArgs {
  readonly findingUid: FindingUid;
  readonly runId: RunId;
}

export interface RecordVerdictApi {
  readonly record: (intent: VerdictIntent, observationId: FindingObservationId) => void;
  readonly isPending: boolean;
  readonly error: unknown;
  readonly result: AppendDecisionResponse | null;
  readonly reset: () => void;
}

export function useRecordVerdict({ findingUid, runId }: RecordVerdictArgs): RecordVerdictApi {
  const queryClient = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);

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
    record: (intent, observationId) => {
      mutation.mutate({ event_type: intent, finding_observation_id: observationId });
    },
    isPending: mutation.isPending,
    error: mutation.error,
    result: mutation.data ?? null,
    reset: () => {
      // Only the mutation result is cleared. `intentRef` deliberately survives: the user
      // dismissing an error has not changed what they asked for, and the retry after it
      // must carry the same key.
      mutation.reset();
    },
  };
}
