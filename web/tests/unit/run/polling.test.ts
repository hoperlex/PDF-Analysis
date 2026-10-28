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

/**
 * A `sleep` that refuses to be called more than `max` times.
 *
 * The bound is not decoration. `scripted`'s "polled more times than the script allows"
 * throw is raised *inside* the fetch implementation, and `transport.request` catches
 * anything the fetch throws and rethrows it as a **retryable** `TransportError` — which
 * this loop is supposed to absorb and retry. So the script's own guard can never stop a
 * loop that has lost its stop condition.
 *
 * `W12-WEB` measured the consequence: removing `cancelled` from `TERMINAL_RUN_STATES`,
 * making `isTerminalRunState` always false, absorbing a non-retryable failure and
 * ignoring an abort each left this suite **hanging** rather than red — and because the
 * injected sleep resolves immediately, the loop never yields to a macrotask, so vitest's
 * own `testTimeout` cannot fire either. `pollRunStatus` calls `sleep` outside that
 * `try`, so a throw from here is the one thing that escapes.
 */
function boundedSleep(
  max: number,
  onDelay: (ms: number) => void = () => {},
): (ms: number) => Promise<void> {
  let calls = 0;
  return async (ms: number): Promise<void> => {
    calls += 1;
    if (calls > max) {
      throw new Error(`the poll loop asked for more than ${max} readings and did not stop`);
    }
    onDelay(ms);
  };
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
          sleep: boundedSleep(3, (ms) => delays.push(ms)),
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
        sleep: boundedSleep(8, (ms) => delays.push(ms)),
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
              contract_version: '1.10.0',
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
      { baseUrl: BASE_URL, fetch, sleep: boundedSleep(5) },
    );
    expect(result.state).toBe('published');
    expect(call).toBe(2);
  });

  it('surfaces a non-retryable failure rather than spinning on it', async () => {
    const fetch: FetchLike = () =>
      Promise.resolve(
        new Response(
          JSON.stringify({
            contract_version: '1.10.0',
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
        { baseUrl: BASE_URL, fetch, sleep: boundedSleep(5) },
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
          sleep: boundedSleep(3),
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

  // The one named exception to the rule below. It is not a run poll: it re-reads an executor
  // connection (`GET /executors/connections/{id}`) and only while a «Проверить» probe on that
  // connection is open, so the outcome shows without the administrator pressing «Обновить».
  // It is bounded three ways, and the assertion further down holds each of them to the source:
  // the interval is `PROBE_POLL_MS` (3000 ms) and nothing else; it is `false` unless
  // `hasOpenProbe(data)`, which is false once every probe is `finished` (a terminal outcome,
  // `no_worker` included - the server ends an unclaimed probe after 120 s); and the only other
  // timer-shaped token, `setInterval` / `refetchIntervalInBackground`, stays forbidden in it.
  // It never reaches the run endpoint, which the sibling assertion below still polices.
  const ALLOWED_BOUNDED_PROBE_POLL = [
    join('entities', 'executor-connection', 'api', 'use-executor-connections.ts'),
  ];
  const code = ({ text }: { text: string }) =>
    text.replace(/\/\/.*$/gm, '').replace(/^\s*\*.*$/gm, '');
  const isAllowedProbePoll = ({ path }: { path: string }) =>
    ALLOWED_BOUNDED_PROBE_POLL.some((allowed) => path.endsWith(allowed));

  // The second named exception, `CMP-VC-UI-01`. «Сравнение версий» re-reads four things while they move, as the original does
  // (`version-comparison-projects.js:296-300` the overview, 5 s while anything runs and 30 s otherwise; `version-comparison.js:785`
  // the matrix while it is built, 1.5 s; `:828` the series while it runs, 2 s; the upload while it is read, 2 s). None of them is a run
  // poll and none reaches the run endpoint, which the assertion below still polices. Each is bounded by what the assertion further down
  // holds to the source: no timer of its own, an interval that is a named constant of at least a second, and a callback with an arm
  // that returns `false`, so a read of something that is not moving schedules nothing.
  const ALLOWED_COMPARISON_POLLS = [
    join('entities', 'version-series', 'api', 'use-overview.ts'),
    join('entities', 'version-series', 'api', 'use-matrix.ts'),
    join('entities', 'version-series', 'api', 'use-series.ts'),
    join('widgets', 'comparison-upload', 'api', 'use-upload.ts'),
  ];
  const isAllowedComparisonPoll = ({ path }: { path: string }) =>
    ALLOWED_COMPARISON_POLLS.some((allowed) => path.endsWith(allowed));

  it('schedules no interval and no timer of its own', () => {
    const offenders = sources.filter(
      (file) =>
        /setInterval\s*\(|refetchInterval|refetchIntervalInBackground/.test(code(file)) &&
        !isAllowedProbePoll(file) &&
        !isAllowedComparisonPoll(file),
    );
    expect(offenders.map((o) => o.path)).toEqual([]);
  });

  it('lets the comparison reads poll only while something moves, on a named interval, with no timer of their own', () => {
    const named = sources.filter(isAllowedComparisonPoll);
    // The allowlist must not rot into a path that no longer exists or no longer polls.
    expect(named.map((f) => f.path)).toHaveLength(ALLOWED_COMPARISON_POLLS.length);
    for (const file of named) {
      const text = code(file);
      expect(text, file.path).not.toMatch(/setInterval\s*\(|setTimeout\s*\(|refetchIntervalInBackground/);
      expect(text.match(/refetchInterval/g)?.length ?? 0, file.path).toBeGreaterThan(0);
      const constants = [...text.matchAll(/export const (\w+_POLL_MS) = ([\d_]+);/g)];
      expect(constants.length, `${file.path} names no interval`).toBeGreaterThan(0);
      for (const match of constants) expect(Number((match[2] ?? '').replaceAll('_', '')), match[1]).toBeGreaterThanOrEqual(1000);
      // It can end: each use is a callback with an arm that schedules nothing (`: false`, `? false :` or `return false`).
      for (const use of text.split('refetchInterval').slice(1)) {
        // The value of the option only: up to the next option of the same query.
        const value = use.split(/\n\s*(?:retry|enabled|queryKey|queryFn|staleTime):/)[0] ?? '';
        expect(value, `${file.path}: a callback`).toMatch(/^:\s*(?:\([^)]*\)|\w+)?\s*=>/);
        expect(value, `${file.path}: an arm that schedules nothing`).toMatch(/:\s*false\b|\?\s*false\b|return false\b/);
      }
      // And it never reaches the run endpoint.
      expect(text, file.path).not.toMatch(/getRunStatus|pollRunStatus|listRuns/);
    }
  });

  it('lets the named probe poll schedule only its bounded 3 s refetch, and nothing else', () => {
    const named = sources.filter(isAllowedProbePoll);
    // The allowlist must not rot into a path that no longer exists or no longer polls.
    expect(named.map((f) => f.path)).toHaveLength(ALLOWED_BOUNDED_PROBE_POLL.length);

    for (const file of named) {
      const text = code(file);
      expect(text).not.toMatch(/setInterval\s*\(|setTimeout\s*\(|refetchIntervalInBackground/);
      expect(text).toMatch(/export const PROBE_POLL_MS = 3000;/);
      // Exactly one use of `refetchInterval`, and it is the guarded form.
      expect(text.match(/refetchInterval/g)).toHaveLength(1);
      expect(text).toMatch(
        /refetchInterval:\s*\(query[^)]*\)\s*=>\s*hasOpenProbe\(query\.state\.data\)\s*\?\s*PROBE_POLL_MS\s*:\s*false/,
      );
      // The condition that ends the poll: every probe `finished`, on the detail and on each revision.
      expect(text).toMatch(/probe\.state !== 'finished'/);
      expect(text).toMatch(/revision\.latest_probe\.state !== 'finished'/);
    }
  });

  it('reaches the run endpoint only through the shared loop', () => {
    // Comments are stripped before matching: a doc comment that names the loop is a
    // reference to it, not a second call site.
    const pollers = sources.filter((file) => /\bpollRunStatus\s*\(/.test(code(file)));
    // Exactly one module drives the loop: the audit-run entity's hook.
    expect(pollers.map((p) => p.path)).toHaveLength(1);
    expect(pollers[0]?.path).toContain(join('entities', 'audit-run'));

    // A one-shot read of the run is not a second loop. The review screen needs the run's
    // provider_mode and state once, to show whether the findings beside it came from a
    // live call or a recording, and it schedules nothing - the sibling assertion above
    // already forbids setInterval and refetchInterval across these same files.
    //
    // So a direct call site is allowed only when it is named here. Naming them keeps the
    // guard real: a new screen reaching the run endpoint is a visible decision rather
    // than silent drift, and a named site that starts scheduling still reddens above.
    //
    // The entry was `_pages/review/ui/review-page.tsx` until `W37-D57`. The call did not
    // multiply, it MOVED: that screen built its own query options and filed the transport
    // envelope under a key the run screen fills with the model (`D-57`), so the one-shot
    // now lives beside the key it fills, as `runStatusQueryOptions`, and the screen calls
    // that. This assertion reddened on the move, which is the guard working -- the list is
    // where the run endpoint is reached, and that place changed.
    const ALLOWED_ONE_SHOT = [join('entities', 'audit-run', 'api', 'run-status-query.ts')];

    const direct = sources.filter((file) => /\bgetRunStatus\s*\(/.test(code(file)));
    const unexpected = direct.filter(
      (file) => !ALLOWED_ONE_SHOT.some((allowed) => file.path.includes(allowed)),
    );
    expect(unexpected.map((d) => d.path)).toEqual([]);

    // The allowlist must not rot into a list of files that no longer exist.
    for (const allowed of ALLOWED_ONE_SHOT) {
      expect(direct.some((file) => file.path.includes(allowed))).toBe(true);
    }
  });
});
