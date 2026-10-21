'use client';

/**
 * `carryOverDecision` (`W59-DECISION-CARRYOVER-01`): an expert confirms carrying one decision
 * from a finding of the older version to the finding of the newer version that the comparison
 * proposes as «Без изменений».
 *
 * **One key per intent, reused on every retry.** The same pair and the same source decision
 * pressed again after a failure carries the same `Idempotency-Key`; a different pair mints a
 * new one. The server also answers an exact repeat under another key with the event already
 * carried (`replayed`), so a second confirmation never appends a second event.
 *
 * **What a success changes, and so what is told.** The comparison (every page and mode of
 * every pair: its `carryover_candidates` moved), the target finding's ledger and detail, the
 * newer run's finding list, the knowledge base and the dashboard. A refusal changes nothing on
 * the server; the comparison is still read again, because each refusal means the screen was
 * showing something that is no longer true.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import type {
  CarryOverDecisionResponse,
  CarryoverCandidate,
  DocumentUid,
  ProjectUid,
  RunId,
  VersionComparison,
  VersionUid,
} from '@/shared/api';
import { carryOverDecision, newIdempotencyKey, queryKeys } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';
import { decisionCacheKeys } from '@/entities/expert-decision';

export interface CarryOverDecisionCommand {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly sourceVersionUid: VersionUid;
  readonly targetVersionUid: VersionUid;
  readonly mode: VersionComparison['mode'];
  readonly candidate: CarryoverCandidate;
  /** The newer side's run, whose finding list shows the target finding; `null` if unknown. */
  readonly targetRunId: RunId | null;
}

/** The intent a key belongs to: the pair, the decision shown and the comparison mode. */
export function carryoverSignature(command: CarryOverDecisionCommand): string {
  return [
    command.sourceVersionUid,
    command.targetVersionUid,
    command.mode,
    command.candidate.source_finding_uid,
    command.candidate.target_finding_uid,
    command.candidate.source_decision.decision_id,
  ].join('|');
}

interface InFlight {
  readonly signature: string;
  readonly promise: Promise<CarryOverDecisionResponse>;
}

export function useCarryOverDecision() {
  const client = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);
  // `BETA-LIVE-JOURNEY-01`: the live journey pressed «Подтвердить перенос» twice before the
  // page had re-rendered and measured TWO `POST`s, the second answered `replayed: true` --
  // so the screen, which shows the latest answer, told the expert the decision "had already
  // been carried earlier" over a carry they had just made. The server was right (one event);
  // the browser was sending a second request for the same intent. A press that arrives while
  // the same intent is in flight now joins the request already sent and shows its answer.
  const flightRef = useRef<InFlight | null>(null);

  const send = async (command: CarryOverDecisionCommand): Promise<CarryOverDecisionResponse> => {
    const intent = resolveIntentKey(intentRef.current, carryoverSignature(command), newIdempotencyKey);
    intentRef.current = intent;
    const response = await carryOverDecision({
      path: {
        project_uid: command.projectUid,
        document_uid: command.documentUid,
        version_uid: command.sourceVersionUid,
      },
      body: {
        target_version_uid: command.targetVersionUid,
        mode: command.mode,
        source_finding_uid: command.candidate.source_finding_uid,
        target_finding_uid: command.candidate.target_finding_uid,
        source_decision_id: command.candidate.source_decision.decision_id,
      },
      idempotencyKey: intent.idempotencyKey,
    });
    return response.data;
  };

  return useMutation<CarryOverDecisionResponse, unknown, CarryOverDecisionCommand>({
    mutationFn: (command) => {
      const signature = carryoverSignature(command);
      const held = flightRef.current;
      if (held !== null && held.signature === signature) return held.promise;
      const promise: Promise<CarryOverDecisionResponse> = send(command).finally(() => {
        if (flightRef.current?.promise === promise) flightRef.current = null;
      });
      flightRef.current = { signature, promise };
      return promise;
    },
    retry: false,
    onSuccess: (_answer, command) => {
      // The intent completed. The next press is a new command and mints a new key.
      intentRef.current = null;
      void client.invalidateQueries({ queryKey: queryKeys.versions.comparisons() });
      const target = command.candidate.target_finding_uid;
      const keys =
        command.targetRunId === null
          ? [queryKeys.findings.decisions(target), queryKeys.findings.detail(target),
             queryKeys.findings.journal(), queryKeys.dashboard.summary()]
          : decisionCacheKeys(target, command.targetRunId);
      for (const queryKey of keys) void client.invalidateQueries({ queryKey });
    },
    onError: () => {
      void client.invalidateQueries({ queryKey: queryKeys.versions.comparisons() });
    },
  });
}
