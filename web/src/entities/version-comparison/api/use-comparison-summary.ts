'use client';

/**
 * `generateComparisonSummary` (`COMPARE-PERSISTED-SUMMARY-01`, B2): an expert asks for the summary
 * of the approved sheet pairs, once, on purpose.
 *
 * **A command, never a side effect of looking.** Opening the comparison reads the newest stored
 * summary and calls no model; only this press does. One key per intent, reused on every retry: the
 * same comparison view pressed again after a failure carries the same `Idempotency-Key`, and the
 * server answers an exact repeat with the summary already stored (`replayed`), so a second press
 * never pays for a second answer.
 *
 * On success and on refusal the comparison is read again: each refusal means the screen was showing
 * something that is no longer true, and a rejected reply is an answer the screen must now show.
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef } from 'react';

import type {
  DocumentUid,
  GenerateComparisonSummaryResponse,
  ProjectUid,
  RunId,
  VersionComparison,
  VersionUid,
} from '@/shared/api';
import { generateComparisonSummary, newIdempotencyKey, queryKeys } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';

export interface GenerateComparisonSummaryCommand {
  readonly projectUid: ProjectUid;
  readonly documentUid: DocumentUid;
  readonly sourceVersionUid: VersionUid;
  readonly targetVersionUid: VersionUid;
  readonly mode: VersionComparison['mode'];
  readonly sourceRunId: RunId | null;
  readonly targetRunId: RunId | null;
  /** The link revision and seal the screen shows: a press for another set is another intent. */
  readonly linkRevision: number;
  readonly sealSha256: string;
}

export function summarySignature(command: GenerateComparisonSummaryCommand): string {
  return [
    'summary', command.sourceVersionUid, command.targetVersionUid, command.mode,
    command.sourceRunId ?? '', command.targetRunId ?? '', command.linkRevision, command.sealSha256,
  ].join('|');
}

interface InFlight {
  readonly signature: string;
  readonly promise: Promise<GenerateComparisonSummaryResponse>;
}

export function useGenerateComparisonSummary() {
  const client = useQueryClient();
  const intentRef = useRef<IntentRecord | null>(null);
  const flightRef = useRef<InFlight | null>(null);
  const tell = () => {
    void client.invalidateQueries({ queryKey: queryKeys.versions.comparisons() });
  };

  return useMutation<GenerateComparisonSummaryResponse, unknown, GenerateComparisonSummaryCommand>({
    mutationFn: (command) => {
      const signature = summarySignature(command);
      const held = flightRef.current;
      if (held !== null && held.signature === signature) return held.promise;
      const intent = resolveIntentKey(intentRef.current, signature, newIdempotencyKey);
      intentRef.current = intent;
      const promise: Promise<GenerateComparisonSummaryResponse> = generateComparisonSummary({
        path: {
          project_uid: command.projectUid,
          document_uid: command.documentUid,
          version_uid: command.sourceVersionUid,
        },
        body: {
          target_version_uid: command.targetVersionUid,
          mode: command.mode,
          ...(command.sourceRunId === null ? {} : { source_run_id: command.sourceRunId }),
          ...(command.targetRunId === null ? {} : { target_run_id: command.targetRunId }),
        },
        idempotencyKey: intent.idempotencyKey,
      })
        .then((response) => response.data)
        .finally(() => {
          if (flightRef.current?.promise === promise) flightRef.current = null;
        });
      flightRef.current = { signature, promise };
      return promise;
    },
    retry: false,
    onSuccess: () => {
      intentRef.current = null;
      tell();
    },
    onError: tell,
  });
}
