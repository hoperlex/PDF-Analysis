'use client';

/**
 * «Подтвердить все предложения» (`UIP-S16-03`, `Г3-B`): the expert's one confirmation over a shown list becomes one command per pair.
 *
 * A suggestion decides nothing (`AGENTS` §4): a pair exists only when the expert confirms it. The button over the table asks that
 * confirmation once, for the list the expert saw, and then each pair is confirmed by its own `confirmStagePair` with its own
 * idempotency key, one after another. There is no command for «all» and none is invented: a pair that the server refuses is
 * reported by name and the others stand; a pair that failed keeps its key until it is confirmed, so a retry of an uncertain
 * request is the same command and not a second decision (`web/docs/PC01_UI_SEAM.md` §4.3).
 */

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRef, useState } from 'react';

import type { DocumentUid, ProjectUid, StagePairSuggestion } from '@/shared/api';
import { confirmStagePair, newIdempotencyKey } from '@/shared/api';
import type { IntentRecord } from '@/shared/lib';
import { resolveIntentKey } from '@/shared/lib';

import { STAGE_PAIR_KEYS } from './catalog';

/** The keys held for pairs not confirmed yet, one per pair: the rule of `resolveIntentKey`, kept for a set of intents. */
export class HeldPairKeys {
  private readonly held = new Map<string, IntentRecord>();
  constructor(private readonly mint: () => string) {}

  /** The key of this pair's confirmation: the held one while it has not been confirmed, a fresh one otherwise. */
  keyFor(signature: string): string {
    const record = resolveIntentKey(this.held.get(signature) ?? null, signature, this.mint);
    this.held.set(signature, record);
    return record.idempotencyKey;
  }

  /** The pair is confirmed: its next confirmation, if there ever is one, is a new command. */
  release(signature: string): void {
    this.held.delete(signature);
  }

  holds(signature: string): boolean {
    return this.held.has(signature);
  }
}

export interface ConfirmedPairRequest {
  readonly leftDocumentUid: DocumentUid;
  readonly rightDocumentUid: DocumentUid;
  readonly idempotencyKey: string;
}

export interface ConfirmAllFailure {
  readonly suggestion: StagePairSuggestion;
  readonly error: unknown;
}

/** «Подтверждено N из M»: what the list asked for, what the server accepted, and which pair it refused and why. */
export interface ConfirmAllResult {
  readonly total: number;
  readonly confirmed: number;
  readonly failures: readonly ConfirmAllFailure[];
}

export function pairSignature(projectUid: ProjectUid, suggestion: Pick<StagePairSuggestion, 'left_document_uid' | 'right_document_uid'>): string {
  return `${projectUid}|${suggestion.left_document_uid}|${suggestion.right_document_uid}`;
}

/**
 * One command per suggestion, in the order shown, each with its own key. A refusal does not stop the others and is not hidden:
 * it is in `failures` with the error as it came.
 */
export async function confirmSuggestions(input: {
  readonly projectUid: ProjectUid;
  readonly suggestions: readonly StagePairSuggestion[];
  readonly send: (request: ConfirmedPairRequest) => Promise<unknown>;
  readonly keys: HeldPairKeys;
  readonly onProgress?: ((done: number) => void) | undefined;
}): Promise<ConfirmAllResult> {
  const failures: ConfirmAllFailure[] = [];
  let confirmed = 0;
  for (const [index, suggestion] of input.suggestions.entries()) {
    const signature = pairSignature(input.projectUid, suggestion);
    try {
      await input.send({
        leftDocumentUid: suggestion.left_document_uid,
        rightDocumentUid: suggestion.right_document_uid,
        idempotencyKey: input.keys.keyFor(signature),
      });
      input.keys.release(signature);
      confirmed += 1;
    } catch (error) {
      failures.push({ suggestion, error });
    }
    input.onProgress?.(index + 1);
  }
  return { total: input.suggestions.length, confirmed, failures };
}

interface ConfirmAllIntent {
  readonly projectUid: ProjectUid;
  readonly suggestions: readonly StagePairSuggestion[];
}

export interface ConfirmAll {
  /** Runs the list; it settles with the result and never rejects: a refusal is a failure of the result. */
  readonly run: (projectUid: ProjectUid, suggestions: readonly StagePairSuggestion[]) => Promise<ConfirmAllResult>;
  readonly pending: boolean;
  /** How many of the list the running command has passed. */
  readonly done: number;
  /** The result of the last run; `undefined` while nothing ran or a run is under way. */
  readonly result: ConfirmAllResult | undefined;
}

export function useConfirmStagePairs(): ConfirmAll {
  const cache = useQueryClient();
  const keys = useRef<HeldPairKeys | null>(null);
  keys.current ??= new HeldPairKeys(newIdempotencyKey);
  const [done, setDone] = useState(0);
  const mutation = useMutation<ConfirmAllResult, unknown, ConfirmAllIntent>({
    mutationFn: async ({ projectUid, suggestions }) => {
      setDone(0);
      return confirmSuggestions({
        projectUid, suggestions, keys: keys.current!, onProgress: setDone,
        send: async (request) => (await confirmStagePair({
          path: { project_uid: projectUid },
          body: { left_document_uid: request.leftDocumentUid, right_document_uid: request.rightDocumentUid },
          idempotencyKey: request.idempotencyKey,
        })).data,
      });
    },
    retry: false,
    // The table and the suggestions are read again once, when the whole list has been passed.
    onSettled: (_result, _error, intent) => {
      void cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectPairs(intent.projectUid) });
      void cache.invalidateQueries({ queryKey: STAGE_PAIR_KEYS.projectSuggestions(intent.projectUid) });
    },
  });
  return {
    run: (projectUid, suggestions) => mutation.mutateAsync({ projectUid, suggestions }),
    pending: mutation.isPending,
    done,
    result: mutation.data,
  };
}
