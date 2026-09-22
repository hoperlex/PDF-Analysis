/**
 * `D-57` — one query key, one shape, measured as two user-visible behaviours.
 *
 * `queryKeys.runs.detail(runId)` is filled by two screens and read by two screens. Until
 * this suite existed, the two halves disagreed about what the key holds — the run screen
 * wrote and read a bare `RunStatus`, the review screen's `useQuery` filed the generated
 * client's `{ data }` envelope under the same key — and neither half was a type error,
 * because `getQueryData<RunStatus>` *asserts* a shape rather than checking one and
 * `useQuery` takes its shape from its own `queryFn`.
 *
 * **These cases assert the behaviours, not the shape.** A test that only compared the
 * written value with the read value would pass over both defects the moment somebody
 * changed both sides to a third wrong thing. What a reviewer meets is asserted instead:
 *
 *   `D-57.1`  the review screen renders the run it was given, rather than its empty
 *             branch, when the run is in the cache. `useStartRun` puts it there on the
 *             202 and `useRunStatus` rewrites it on every reading, so this is the
 *             ordinary path from "start a run" to "review it", not a contrived seeding.
 *   `D-57.2`  a terminal run is not polled again. The run screen decides that by reading
 *             the cache entry the review screen left behind; when that entry was the
 *             envelope, `seeded.state` was `undefined`, `isTerminalRunState(undefined)`
 *             was `false`, and the loop restarted on a run that had finished.
 *
 * `D-57.2` fills the cache by running the review screen's own query — `runStatusQueryOptions`,
 * literally the options object that screen hands `useQuery` — against a stubbed `fetch`, so
 * whatever shape that screen files is the shape this test reads back. Seeding an envelope
 * by hand here would make this a test of a literal in this file, and changing the screen
 * would leave it green.
 *
 * Before the repair this file was identical except that those three cases built the same
 * options inline, because the screen built them inline; `/root/w37-logs/d57-before.log`
 * records that run.
 */

import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

import type { RunStatus } from '@/shared/api';
import { isTerminalRunState, queryKeys } from '@/shared/api';
import { runStatusQueryOptions } from '@/entities/audit-run';
import { ReviewPage } from '@/_pages/review';
import { RunProgress } from '@/widgets/run-progress';

import { PROJECT_UID, RUN_ID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from './harness';

const BASE_URL = 'http://api.test/v1';

function stubRouter(): AppRouterInstance {
  return {
    push: () => {},
    replace: () => {},
    refresh: () => {},
    back: () => {},
    forward: () => {},
    prefetch: () => {},
  } as unknown as AppRouterInstance;
}

let served: RunStatus;

beforeEach(() => {
  served = runStatus({ state: 'published', published_finding_count: 1 });
  process.env.NEXT_PUBLIC_API_BASE_URL = BASE_URL;
  vi.stubGlobal(
    'fetch',
    async () =>
      new Response(JSON.stringify(served), {
        status: 200,
        headers: { 'content-type': 'application/json', 'X-Correlation-Id': 'cid-d57' },
      }),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  delete process.env.NEXT_PUBLIC_API_BASE_URL;
});

describe('the review screen shows the run that is in the cache (D-57.1)', () => {
  /** Exactly what `useStartRun` writes on a 202 and `useRunStatus` writes on each reading. */
  function reviewOverSeededRun(overrides: Partial<RunStatus> = {}): string {
    const client = newClient();
    const status = runStatus({ state: 'published', published_finding_count: 1, ...overrides });
    client.setQueryData(queryKeys.runs.detail(RUN_ID), status);
    return renderWith(
      client,
      createElement(
        AppRouterContext.Provider,
        { value: stubRouter() },
        createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }),
      ),
    );
  }

  it('renders the run header rather than the loading branch', () => {
    const markup = reviewOverSeededRun();
    expect(markup).toContain(`data-run-id="${RUN_ID}"`);
    expect(markup).toContain('data-run-state="published"');
    // The empty branch this screen rendered over a run that was definitely in the cache.
    expect(markup).not.toContain('Загрузка прогона…');
  });

  it('reads the run state from the entry, so a different run reads differently', () => {
    expect(reviewOverSeededRun({ state: 'partial' })).toContain('data-run-state="partial"');
    expect(reviewOverSeededRun({ state: 'failed', published_finding_count: 0 })).toContain(
      'data-run-state="failed"',
    );
  });

  it('reports the diagnostic count the run carries, which the empty branch swallowed', () => {
    const markup = reviewOverSeededRun({ diagnostic_observation_count: 11 });
    expect(markup).toContain('data-diagnostic-observation-count="11"');
    expect(markup).toContain('шлюз привязки отклонил непривязанных элементов модели: 11');
  });

  it('still renders the loading branch when nothing is in the cache', () => {
    const markup = renderWith(
      newClient(),
      createElement(
        AppRouterContext.Provider,
        { value: stubRouter() },
        createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }),
      ),
    );
    expect(markup).toContain('Загрузка прогона…');
    expect(markup).not.toContain(`data-run-id="${RUN_ID}"`);
  });
});

describe('a terminal run is not polled again after the review screen ran (D-57.2)', () => {
  it('shows a stopped run on the run screen, not one still being polled', async () => {
    const client = newClient();
    await client.fetchQuery(runStatusQueryOptions(RUN_ID));

    const markup = renderWith(
      client,
      createElement(RunProgress, { projectUid: PROJECT_UID, runId: RUN_ID }),
    );

    expect(markup).toContain('data-run-activity="stopped"');
    expect(markup).not.toContain('data-run-activity="polling"');
    expect(markup).toContain('показание окончательное');
    expect(markup).toContain(`data-run-id="${RUN_ID}"`);
  });

  it('leaves the loop with a true stop condition, which is the value it branches on', async () => {
    const client = newClient();
    await client.fetchQuery(runStatusQueryOptions(RUN_ID));

    // `useRunStatus` reads exactly this and stops on `isTerminalRunState(seeded.state)`.
    const seeded = client.getQueryData<RunStatus>(queryKeys.runs.detail(RUN_ID));
    expect(seeded).toBeDefined();
    expect(seeded?.state).toBe('published');
    expect(isTerminalRunState(seeded?.state as RunStatus['state'])).toBe(true);
  });

  it('keeps polling an open run, so the stop is a reading and not a constant', async () => {
    served = runStatus({ state: 'running', terminal_at: null });
    const client = newClient();
    await client.fetchQuery(runStatusQueryOptions(RUN_ID));

    const markup = renderWith(
      client,
      createElement(RunProgress, { projectUid: PROJECT_UID, runId: RUN_ID }),
    );
    expect(markup).toContain('data-run-activity="polling"');
    expect(markup).not.toContain('data-run-activity="stopped"');
  });
});
