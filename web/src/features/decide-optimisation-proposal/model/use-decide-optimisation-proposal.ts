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
 * **A press that finds its intent in flight sends nothing** (`WEB-FOLLOWUPS-01`). The live
 * journey (`BETA-LIVE-JOURNEY-01`) pressed «Принять» twice before the page had re-rendered --
 * which is what disables the buttons -- and measured two identical `POST`s under one key (both
 * `201`, one decision id). The server was right; the browser sent the intent twice, and on a
 * slower answer the second would have met the first still executing
 * (`409 idempotency_key_in_progress`) and shown a refusal over a stored decision. The press
 * joins the request already sent and gets its answer. It is the same guard `carry-over-decision`
 * and `upload-price-list` carry, and it covers all three verdicts because the intent is the
 * proposal, the verdict and the comment together.
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

interface InFlight {
  readonly signature: string;
  readonly promise: Promise<ProposalDecisionResult>;
}

export function useDecideOptimisationProposal() {
  const client = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);
  const flightRef = useRef<InFlight | null>(null);

  const send = async (command: DecideOptimisationProposalCommand): Promise<ProposalDecisionResult> => {
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
  };

  return useMutation<ProposalDecisionResult, unknown, DecideOptimisationProposalCommand>({
    mutationFn: (command) => {
      const signature = decisionSignature(command);
      const held = flightRef.current;
      if (held !== null && held.signature === signature) return held.promise;
      const promise: Promise<ProposalDecisionResult> = send(command).finally(() => {
        if (flightRef.current?.promise === promise) flightRef.current = null;
      });
      flightRef.current = { signature, promise };
      return promise;
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
