/**
 * Three run-level rules the `W12-WEB` sweep could not redden.
 *
 * 1. **A failed run reports its interrupted reason.** `runOutcome` carries both
 *    `terminal_reason` and the `OD-10` interrupted reason on the `failed` arm. The
 *    terminal reason has a test; replacing the interrupted one with `null` reddened
 *    nothing, so a run reconciled out of `running` by a crash would have rendered as an
 *    ordinary failure with no explanation of why it stopped.
 *
 * 2. **`stageCarriesError` is the predicate the vocabulary declares.** It is exported from
 *    `@/shared/api` and read by nothing in `web/src` or `web/tests` — the shape `W10-FND`
 *    found in `SORT_KEY`. Replacing its body with `false` was indistinguishable from the
 *    rule. A declared constant with no consumer can only be defended by pinning it.
 *
 * 3. **The poll loop terminates.** Removing `cancelled` from `TERMINAL_RUN_STATES`, and
 *    making `isTerminalRunState` always false, did **not** redden the suite: they made it
 *    hang. `polling.test.ts` injects a `sleep` that resolves immediately, so a
 *    non-terminating loop never yields to a macrotask and vitest's own `testTimeout`
 *    cannot fire; and the scripted fetch's "polled more times than the script allows"
 *    throw is caught by `transport.request` and rewrapped as a **retryable**
 *    `TransportError`, which the loop then absorbs. The bound below is placed in the
 *    injected `sleep`, which the loop calls outside that `try`, so it escapes.
 *
 * Every expectation is a literal.
 */

import { describe, expect, it } from 'vitest';

import type { FetchLike, RunState, RunStatus, StageStatus } from '@/shared/api';
import { STAGE_STATUS_VALUES, pollRunStatus, stageCarriesError } from '@/shared/api';
import { runOutcome } from '@/entities/audit-run';

const RUN_ID = 'run_01M2545JSD15ETSNNV904X991J';
const BASE_URL = 'http://api.invalid/v1';

function reading(state: RunState, extra: Partial<RunStatus> = {}): RunStatus {
  return {
    run_id: RUN_ID,
    project_uid: 'prj_01M2545JSD15ETSNNV904X991J',
    version_uid: 'ver_01M2545JSD15ETSNNV904X991J',
    provider_mode: 'recorded',
    created_at: '2026-01-01T00:00:00Z',
    state,
    stages: [],
    ...extra,
  };
}

// ---------------------------------------------------------------------------------------
// 1. The interrupted reason survives classification
// ---------------------------------------------------------------------------------------

describe('a failed run carries both of the reasons it can have', () => {
  it('reports the OD-10 interrupted reason alongside the terminal reason', () => {
    const outcome = runOutcome(
      reading('failed', {
        terminal_reason: 'analysis_failed',
        interrupted_reason: 'worker lost before the run reached a terminal',
      }),
    );
    if (outcome.kind !== 'failed') throw new Error('expected a failed outcome');
    expect(outcome.terminalReason).toBe('analysis_failed');
    expect(outcome.interrupted).toBe('worker lost before the run reached a terminal');
  });

  it('reports an interrupted reason even when there is no terminal reason', () => {
    // The reconciliation case: the run was abandoned in `running`, so nothing chose a
    // catalog code for it, and the interrupted reason is the only thing to say.
    const outcome = runOutcome(
      reading('failed', { interrupted_reason: 'reconciled after a crash' }),
    );
    if (outcome.kind !== 'failed') throw new Error('expected a failed outcome');
    expect(outcome.terminalReason).toBeNull();
    expect(outcome.interrupted).toBe('reconciled after a crash');
  });

  it('reports no interrupted reason when the reading carries none', () => {
    const outcome = runOutcome(reading('failed', { terminal_reason: 'analysis_failed' }));
    if (outcome.kind !== 'failed') throw new Error('expected a failed outcome');
    expect(outcome.interrupted).toBeNull();
  });

  it('treats an empty interrupted reason as no reason, not as an empty explanation', () => {
    const outcome = runOutcome(reading('failed', { interrupted_reason: '' }));
    if (outcome.kind !== 'failed') throw new Error('expected a failed outcome');
    expect(outcome.interrupted).toBeNull();
  });
});

// ---------------------------------------------------------------------------------------
// 2. stageCarriesError
// ---------------------------------------------------------------------------------------

describe('the stage vocabulary says which statuses carry an error', () => {
  it('is false for `succeeded` and true for the other three', () => {
    // Written out rather than looped over the contract set: a predicate defended by a loop
    // over its own vocabulary is defended by nothing if the vocabulary shrinks.
    expect(stageCarriesError('succeeded')).toBe(false);
    expect(stageCarriesError('partial')).toBe(true);
    expect(stageCarriesError('failed')).toBe(true);
    expect(stageCarriesError('skipped')).toBe(true);
  });

  it('is asked about every status the contract declares, and only those', () => {
    // If the contract gains a fifth status this goes red rather than leaving it unclassified.
    expect([...STAGE_STATUS_VALUES]).toEqual(['succeeded', 'partial', 'failed', 'skipped']);
    const carrying = (STAGE_STATUS_VALUES as readonly StageStatus[]).filter(stageCarriesError);
    expect([...carrying]).toEqual(['partial', 'failed', 'skipped']);
  });
});

// ---------------------------------------------------------------------------------------
// 3. The poll loop terminates on every terminal
// ---------------------------------------------------------------------------------------

/**
 * Poll a run that reports `state` on every reading, refusing to sleep more than
 * `maxSleeps` times.
 *
 * The bound lives in `sleep` on purpose. A bound in the fetch would be swallowed:
 * `transport.request` catches anything thrown by the fetch implementation and rethrows it
 * as a retryable `TransportError`, which `pollRunStatus` absorbs and retries forever.
 */
async function pollBounded(state: RunState, maxSleeps: number): Promise<RunStatus> {
  let sleeps = 0;
  const fetch: FetchLike = () =>
    Promise.resolve(
      new Response(JSON.stringify(reading(state)), {
        status: 200,
        headers: { 'Content-Type': 'application/json', 'X-Correlation-Id': 'corr-bound' },
      }),
    );

  return pollRunStatus(
    { path: { run_id: RUN_ID } },
    {
      baseUrl: BASE_URL,
      fetch,
      sleep: async (): Promise<void> => {
        sleeps += 1;
        if (sleeps > maxSleeps) {
          throw new Error(`the loop did not stop on \`${state}\` within ${maxSleeps} readings`);
        }
      },
    },
  );
}

describe('the poll loop stops on every terminal, and says so by stopping', () => {
  for (const terminal of ['published', 'partial', 'failed', 'cancelled'] as const) {
    it(`returns after the first \`${terminal}\` reading`, async () => {
      const status = await pollBounded(terminal, 1);
      expect(status.state).toBe(terminal);
    });
  }

  it('does not stop on a non-terminal reading — the bound is a real bound', () => {
    // The proof that the four assertions above are not vacuous. `running` is not a
    // terminal, so the loop keeps asking and the bound in `sleep` is what ends it.
    return expect(pollBounded('running', 3)).rejects.toThrow(
      'the loop did not stop on `running` within 3 readings',
    );
  });
});
