'use client';

/**
 * `decideOptimisationProposal` (`W60-OPT-PROPOSALS-01`): an expert's accept, reject or revise
 * (with a comment) on one proposal.
 *
 * **One key per intent, dropped when the intent completes.** The same verdict and comment on
 * the same proposal pressed again after a failure carries the same `Idempotency-Key`, so a
 * lost answer never appends two events; another verdict or comment is another intent. Once
 * a decision is stored the intent is over: deciding again is a new event on purpose, because
 * decisions are only appended and the latest one is current.
 *
 * **What a success changes.** The pass's proposals (the decided one's current decision),
 * every project's passes (their counts by decision) and the proposal's history. A decision
 * touches no finding, so nothing under `findings` or the dashboard is invalidated.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import type {
  OptimisationPassId,
  OptimisationProposalId,
  ProposalDecisionResult,
  ProposalVerdict,
} from '@/shared/api';
import { decideOptimisationProposal, newIdempotencyKey, queryKeys } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';

export interface DecideOptimisationProposalCommand {
  readonly passId: OptimisationPassId;
  readonly proposalId: OptimisationProposalId;
  readonly verdict: ProposalVerdict;
  /** Trimmed; `null` for none. `revise` requires one (the server also checks). */
  readonly comment: string | null;
}

/** The intent a key belongs to; length-safe, so a comment cannot collide two intents. */
export function decisionSignature(command: DecideOptimisationProposalCommand): string {
  return JSON.stringify([command.proposalId, command.verdict, command.comment]);
}

export function useDecideOptimisationProposal() {
  const client = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);
  return useMutation<ProposalDecisionResult, unknown, DecideOptimisationProposalCommand>({
    mutationFn: async (command) => {
      const intent = resolveIntentKey(intentRef.current, decisionSignature(command), newIdempotencyKey);
      intentRef.current = intent;
      const response = await decideOptimisationProposal({
        path: { optimisation_proposal_id: command.proposalId },
        body:
          command.comment === null
            ? { verdict: command.verdict }
            : { verdict: command.verdict, comment: command.comment },
        idempotencyKey: intent.idempotencyKey,
      });
      return response.data;
    },
    retry: false,
    onSuccess: (_answer, command) => {
      intentRef.current = null;
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.proposalsOf(command.passId) });
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.allPasses() });
      void client.invalidateQueries({
        queryKey: queryKeys.optimisation.proposalDecisions(command.proposalId),
      });
    },
  });
}
