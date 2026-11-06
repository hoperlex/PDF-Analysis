'use client';

/**
 * `carryOverProposalDecisions` (`UI-B-14`, contract 1.37.0): an expert confirms carrying the decisions in force of an
 * earlier version's pass into this pass. The server matches them by content, appends each unambiguous match as an
 * ordinary decision event authored by the caller and answers how every source decision came out.
 *
 * **One key per intent, dropped when the intent completes.** The same source pass pressed again after a failure carries
 * the same `Idempotency-Key`, so a lost answer never appends twice. Once a report is stored the intent is over: pressing
 * again later is a new request with a new key, because the matching is repeated on purpose (the source may have been
 * decided further, the target is decided now) and a stored report of the earlier press would hide that.
 *
 * **A press that finds its intent in flight sends nothing** and joins the request already sent, as the decision form does.
 *
 * **What a success changes.** The pass's proposals (the carried decisions), every project's passes (their counts by
 * decision), each proposal's history and the accepted list of the sections (a carried acceptance joins it). A carryover
 * touches no finding, so nothing under `findings` or the dashboard is invalidated.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import type { OptimisationPassId, ProposalDecisionCarryoverReport } from '@/shared/api';
import { carryOverProposalDecisions, newIdempotencyKey, queryKeys } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';

export interface CarryOverProposalDecisionsCommand {
  /** The pass the decisions are carried into. */
  readonly passId: OptimisationPassId;
  /** The pass of an earlier version whose decisions in force are carried. */
  readonly sourcePassId: OptimisationPassId;
}

/** The intent a key belongs to: the two passes. */
export function carryOverSignature(command: CarryOverProposalDecisionsCommand): string {
  return JSON.stringify([command.passId, command.sourcePassId]);
}

interface InFlight {
  readonly signature: string;
  readonly promise: Promise<ProposalDecisionCarryoverReport>;
}

export function useCarryOverProposalDecisions() {
  const client = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);
  const flightRef = useRef<InFlight | null>(null);

  const send = async (command: CarryOverProposalDecisionsCommand): Promise<ProposalDecisionCarryoverReport> => {
    const intent = resolveIntentKey(intentRef.current, carryOverSignature(command), newIdempotencyKey);
    intentRef.current = intent;
    const response = await carryOverProposalDecisions({
      path: { optimisation_pass_id: command.passId },
      body: { source_optimisation_pass_id: command.sourcePassId },
      idempotencyKey: intent.idempotencyKey,
    });
    return response.data;
  };

  return useMutation<ProposalDecisionCarryoverReport, unknown, CarryOverProposalDecisionsCommand>({
    mutationFn: (command) => {
      const signature = carryOverSignature(command);
      const held = flightRef.current;
      if (held !== null && held.signature === signature) return held.promise;
      const promise: Promise<ProposalDecisionCarryoverReport> = send(command).finally(() => {
        if (flightRef.current?.promise === promise) flightRef.current = null;
      });
      flightRef.current = { signature, promise };
      return promise;
    },
    retry: false,
    onSuccess: (report, command) => {
      intentRef.current = null;
      if (report.carried === 0) return;
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.proposalsOf(command.passId) });
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.allPasses() });
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.allAccepted() });
      void client.invalidateQueries({ queryKey: queryKeys.optimisation.allProposalDecisions() });
    },
  });
}
