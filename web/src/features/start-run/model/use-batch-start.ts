'use client';

/**
 * The batch start of `R-151c`: estimate every chosen version, then start each agreed one with its own consent.
 *
 * Sequential on purpose: one request at a time keeps the stand's admission order the reader's order and makes a
 * refusal of one run land beside that run, not as a burst. A run's idempotency key is minted once per intent (its
 * signature carries the consent) and reused if the reader presses «Запустить» again after a failure, so a retry
 * never starts a second run. A failed estimate excludes its document: nothing is started without an agreed figure.
 */

import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { VersionUid } from '@/shared/api';
import { estimateRunCost, failureMessage, newIdempotencyKey, queryKeys, startRun } from '@/shared/api';

import type { BatchEntry, BatchEstimate, BatchOutcome } from './batch-start';
import { batchConsent, estimateFits } from './batch-start';
import { startRunBody, startRunIntent } from './start-run-intent';

export interface BatchStartApi {
  readonly estimates: ReadonlyMap<VersionUid, BatchEstimate>;
  readonly outcomes: ReadonlyMap<VersionUid, BatchOutcome>;
  readonly estimating: boolean;
  readonly starting: boolean;
  readonly estimate: () => Promise<void>;
  readonly start: () => Promise<void>;
}

export function useBatchStart(entries: readonly BatchEntry[]): BatchStartApi {
  const queryClient = useQueryClient();
  const [estimates, setEstimates] = useState<ReadonlyMap<VersionUid, BatchEstimate>>(new Map());
  const [outcomes, setOutcomes] = useState<ReadonlyMap<VersionUid, BatchOutcome>>(new Map());
  const [estimating, setEstimating] = useState(false);
  const [starting, setStarting] = useState(false);
  const keys = useRef(new Map<string, string>());

  const put = <T,>(set: (update: (map: ReadonlyMap<VersionUid, T>) => ReadonlyMap<VersionUid, T>) => void, uid: VersionUid, value: T) =>
    set((map) => new Map(map).set(uid, value));

  async function estimate(): Promise<void> {
    setEstimating(true);
    setOutcomes(new Map());
    setEstimates(new Map(entries.map((entry) => [entry.versionUid, { kind: 'pending' } as const])));
    for (const entry of entries) {
      try {
        const body = startRunBody(startRunIntent(entry.versionUid, null).command('estimate-only'));
        const value = (await estimateRunCost({ body })).data;
        put(setEstimates, entry.versionUid, estimateFits(value, entry.versionUid)
          ? { kind: 'ready', estimate: value }
          : { kind: 'failed', text: 'Ответ оценки стоимости не соответствует этой версии.' });
      } catch (error) {
        put(setEstimates, entry.versionUid, { kind: 'failed', text: failureMessage(error).detail });
      }
    }
    setEstimating(false);
  }

  async function start(): Promise<void> {
    setStarting(true);
    for (const entry of entries) {
      const reading = estimates.get(entry.versionUid);
      if (reading?.kind !== 'ready' || outcomes.get(entry.versionUid)?.kind === 'started') continue;
      const intent = startRunIntent(entry.versionUid, null, null, false, batchConsent(reading.estimate));
      const key = keys.current.get(intent.signature) ?? newIdempotencyKey();
      keys.current.set(intent.signature, key);
      put(setOutcomes, entry.versionUid, { kind: 'sending' });
      try {
        const command = intent.command(key);
        const run = (await startRun({ body: startRunBody(command), idempotencyKey: command.idempotencyKey })).data;
        queryClient.setQueryData(queryKeys.runs.detail(run.run_id), run);
        put(setOutcomes, entry.versionUid, { kind: 'started', run });
      } catch (error) {
        put(setOutcomes, entry.versionUid, { kind: 'refused', text: failureMessage(error).detail });
      }
    }
    void queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.summary() });
    void queryClient.invalidateQueries({ queryKey: queryKeys.execution.all() });
    setStarting(false);
  }

  return { estimates, outcomes, estimating, starting, estimate, start };
}
