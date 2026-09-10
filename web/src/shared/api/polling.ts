/**
 * The single run-progress polling loop.
 *
 * PC-01 has no WebSocket and no server-sent events, so progress is a poll of
 * `GET /runs/{run_id}`. There is one implementation of that loop, here, honoring the
 * frozen interval and backoff of `shared/config/polling`. A slice that polls the run
 * endpoint by hand has made a second cadence nobody documented.
 *
 * The loop stops on any terminal state, on abort, and on a non-retryable failure. It has
 * no wall-clock deadline: the stop condition is the run's own terminal, and inventing a
 * timeout would invent a failure the contract does not define.
 */

import { pollDelayMs } from '../config';
import { getRunStatus } from './generated/client.gen';
import type { GetRunStatusInput } from './generated/operations.gen';
import type { RunStatus } from './generated/types.gen';
import { ApiFailure, TransportError } from './errors';
import { isTerminalRunState } from './run-state';
import type { RequestOptions } from './transport';

export interface PollRunOptions extends RequestOptions {
  /** Called with every reading, including the terminal one. */
  readonly onUpdate?: (status: RunStatus) => void;
  /** Sleep implementation. Injected by tests so the schedule can be asserted, not waited on. */
  readonly sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
}

function defaultSleep(ms: number, signal?: AbortSignal): Promise<void> {
  if (ms <= 0) return Promise.resolve();
  return new Promise<void>((resolve, reject) => {
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      reject(new TransportError('Run polling was aborted.'));
    };
    if (signal?.aborted === true) {
      onAbort();
      return;
    }
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

/**
 * Poll until the run reaches a terminal state, then return that reading.
 *
 * A retryable failure — the envelope says so, or the request never reached the API —
 * is absorbed and the loop continues at the next interval. A non-retryable failure is
 * rethrown: a `not_found` run will not become found by asking again.
 */
export async function pollRunStatus(
  input: GetRunStatusInput,
  options: PollRunOptions = {},
): Promise<RunStatus> {
  const sleep = options.sleep ?? defaultSleep;
  const signal = options.signal;

  const requestOptions: RequestOptions = {
    ...(options.signal !== undefined ? { signal: options.signal } : {}),
    ...(options.baseUrl !== undefined ? { baseUrl: options.baseUrl } : {}),
    ...(options.fetch !== undefined ? { fetch: options.fetch } : {}),
  };

  for (let attempt = 0; ; attempt += 1) {
    await sleep(pollDelayMs(attempt), signal);

    if (signal?.aborted === true) {
      throw new TransportError('Run polling was aborted.');
    }

    let status: RunStatus;
    try {
      status = (await getRunStatus(input, requestOptions)).data;
    } catch (failure) {
      if (failure instanceof ApiFailure && failure.retryable) continue;
      throw failure;
    }

    options.onUpdate?.(status);

    if (isTerminalRunState(status.state)) return status;
  }
}
