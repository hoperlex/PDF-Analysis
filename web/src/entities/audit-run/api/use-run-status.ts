'use client';

/**
 * Run progress, driven by the one polling loop.
 *
 * `pollRunStatus` in `@/shared/api` is the only run-progress loop in this application.
 * This hook adapts it to a component lifetime and does not re-implement it: it does not
 * set its own interval, does not use React Query's `refetchInterval`, and does not add a
 * deadline. A second cadence would mean two answers to how often a run is asked about,
 * and the backoff schedule frozen in the seam document would stop being the schedule.
 *
 * Each reading is written into the query cache under the frozen
 * `queryKeys.runs.detail(runId)` key, which is how the review slice reads run state
 * without polling.
 *
 * The loop stops on any terminal state, on unmount, and on a non-retryable failure. A
 * retryable failure is absorbed by the loop itself and never surfaces here as an error.
 */

import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';

import type { RunId, RunStatus } from '@/shared/api';
import { TransportError, isTerminalRunState, pollRunStatus, queryKeys } from '@/shared/api';

import type { RunFailure } from '../model/run-failure';
import { classifyRunFailure } from '../model/run-failure';

export interface RunStatusPolling {
  /** The most recent reading, or `null` before the first one arrives. */
  readonly status: RunStatus | null;
  /** A non-retryable failure that stopped the loop. Explicit; never a silent stop. */
  readonly failure: RunFailure | null;
  /** True while the loop is running and no terminal reading has arrived. */
  readonly polling: boolean;
  /** Restart the loop after a failure. Reads the same run; starts nothing. */
  readonly retry: () => void;
}

export function useRunStatus(runId: RunId): RunStatusPolling {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<RunStatus | null>(
    () => queryClient.getQueryData<RunStatus>(queryKeys.runs.detail(runId)) ?? null,
  );
  const [failure, setFailure] = useState<RunFailure | null>(null);
  const [polling, setPolling] = useState(true);
  const [attempt, setAttempt] = useState(0);

  const retry = useCallback(() => {
    setFailure(null);
    setPolling(true);
    setAttempt((n) => n + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let live = true;

    const seeded = queryClient.getQueryData<RunStatus>(queryKeys.runs.detail(runId)) ?? null;
    if (seeded !== null) {
      setStatus(seeded);
      if (isTerminalRunState(seeded.state)) {
        setPolling(false);
        return () => {
          live = false;
          controller.abort();
        };
      }
    }

    setPolling(true);
    pollRunStatus(
      { path: { run_id: runId } },
      {
        signal: controller.signal,
        onUpdate: (reading) => {
          if (!live) return;
          setStatus(reading);
          queryClient.setQueryData(queryKeys.runs.detail(runId), reading);
        },
      },
    )
      .then(() => {
        if (live) setPolling(false);
      })
      .catch((error: unknown) => {
        if (!live) return;
        // An abort is this component going away, not a failure to report.
        if (controller.signal.aborted && error instanceof TransportError) return;
        setFailure(classifyRunFailure(error));
        setPolling(false);
      });

    return () => {
      live = false;
      controller.abort();
    };
  }, [runId, attempt, queryClient]);

  return { status, failure, polling, retry };
}
