'use client';

/**
 * The administrator's two standing changes of a memory case (`D-495`, contract 1.44.0): `withdrawDecisionMemoryCase` takes a case
 * out of hints, prompts and exports, `restoreDecisionMemoryCase` undoes that. Both are keyed commands with a closed reason, and
 * both are append-only status events on the server: nothing is edited, and an exact repeat of the key answers the first call's
 * event and writes nothing.
 *
 * The key is the caller's (`useIntentKey` over the intent's signature): one key per intent, the same on every retry.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';

import type { DecisionMemoryCaseId, DecisionMemoryStatusChange } from '@/shared/api';
import { queryKeys, restoreDecisionMemoryCase, withdrawDecisionMemoryCase } from '@/shared/api';
import type { MemoryReason } from '@/entities/decision-memory';

export type StandingKind = 'withdraw' | 'restore';

export interface StandingChange {
  readonly kind: StandingKind;
  readonly caseId: DecisionMemoryCaseId;
  readonly reason: MemoryReason;
  readonly idempotencyKey: string;
}

export function useChangeStanding() {
  const client = useQueryClient();
  return useMutation<DecisionMemoryStatusChange, unknown, StandingChange>({
    mutationFn: async ({ kind, caseId, reason, idempotencyKey }) => {
      const input = { path: { case_id: caseId }, body: { reason_code: reason }, idempotencyKey };
      const response = kind === 'withdraw' ? await withdrawDecisionMemoryCase(input) : await restoreDecisionMemoryCase(input);
      return response.data;
    },
    retry: false,
    onSuccess: (_change, { caseId }) => {
      // The list (a case changes its standing), the case (its history gains an event) and the counts all move.
      void client.invalidateQueries({ queryKey: queryKeys.findings.memoryCases() });
      void client.invalidateQueries({ queryKey: queryKeys.findings.memoryCase(caseId) });
      void client.invalidateQueries({ queryKey: queryKeys.findings.memoryStatus() });
    },
  });
}
