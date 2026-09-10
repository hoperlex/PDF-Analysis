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
