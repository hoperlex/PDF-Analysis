'use client';

/**
 * The sequence behind «Отменить очередь» (`UIP-S13-04`): read the jobs that can be cancelled, ask once, then send one `cancelRun` for each,
 * in order, each under a key of its own that the sweep keeps for the whole of its life.
 *
 * - **Read.** The count on the button is the overview's; the jobs to cancel are read at the press, every page of the group «Активные»
 *   (`state_group`), so the number the confirmation names is the one the sweep will send and no page of the queue is left out.
 * - **Ask.** One confirmation, with the number. Nothing is sent before it.
 * - **Send.** One command per run, one after another, never in parallel. A reader may stop the sweep: the runs not yet sent are said
 *   to be unsent, and the ones already cancelled stay cancelled (nothing is rolled back).
 * - **Say.** «Отменено N из M», and the runs that are not cancelled, each with its reason. A run whose outcome is unknown can be sent
 *   again, and is sent under the key it had.
 */

import { useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

import type { ExecutionQueueItem } from '@/shared/api';
import { newIdempotencyKey } from '@/shared/api';
import { executionFailure, queueQueryOptions } from '@/entities/execution';
import type { ExecutionFailure } from '@/entities/execution';
import { useCancelRun } from '@/features/cancel-run';

import { cancellableJobs, readActiveJobs, sweepCancel } from '../model/cancel-queue';
import type { CancelOutcome } from '../model/cancel-queue';

export type CancelQueuePhase =
  | { readonly kind: 'idle' }
  | { readonly kind: 'reading' }
  | { readonly kind: 'read_failed'; readonly failure: ExecutionFailure }
  /** The confirmation: the jobs the sweep will cancel. */
  | { readonly kind: 'ask'; readonly jobs: readonly ExecutionQueueItem[] }
  | { readonly kind: 'sending'; readonly total: number; readonly sent: number }
  | { readonly kind: 'done'; readonly outcomes: readonly CancelOutcome[] };

export interface CancelQueue {
  readonly phase: CancelQueuePhase;
  /** A read or a send is in flight: the page's other commands wait. */
  readonly busy: boolean;
  /** «Отменить очередь (N)»: read the jobs, then ask. */
  readonly begin: () => void;
  /** The confirmation's «Подтвердить»: send. */
  readonly confirm: () => void;
  /** «Отмена» of the confirmation, and «Закрыть» of the result: nothing is sent and nothing is kept. */
  readonly dismiss: () => void;
  /** Stop sending after the run in hand. */
  readonly stop: () => void;
  /** Send again the runs whose outcome is unknown, under their keys. */
  readonly retryUnknown: () => void;
}

export function useCancelQueue(): CancelQueue {
  const client = useQueryClient();
  const cancel = useCancelRun();
  const [phase, setPhase] = useState<CancelQueuePhase>({ kind: 'idle' });
  // One key per run for the life of the sweep: a repeated send of a run is the same command, not a second one.
  const keys = useRef(new Map<string, string>());
  const turn = useRef(0);
  const stopped = useRef(false);

  async function send(jobs: readonly ExecutionQueueItem[], earlier: readonly CancelOutcome[]) {
    const mine = turn.current;
    stopped.current = false;
    const outcomes = await sweepCancel(
      jobs,
      (item, key) => cancel.mutateAsync({ runId: item.run_id, idempotencyKey: key }),
      {
        keys: keys.current,
        newKey: newIdempotencyKey,
        stopped: () => stopped.current,
        onProgress: (sent, total) => setPhase({ kind: 'sending', total, sent }),
      },
    );
    if (mine === turn.current) setPhase({ kind: 'done', outcomes: [...earlier, ...outcomes] });
  }

  function begin() {
    turn.current += 1;
    const mine = turn.current;
    keys.current = new Map();
    setPhase({ kind: 'reading' });
    readActiveJobs((cursor) => {
      const options = queueQueryOptions(cursor, { stateGroup: 'active' });
      return client.fetchQuery({ queryKey: options.queryKey, queryFn: options.queryFn, staleTime: 0 });
    }).then((read) => {
      if (mine !== turn.current) return;
      const jobs = cancellableJobs(read);
      setPhase(jobs.length === 0 ? { kind: 'done', outcomes: [] } : { kind: 'ask', jobs });
    }, (error: unknown) => {
      if (mine !== turn.current) return;
      setPhase({ kind: 'read_failed', failure: executionFailure(error, false) });
    });
  }

  return {
    phase,
    busy: phase.kind === 'reading' || phase.kind === 'sending',
    begin,
    confirm: () => {
      if (phase.kind === 'ask') void send(phase.jobs, []);
    },
    dismiss: () => {
      turn.current += 1;
      stopped.current = true;
      setPhase({ kind: 'idle' });
    },
    stop: () => { stopped.current = true; },
    retryUnknown: () => {
      if (phase.kind !== 'done') return;
      const unknown = phase.outcomes.flatMap((outcome) => (outcome.kind === 'unknown' ? [outcome.item] : []));
      const settled = phase.outcomes.filter((outcome) => outcome.kind !== 'unknown');
      if (unknown.length > 0) void send(unknown, settled);
    },
  };
}
