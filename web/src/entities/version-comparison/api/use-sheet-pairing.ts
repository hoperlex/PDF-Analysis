'use client';

/**
 * `approveSheetPairing` and `withdrawSheetPairing` (`COMPARE-PERSISTED-SUMMARY-01`): an expert
 * confirms one pair of sheets the comparison proposed, or ends an approved one.
 *
 * **One key per intent, reused on every retry.** The same pair pressed again after a failure
 * carries the same `Idempotency-Key`; a different pair mints a new one. The server also answers
 * an exact repeat under another key with the approval already stored (`replayed`), so a second
 * press never stores a second row.
 *
 * **What a success changes, and so what is told.** The comparison (every page and mode of every
 * pair: its `approved_pairs` moved). A refusal changes nothing on the server; the comparison is
 * still read again, because each refusal means the screen was showing something that is no
 * longer true.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import type {
  DocumentUid,
  ProjectUid,
  RunId,
  SheetLinkId,
  SheetPairingEvent,
  VersionComparison,
  VersionUid,
} from '@/shared/api';
import { approveSheetPairing, newIdempotencyKey, queryKeys, withdrawSheetPairing } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';

interface ComparisonView {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly sourceVersionUid: VersionUid;
  readonly targetVersionUid: VersionUid;
  readonly mode: VersionComparison['mode'];
  readonly sourceRunId: RunId | null;
  readonly targetRunId: RunId | null;
}

export interface ApproveSheetPairingCommand extends ComparisonView {
  readonly sourcePageNumber: number;
  readonly targetPageNumber: number;
  readonly suggestionSha256: string;
}

export interface WithdrawSheetPairingCommand extends ComparisonView {
  readonly sheetLinkId: SheetLinkId;
}

/** The intent an approval's key belongs to: the pair, the pages, the proposal shown and the view. */
export function approveSignature(command: ApproveSheetPairingCommand): string {
  return [
    'approve', command.sourceVersionUid, command.targetVersionUid, command.mode,
    command.sourceRunId ?? '', command.targetRunId ?? '',
    command.sourcePageNumber, command.targetPageNumber, command.suggestionSha256,
  ].join('|');
}

export function withdrawSignature(command: WithdrawSheetPairingCommand): string {
  return [
    'withdraw', command.sourceVersionUid, command.mode, command.sourceRunId ?? '',
    command.targetRunId ?? '', command.sheetLinkId,
  ].join('|');
}

function optionalRuns(command: ComparisonView) {
  return {
    ...(command.sourceRunId === null ? {} : { source_run_id: command.sourceRunId }),
    ...(command.targetRunId === null ? {} : { target_run_id: command.targetRunId }),
  };
}

interface InFlight {
  readonly signature: string;
  readonly promise: Promise<SheetPairingEvent>;
}

function useOnePress<Command>(
  signatureOf: (command: Command) => string,
  send: (command: Command, idempotencyKey: string) => Promise<SheetPairingEvent>,
) {
  const client = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);
  // A press that arrives while the same intent is in flight joins the request already sent and
  // shows its answer (`BETA-LIVE-JOURNEY-01`: two presses before the page re-rendered measured
  // two POSTs for one intent).
  const flightRef = useRef<InFlight | null>(null);
  const tell = () => {
    void client.invalidateQueries({ queryKey: queryKeys.versions.comparisons() });
  };

  return useMutation<SheetPairingEvent, unknown, Command>({
    mutationFn: (command) => {
      const signature = signatureOf(command);
      const held = flightRef.current;
      if (held !== null && held.signature === signature) return held.promise;
      const intent = resolveIntentKey(intentRef.current, signature, newIdempotencyKey);
      intentRef.current = intent;
      const promise: Promise<SheetPairingEvent> = send(command, intent.idempotencyKey).finally(() => {
        if (flightRef.current?.promise === promise) flightRef.current = null;
      });
      flightRef.current = { signature, promise };
      return promise;
    },
    retry: false,
    onSuccess: () => {
      // The intent completed. The next press is a new command and mints a new key.
      intentRef.current = null;
      tell();
    },
    onError: tell,
  });
}

export function useApproveSheetPairing() {
  return useOnePress<ApproveSheetPairingCommand>(approveSignature, async (command, idempotencyKey) => {
    const response = await approveSheetPairing({
      path: {
        project_uid: command.projectUid,
        document_uid: command.documentUid,
        version_uid: command.sourceVersionUid,
      },
      body: {
        target_version_uid: command.targetVersionUid,
        mode: command.mode,
        source_page_number: command.sourcePageNumber,
        target_page_number: command.targetPageNumber,
        suggestion_sha256: command.suggestionSha256,
        ...optionalRuns(command),
      },
      idempotencyKey,
    });
    return response.data;
  });
}

export function useWithdrawSheetPairing() {
  return useOnePress<WithdrawSheetPairingCommand>(withdrawSignature, async (command, idempotencyKey) => {
    const response = await withdrawSheetPairing({
      path: {
        project_uid: command.projectUid,
        document_uid: command.documentUid,
        version_uid: command.sourceVersionUid,
        sheet_link_id: command.sheetLinkId,
      },
      body: { mode: command.mode, ...optionalRuns(command) },
      idempotencyKey,
    });
    return response.data;
  });
}
