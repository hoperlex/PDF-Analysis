/**
 * The frozen run-progress polling contract.
 *
 * PC-01 has no WebSocket and no server-sent events — the OpenAPI document says so
 * explicitly — so run progress is a poll of `GET /runs/{run_id}`. These numbers are
 * frozen here by the toolchain owner and repeated in `web/docs/PC01_UI_SEAM.md`.
 *
 * They are **not** derived from an upstream owner decision: no P02 document declares a
 * polling interval, so this module is where the value is first fixed. A slice that wants
 * a different cadence changes it here, in one place, and the seam document with it.
 *
 * There is deliberately no wall-clock deadline. The stop condition is the run reaching a
 * terminal state; inventing a timeout would mean inventing a failure the contract does
 * not define, and `RunStatus.state` already distinguishes `failed` from still-running.
 */
export const RUN_POLLING = {
  /** Delay before the first re-poll after a non-terminal reading. */
  initialIntervalMs: 2_000,
  /** Multiplier applied after each consecutive non-terminal reading. */
  backoffFactor: 1.5,
  /** Ceiling for the backed-off interval. Reached after five non-terminal readings. */
  maxIntervalMs: 15_000,
} as const;

/**
 * The delay before poll number `attempt` (0-based: attempt 0 is immediate).
 *
 * Deterministic and pure, so a test can assert the schedule without waiting for it.
 */
export function pollDelayMs(attempt: number): number {
  if (attempt <= 0) return 0;
  const raw = RUN_POLLING.initialIntervalMs * RUN_POLLING.backoffFactor ** (attempt - 1);
  return Math.min(Math.round(raw), RUN_POLLING.maxIntervalMs);
}

/**
 * The polling policy for operational lists: the execution queue and the execution journal
 * («Очередь», «Журнал выполнения»).
 *
 * These are the screens an operator opens to see what the runner is doing now, so they refresh
 * themselves. PC-01 still has no WebSocket and no server-sent events, so the mechanism is a
 * timed re-read; what this policy fixes is the cadence and what the screen may claim about it:
 *
 *   - every `intervalMs` while the tab is visible, and not at all while it is hidden;
 *   - after a failed read the delay doubles (`backoffFactor`) up to `maxBackoffMs`, and the
 *     next success restores `intervalMs`;
 *   - data older than `staleAfterIntervals` intervals, or whose latest read failed, is shown
 *     as possibly out of date, never as current.
 *
 * It is separate from {@link RUN_POLLING}: that one ends when a run reaches a terminal state,
 * this one has no end because a list is never finished. Any other screen that wants a timed
 * refresh names its own policy here instead of a local constant.
 */
export const OPERATIONAL_LIST_POLLING = {
  /** Delay between reads while the tab is visible and the last read succeeded. */
  intervalMs: 10_000,
  /** Multiplier applied to the delay after each consecutive failed read. */
  backoffFactor: 2,
  /** Ceiling for the backed-off delay. Reached after three consecutive failures. */
  maxBackoffMs: 60_000,
  /** The stale threshold, in intervals: data older than this is no longer shown as current. */
  staleAfterIntervals: 3,
} as const;

/** How old the last successful read may get before the screen stops presenting it as current. */
export const OPERATIONAL_LIST_STALE_MS =
  OPERATIONAL_LIST_POLLING.intervalMs * OPERATIONAL_LIST_POLLING.staleAfterIntervals;

export interface OperationalListPollState {
  /**
   * Reads that failed one after another since the last success; `0` after a success.
   *
   * React Query's own `fetchFailureCount` is not this number: it restarts at `0` whenever a new
   * read begins and counts the retries inside one read, so it can neither build a backoff over
   * several reads nor tell one failed read from three. The count is kept by
   * `entities/execution` from the query's settled-read counters.
   */
  readonly failures: number;
  /** `false` while the tab is hidden. */
  readonly visible: boolean;
}

/**
 * The delay before the next read of an operational list, or `false` for "do not schedule one".
 *
 * Deterministic and pure, so a test can assert the whole schedule without waiting for it:
 * 10, 20, 40, 60, 60 … seconds as failures accumulate, 10 again after a success, and `false`
 * while the tab is hidden (the first read after the tab returns is the window-focus refetch).
 */
export function operationalListInterval(state: OperationalListPollState): number | false {
  if (!state.visible) return false;
  const failures = Number.isFinite(state.failures) ? Math.max(0, Math.trunc(state.failures)) : 0;
  const raw = OPERATIONAL_LIST_POLLING.intervalMs * OPERATIONAL_LIST_POLLING.backoffFactor ** failures;
  return Math.min(raw, OPERATIONAL_LIST_POLLING.maxBackoffMs);
}

export interface OperationalListFreshness {
  /** Epoch milliseconds of the last successful read; `0` when there has been none. */
  readonly dataUpdatedAt: number;
  /** Whether the latest read failed. */
  readonly failed: boolean;
  /** The current time, in epoch milliseconds. */
  readonly now: number;
}

/**
 * Whether an operational list may no longer be presented as current.
 *
 * It may not when the latest read failed (the data is whatever the last success left), or when
 * the last success is older than {@link OPERATIONAL_LIST_STALE_MS}. A list that has never been
 * read has no data to call stale; the loading and error states speak for it.
 */
export function isOperationalListStale({ dataUpdatedAt, failed, now }: OperationalListFreshness): boolean {
  if (dataUpdatedAt <= 0) return false;
  return failed || now - dataUpdatedAt > OPERATIONAL_LIST_STALE_MS;
}
