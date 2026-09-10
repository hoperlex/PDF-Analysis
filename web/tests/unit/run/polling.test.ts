/**
 * Run progress polls through the one shared loop, and stops on every terminal state.
 *
 * The loop itself is `A5`'s. What this suite holds is the two things a Gate B session can
 * break: that this slice uses it rather than writing a second cadence, and that the stop
 * condition covers all four terminals rather than the two anyone remembers.
 *
 * The sleep is injected, so the schedule is asserted rather than waited for.
 */

import { describe, expect, it } from 'vitest';

import type { FetchLike, RunState, RunStatus } from '@/shared/api';
import { ApiError, TERMINAL_RUN_STATES, TransportError, pollRunStatus } from '@/shared/api';
import { RUN_POLLING, pollDelayMs } from '@/shared/config';
import { WEB_ROOT, readText, walkFiles } from '../../guards/lib/repo';
import { join } from 'node:path';

const BASE_URL = 'http://api.invalid/v1';

function reading(state: RunState): RunStatus {
  return {
    run_id: 'run_01M2545JSD15ETSNNV904X991J',
    project_uid: 'prj_01M2545JSD15ETSNNV904X991J',
    version_uid: 'ver_01M2545JSD15ETSNNV904X991J',
    provider_mode: 'recorded',
    created_at: '2026-01-01T00:00:00Z',
    state,
    stages: [],
  };
}

function ok(status: RunStatus): Response {
  return new Response(JSON.stringify(status), {
    status: 200,
    headers: { 'Content-Type': 'application/json', 'X-Correlation-Id': 'corr-poll' },
  });
}

/** A fetch that replays a scripted sequence of readings and records the delays asked for. */
function scripted(states: readonly RunState[]) {
  const calls: string[] = [];
  const fetch: FetchLike = (url) => {
    const next = states[calls.length];
    calls.push(url);
    if (next === undefined) throw new Error('polled more times than the script allows');
    return Promise.resolve(ok(reading(next)));
  };
  return { fetch, calls };
}

describe('the loop stops on every terminal state', () => {
  it('covers all four terminals, not just the two that come to mind', () => {
    expect(TERMINAL_RUN_STATES).toEqual(['published', 'partial', 'failed', 'cancelled']);
  });

  for (const terminal of ['published', 'partial', 'failed', 'cancelled'] as const) {
    it(`stops on \`${terminal}\` after one reading`, async () => {
      const { fetch, calls } = scripted([terminal]);
      const delays: number[] = [];
      const result = await pollRunStatus(
        { path: { run_id: 'run_01M2545JSD15ETSNNV904X991J' } },
        {
          baseUrl: BASE_URL,
          fetch,
          sleep: async (ms) => {
            delays.push(ms);
          },
        },
      );
      expect(result.state).toBe(terminal);
      expect(calls).toHaveLength(1);
      expect(delays).toEqual([0]);
    });
  }
});

describe('the loop continues while the run is open', () => {
  it('keeps reading until a terminal arrives, at the frozen schedule', async () => {
    const { fetch, calls } = scripted(['queued', 'running', 'validating', 'published']);
    const delays: number[] = [];
    const updates: RunState[] = [];

    const result = await pollRunStatus(
      { path: { run_id: 'run_01M2545JSD15ETSNNV904X991J' } },
      {
        baseUrl: BASE_URL,
        fetch,
        sleep: async (ms) => {
          delays.push(ms);
        },
        onUpdate: (status) => updates.push(status.state),
      },
    );

    expect(result.state).toBe('published');
    expect(calls).toHaveLength(4);
    expect(updates).toEqual(['queued', 'running', 'validating', 'published']);
    expect(delays).toEqual([0, 2000, 3000, 4500]);
  });
});

describe('the frozen schedule', () => {
  it('is 0, 2000, 3000, 4500, 6750, 10125 then capped at 15000', () => {
    expect([0, 1, 2, 3, 4, 5, 6, 7].map(pollDelayMs)).toEqual([
      0, 2000, 3000, 4500, 6750, 10125, 15000, 15000,
    ]);
  });

  it('has no wall-clock deadline to configure', () => {
    expect(RUN_POLLING.initialIntervalMs).toBe(2000);
    expect(RUN_POLLING.backoffFactor).toBe(1.5);
    expect(RUN_POLLING.maxIntervalMs).toBe(15000);
    expect(Object.keys(RUN_POLLING)).not.toContain('deadlineMs');
  });
});

describe('a failure is absorbed or surfaced according to the envelope', () => {
  it('absorbs a retryable failure and keeps polling', async () => {
    let call = 0;
    const fetch: FetchLike = () => {
      call += 1;
      if (call === 1) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              contract_version: '1.0.0-draft.1',
              error_code: 'dependency_unavailable',
              message: 'A caller-safe sentence.',
              correlation_id: 'corr-poll',
              retryable: true,
            }),
            {
              status: 503,
              headers: { 'Content-Type': 'application/json', 'X-Correlation-Id': 'corr-poll' },
            },
          ),
        );
      }
      return Promise.resolve(ok(reading('published')));
    };

    const result = await pollRunStatus(
      { path: { run_id: 'run_01M2545JSD15ETSNNV904X991J' } },
      { baseUrl: BASE_URL, fetch, sleep: async () => {} },
    );
    expect(result.state).toBe('published');
    expect(call).toBe(2);
  });

  it('surfaces a non-retryable failure rather than spinning on it', async () => {
    const fetch: FetchLike = () =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            contract_version: '1.0.0-draft.1',
            error_code: 'not_found',
            message: 'A caller-safe sentence.',
            correlation_id: 'corr-poll',
            retryable: false,
          }),
          {
            status: 404,
            headers: { 'Content-Type': 'application/json', 'X-Correlation-Id': 'corr-poll' },
          },
        ),
      );

    await expect(
      pollRunStatus(
        { path: { run_id: 'run_01M2545JSD15ETSNNV904X991J' } },
        { baseUrl: BASE_URL, fetch, sleep: async () => {} },
      ),
    ).rejects.toBeInstanceOf(ApiError);
  });

  it('stops on abort rather than continuing in the background', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(
      pollRunStatus(
        { path: { run_id: 'run_01M2545JSD15ETSNNV904X991J' } },
        {
          baseUrl: BASE_URL,
          fetch: () => Promise.resolve(ok(reading('running'))),
          sleep: async () => {},
          signal: controller.signal,
        },
      ),
    ).rejects.toBeInstanceOf(TransportError);
  });
});

describe('this slice adds no second polling loop', () => {
  const OWNED = ['_pages', 'widgets', 'features', 'entities'];

  const sources = OWNED.flatMap((layer) =>
    walkFiles(join(WEB_ROOT, 'src', layer), (p) => /\.(ts|tsx)$/.test(p)).map((path) => ({
      path,
      text: readText(path),
    })),
  );

  it('reads a non-trivial number of files, so a broken walk cannot pass vacuously', () => {
    expect(sources.length).toBeGreaterThan(15);
  });

  it('schedules no interval and no timer of its own', () => {
    const offenders = sources.filter(({ text }) =>
      /setInterval\s*\(|refetchInterval|refetchIntervalInBackground/.test(
        text.replace(/\/\/.*$/gm, '').replace(/^\s*\*.*$/gm, ''),
      ),
    );
    expect(offenders.map((o) => o.path)).toEqual([]);
  });

  it('reaches the run endpoint only through the shared loop', () => {
    // Comments are stripped before matching: a doc comment that names the loop is a
    // reference to it, not a second call site.
    const code = ({ text }: { text: string }) =>
      text.replace(/\/\/.*$/gm, '').replace(/^\s*\*.*$/gm, '');

    const pollers = sources.filter((file) => /\bpollRunStatus\s*\(/.test(code(file)));
    // Exactly one module drives the loop: the audit-run entity's hook.
    expect(pollers.map((p) => p.path)).toHaveLength(1);
    expect(pollers[0]?.path).toContain(join('entities', 'audit-run'));

    const direct = sources.filter((file) => /\bgetRunStatus\s*\(/.test(code(file)));
    expect(direct.map((d) => d.path)).toEqual([]);
  });
});
