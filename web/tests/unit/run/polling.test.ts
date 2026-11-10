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
import {
  AGENT_INSTALL_POLL_MS, AGENT_STATUS_POLL_MS, AI_POLL_MS, AI_QUEUE_POLL_MS, MATRIX_BUILD_POLL_MS,
  OVERVIEW_BUSY_POLL_MS, OVERVIEW_IDLE_POLL_MS, PROBE_POLL_MS, RUN_POLLING, SERIES_POLL_MS,
  SPECIFICATION_POLL_MS, STAGE_REVIEW_POLL_MS, STAGE_TEXT_POLL_MS, UPLOAD_POLL_MS, pollDelayMs,
} from '@/shared/config';
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
              contract_version: '1.47.0',
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
            contract_version: '1.47.0',
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
  // `D-333`: `_app` is read too. The side menu's counters poll from there (`_app/use-menu-badges.ts`), and a walk that stopped at `entities`
  // left them outside the census while the prose above said four reads poll.
  const OWNED = ['_app', '_pages', 'widgets', 'features', 'entities'];

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
  // the interval is `PROBE_POLL_MS` (3000 ms, defined in `shared/config/polling.ts`) and nothing else; it is `false` unless
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
  // that returns `false`, so a read of something that is not moving schedules nothing. Since `D-307` the intervals are not defined here:
  // every `*_POLL_MS` lives in `shared/config/polling.ts` and the file imports it (the sibling assertions below hold both halves).
  const ALLOWED_COMPARISON_POLLS = [
    join('entities', 'version-series', 'api', 'use-overview.ts'),
    join('entities', 'version-series', 'api', 'use-matrix.ts'),
    join('entities', 'version-series', 'api', 'use-series.ts'),
    join('entities', 'version-series', 'api', 'use-ai.ts'),
    join('widgets', 'comparison-upload', 'api', 'use-upload.ts'),
    // `EXEC2-WEB-WIZARD-01`: the agent lifecycle and the path-A session, bounded `_POLL_MS` callbacks.
    join('features', 'connect-remote-agent', 'model', 'use-agent-polls.ts'),
    join('widgets', 'stage-text-evidence', 'ui', 'stage-text-evidence.tsx'),
    join('widgets', 'stage-changes', 'ui', 'stage-raw-differences.tsx'),
    join('widgets', 'stage-changes', 'ui', 'stage-changes.tsx'),
    join('widgets', 'stage-changes', 'ui', 'stage-high-level-changes.tsx'),
    join('widgets', 'stage-changes', 'ui', 'stage-journal.tsx'),
    join('widgets', 'stage-run-controls', 'ui', 'stage-batch-controls.tsx'),
    join('widgets', 'stage-run-controls', 'ui', 'stage-run-controls.tsx'),
    // `CMP-SPEC` (`2510d5e3`): the whole-specification list of a series, re-read only while one of its
    // transitions is `running` or `paused` -- the source was `open ? 3000 : false`, a poll with no end
    // while the panel was open, and now names `SPECIFICATION_POLL_MS` (from config) and ends when nothing moves.
    join('widgets', 'version-series', 'ui', 'specification-panel.tsx'),
  ];
  const isAllowedComparisonPoll = ({ path }: { path: string }) =>
    ALLOWED_COMPARISON_POLLS.some((allowed) => path.endsWith(allowed));

  // The pair-run summary hook of the stage pairs catalog (`UI-B-85`; lane D6 moved it out of `stage-run-controls.tsx`, lane F1 gave
  // it its own rule). Lane D6 had listed it above with the review-cadence polls, which let a row of the catalog poll its pair at
  // 1.5 s: with a hundred pairs, a hundred rows. It is not a review poll. The one pair the expert has open is polled at the review
  // cadence by `StageRunControls`; a row of the catalog reads its pair only while it is in view, polls only while a run of the pair
  // moves, and at the operational cadence (`OPERATIONAL_LIST_POLLING`, ten seconds). The source is held to that below: by the shape
  // of the hook, and by every place that calls it per row.
  const PAIR_ROW_POLL_HOOK = join('widgets', 'stage-run-controls', 'api', 'use-pair-run.ts');
  const isPairRowPollHook = ({ path }: { path: string }) => path.endsWith(PAIR_ROW_POLL_HOOK);

  // `D-307`: every interval lives in `shared/config/polling.ts`. The values as the config exports them, so the table below is
  // also a check that the barrel exports what the file declares.
  const CONFIG_INTERVALS: Readonly<Record<string, number>> = {
    AGENT_INSTALL_POLL_MS, AGENT_STATUS_POLL_MS, AI_POLL_MS, AI_QUEUE_POLL_MS, MATRIX_BUILD_POLL_MS,
    OVERVIEW_BUSY_POLL_MS, OVERVIEW_IDLE_POLL_MS, PROBE_POLL_MS, SERIES_POLL_MS, SPECIFICATION_POLL_MS,
    STAGE_REVIEW_POLL_MS, STAGE_TEXT_POLL_MS, UPLOAD_POLL_MS,
  };

  /**
   * The value of every `refetchInterval` option in a file, exactly: from the colon to the comma or the closing bracket at the
   * option's own depth, so an inline callback, a block callback and a bare function name each come out whole. (Cutting at "the
   * next option" read to the end of the file for the last use of a query, and the arm it looked for could be anyone's.)
   * `refetchIntervalInBackground` is a different option and is not matched.
   */
  function refetchIntervalValues(text: string): string[] {
    const values: string[] = [];
    const option = /\brefetchInterval\b(?!InBackground)\s*:/g;
    for (let found = option.exec(text); found !== null; found = option.exec(text)) {
      let depth = 0;
      let quote: string | null = null;
      let at = option.lastIndex;
      for (; at < text.length; at += 1) {
        const char = text.charAt(at);
        if (quote !== null) {
          if (char === '\\') at += 1;
          else if (char === quote) quote = null;
        } else if (char === "'" || char === '"' || char === '`') quote = char;
        else if (char === '(' || char === '[' || char === '{') depth += 1;
        else if (char === ')' || char === ']' || char === '}') {
          if (depth === 0) break;
          depth -= 1;
        } else if (char === ',' && depth === 0) break;
      }
      values.push(text.slice(option.lastIndex, at).trim());
    }
    return values;
  }

  /** A number of three or more digits written into an option's value: an interval that has no name. */
  const carriesNumberOfItsOwn = (value: string) => /\b\d[\d_]{2,}\b/.test(value);
  /** A `*_POLL_MS` given a value of its own in this file. */
  const definesInterval = (text: string) => /\b\w*POLL\w*_MS\s*(?::\s*\w+\s*)?=(?![=>])/.test(text);
  /** The names a file imports from `@/shared/config`. */
  const importedFromConfig = (text: string): string[] =>
    [...text.matchAll(/import\s*\{([^}]*)\}\s*from\s*'@\/shared\/config';/g)].flatMap((match) =>
      (match[1] ?? '').split(',').map((name) => name.trim()).filter((name) => name !== ''));
  const intervalNames = (value: string): string[] => [...value.matchAll(/\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_POLL_MS)\b/g)].map((match) => match[1] ?? '');

  // The third named exception, `EMERGENCY-ANALYSIS` (`af8c69f7`, `widgets/extended-review`). The section-analysis
  // panel re-reads `getExtendedRunReview` while the base run moves and for a bounded number of reads after it ends.
  // It is not a run poll either (the run endpoint is policed below). Its callback is not inline: the whole decision
  // is `extendedReviewPollInterval`, a pure function the unit tests drive (`analysis-extended/workflow.test.ts`), so
  // the assertion below holds the SOURCE to the shape instead: the option calls that function and nothing else, the
  // function has an arm that schedules nothing and is bounded by `MAX_TERMINAL_REVIEW_READS`, and the file has no
  // timer of its own. It is a viewer-lane path; this file only names it.
  const ALLOWED_EXTENDED_REVIEW_POLL = [join('widgets', 'extended-review', 'ui', 'extended-review.tsx')];
  const isAllowedExtendedReviewPoll = ({ path }: { path: string }) =>
    ALLOWED_EXTENDED_REVIEW_POLL.some((allowed) => path.endsWith(allowed));

  // The fourth named exception, the operational-list policy (`OPERATIONAL_LIST_POLLING`, `web/docs/PC01_UI_SEAM.md` §7.1). The
  // execution queue, the execution journal, the «Исполнители» worker list and the pause state refresh themselves. The option is written
  // once, in `operational-poll.ts`, and applied by spread to those four queries only; the assertion further down holds the source to that
  // shape. The side menu's counters (`_app/use-menu-badges.ts`: the queue, the knowledge base, the pending registrations) are the same
  // policy's second home and are named below (`D-333`).
  const ALLOWED_OPERATIONAL_LIST_POLL = [join('entities', 'execution', 'api', 'operational-poll.ts')];
  const isAllowedOperationalListPoll = ({ path }: { path: string }) =>
    ALLOWED_OPERATIONAL_LIST_POLL.some((allowed) => path.endsWith(allowed));

  // The operational-list policy's second home, `D-333`: the side menu's three counters (`_app/use-menu-badges.ts`). They follow the policy
  // by SPREAD (`...OPERATIONAL_LIST_POLL`), which carries the one `refetchInterval` from `operational-poll.ts` into a query, so the token
  // the sibling assertions search for never appears in the file. A guard that reads only the token therefore cannot see them; this one
  // reads the spread. Where the spread may be written is a closed list, and a new consumer is a visible decision, not drift.
  const ALLOWED_OPERATIONAL_SPREAD = [
    join('entities', 'execution', 'api', 'operational-poll.ts'), // defines it
    join('entities', 'execution', 'api', 'use-execution.ts'), // the queue, the journal, the worker list and the pause state (asserted below)
    join('entities', 'execution', 'index.ts'), // re-exports it
    join('_app', 'use-menu-badges.ts'), // the side menu's counters (asserted below)
    // `HOSTS-WEB-01` (plan 2026-11-09 §6: the web polls the servers every 10 s while the screen is open): the list of servers.
    join('entities', 'executor-host', 'api', 'use-executor-hosts.ts'),
  ];
  const MENU_COUNTERS = join('_app', 'use-menu-badges.ts');
  /** The files that name the policy's spread (`OPERATIONAL_LIST_POLL`, not the config's `OPERATIONAL_LIST_POLLING`) outside the closed list. */
  const operationalSpreadOutsideTheList = (files: readonly { path: string; text: string }[]): string[] =>
    files
      .filter((file) => /\bOPERATIONAL_LIST_POLL\b/.test(code(file)) && !ALLOWED_OPERATIONAL_SPREAD.some((allowed) => file.path.endsWith(allowed)))
      .map((file) => file.path);
  const spreadsIn = (text: string): number => (text.match(/\.\.\.OPERATIONAL_LIST_POLL\b/g) ?? []).length;

  it('schedules no interval and no timer of its own', () => {
    const offenders = sources.filter(
      (file) =>
        /setInterval\s*\(|refetchInterval|refetchIntervalInBackground/.test(code(file)) &&
        !isAllowedProbePoll(file) &&
        !isAllowedComparisonPoll(file) &&
        !isPairRowPollHook(file) &&
        !isAllowedExtendedReviewPoll(file) &&
        !isAllowedOperationalListPoll(file),
    );
    expect(offenders.map((o) => o.path)).toEqual([]);
  });

  it('lets the comparison reads poll only while something moves, on a named interval from the config, with no timer of their own', () => {
    const named = sources.filter(isAllowedComparisonPoll);
    // The allowlist must not rot into a path that no longer exists or no longer polls.
    expect(named.map((f) => f.path)).toHaveLength(ALLOWED_COMPARISON_POLLS.length);
    for (const file of named) {
      const text = code(file);
      expect(text, file.path).not.toMatch(/setInterval\s*\(|setTimeout\s*\(|refetchIntervalInBackground/);
      const uses = refetchIntervalValues(text);
      expect(uses.length, `${file.path} polls through no refetchInterval`).toBeGreaterThan(0);
      // The interval is not defined here: it is a name `shared/config` exports, imported by this file, of at least a second.
      expect(definesInterval(text), `${file.path} defines an interval of its own`).toBe(false);
      const imported = importedFromConfig(text);
      for (const use of uses) {
        const names = intervalNames(use);
        expect(names.length, `${file.path}: a named interval in \`${use}\``).toBeGreaterThan(0);
        for (const name of names) {
          expect(imported, `${file.path} imports ${name} from @/shared/config`).toContain(name);
          expect(CONFIG_INTERVALS[name], `${name} is declared in shared/config/polling.ts`).toBeGreaterThanOrEqual(1000);
        }
        // It can end: each use is a callback with an arm that schedules nothing (`: false`, `? false :` or `return false`).
        expect(use, `${file.path}: a callback`).toMatch(/^(?:\([^)]*\)|\w+)?\s*=>/);
        expect(use, `${file.path}: an arm that schedules nothing`).toMatch(/:\s*false\b|\?\s*false\b|return false\b/);
      }
      // And it never reaches the run endpoint.
      expect(text, file.path).not.toMatch(/getRunStatus|pollRunStatus|listRuns/);
    }
  });

  /**
   * What is wrong with the source of the pair-row hook, as sentences (empty: nothing). The run-list read must poll through one
   * `refetchInterval` that ends (`: false`) when no run moves and otherwise waits `OPERATIONAL_LIST_POLLING.intervalMs`; the hook must
   * not name the review cadence or a number of its own; and its caller must say which rows are in view (`enabled: read`, a required
   * `inView` parameter), so a row cannot read or poll unseen.
   */
  function pairRowPollProblems(text: string): string[] {
    const problems: string[] = [];
    const uses = refetchIntervalValues(text);
    if (uses.length !== 1) problems.push(`${uses.length} refetchInterval options, expected the one of the run list`);
    for (const use of uses) {
      if (!/runActive/.test(use)) problems.push(`polls whatever the run list holds: ${use}`);
      if (!/OPERATIONAL_LIST_POLLING\.intervalMs/.test(use)) problems.push(`not the operational cadence: ${use}`);
      if (!/:\s*false\b/.test(use)) problems.push(`never stops: ${use}`);
      if (carriesNumberOfItsOwn(use)) problems.push(`a number of its own: ${use}`);
    }
    if (/STAGE_REVIEW_POLL_MS|\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_POLL_MS\b/.test(text)) problems.push('names a *_POLL_MS cadence (the review cadence is the open pair\'s)');
    if (/setInterval\s*\(|setTimeout\s*\(|refetchIntervalInBackground/.test(text)) problems.push('a timer of its own');
    if (!/enabled:\s*read\b/.test(text)) problems.push('the run-list read is not gated by `read`');
    if (!/export function useLatestPairRun\(\s*pairId: string,\s*inView: boolean\s*\)/.test(text)) problems.push('useLatestPairRun does not require `inView`');
    return problems;
  }

  /** The calls of `useLatestPairRun` that do not say which rows are in view: no second argument, or a literal `true` (every row, as before). */
  function ungatedPairRowReads(files: readonly { path: string; text: string }[]): string[] {
    return files.filter((file) => !isPairRowPollHook(file)).flatMap((file) =>
      [...code(file).matchAll(/\buseLatestPairRun\(([^)]*)\)/g)]
        .map((call) => (call[1] ?? '').split(',').map((argument) => argument.trim()))
        .filter((args) => args.length < 2 || args[1] === '' || args[1] === 'true')
        .map((args) => `${file.path}: useLatestPairRun(${args.join(', ')})`));
  }

  /** The row components of the catalog that are rendered without `inView={rowsInView.has(…)}`: a row that reads whatever its neighbours do. */
  function rowsWithoutGate(text: string): string[] {
    return [...text.matchAll(/<(PairRunCell|OpenButton|ManageButton)\s[\s\S]*?\/>/g)]
      .filter((element) => !/inView=\{rowsInView\.has\(/.test(element[0]))
      .map((element) => element[1] ?? '');
  }

  it('lets a row of the pairs catalog poll only while a run of its pair moves, at the operational cadence, and only when in view', () => {
    const hook = sources.filter(isPairRowPollHook);
    // The allowlist must not rot into a path that no longer exists.
    expect(hook.map((file) => file.path)).toHaveLength(1);
    expect(pairRowPollProblems(code(hook[0]!))).toEqual([]);
  });

  it('calls useLatestPairRun with the rows in view at every place, the catalog included', () => {
    expect(ungatedPairRowReads(sources)).toEqual([]);
    const catalog = sources.filter(({ path }) => path.endsWith(join('widgets', 'stage-pair-catalog', 'ui', 'stage-pair-catalog.tsx')));
    expect(catalog).toHaveLength(1);
    const text = code(catalog[0]!);
    // It calls the hook (through its row components), so the check above is not a walk of nothing, and it gates every row component.
    expect(text.match(/\buseLatestPairRun\(/g)?.length ?? 0).toBeGreaterThanOrEqual(3);
    expect(rowsWithoutGate(text)).toEqual([]);
    expect(text.match(/<(?:PairRunCell|OpenButton|ManageButton)\s/g)?.length ?? 0).toBeGreaterThanOrEqual(7);
  });

  // The two guards above are not vacuous: each can fail, on the shapes lane D6 shipped and the ways a later change could return to them.
  it('shows that the pair-row guards fail on a row polled at the review cadence, a row called per row, and a row left ungated', () => {
    const gated = 'export function useLatestPairRun(pairId: string, inView: boolean) {}\n'
      + 'const a = queryOptions({ enabled: read, refetchInterval: (query) => (query.state.data?.some(runActive) ? OPERATIONAL_LIST_POLLING.intervalMs : false) });';
    expect(pairRowPollProblems(gated)).toEqual([]);
    // The hook as lane D6 shipped it: the review cadence for every row, whatever the row's place on the screen.
    const shipped = "import { STAGE_REVIEW_POLL_MS } from '@/shared/config';\n"
      + 'export function useLatestPairRun(pairId: string) {\n'
      + '  useQuery({ refetchInterval: (query) => (query.state.data?.some(runActive) ? STAGE_REVIEW_POLL_MS : false) });\n}';
    const problems = pairRowPollProblems(shipped);
    expect(problems.some((problem) => problem.startsWith('not the operational cadence'))).toBe(true);
    expect(problems.some((problem) => problem.startsWith('names a *_POLL_MS cadence'))).toBe(true);
    expect(problems).toContain('the run-list read is not gated by `read`');
    expect(problems).toContain('useLatestPairRun does not require `inView`');
    // A poll that never stops, one that polls anything, and one with a number of its own.
    expect(pairRowPollProblems(gated.replace(': false)', ': 5000)')).some((problem) => problem.startsWith('never stops'))).toBe(true);
    expect(pairRowPollProblems(gated.replace('(query.state.data?.some(runActive)', '(true')).some((problem) => problem.startsWith('polls whatever'))).toBe(true);
    expect(pairRowPollProblems(gated.replace('OPERATIONAL_LIST_POLLING.intervalMs', '10_000')).some((problem) => problem.startsWith('a number of its own'))).toBe(true);
    // Called per row: with no second argument, with a literal `true`, or with the rows in view.
    const file = (text: string) => [{ path: join('widgets', 'stage-pair-catalog', 'ui', 'cell.tsx'), text }];
    expect(ungatedPairRowReads(file('const { run } = useLatestPairRun(pairId);'))).toHaveLength(1);
    expect(ungatedPairRowReads(file('const { run } = useLatestPairRun(pairId, true);'))).toHaveLength(1);
    expect(ungatedPairRowReads(file('const { run } = useLatestPairRun(pair.pair_id , inView);'))).toEqual([]);
    expect(ungatedPairRowReads(file('// useLatestPairRun(pairId)\nconst x = 1;'))).toEqual([]);
    // A row component rendered without the gate.
    expect(rowsWithoutGate('<PairRunCell pairId={pair.pair_id} cell="method" />')).toEqual(['PairRunCell']);
    expect(rowsWithoutGate('<ManageButton pairId={id} open={a} onToggle={() => go(id)} />')).toEqual(['ManageButton']);
    expect(rowsWithoutGate('<OpenButton pairId={pair.pair_id} inView={rowsInView.has(pair.pair_id)} onRunChange={x} />')).toEqual([]);
  });

  // `D-307`: one source for every polling interval. Three halves, each with a case that shows it can fail (below).
  it('declares every interval in shared/config/polling.ts, once, and exports each of them', () => {
    const declared = [...readText(join(WEB_ROOT, 'src', 'shared', 'config', 'polling.ts')).matchAll(/^export const (\w+_POLL_MS) = /gm)].map(
      (match) => match[1] ?? '',
    );
    expect(declared.length).toBeGreaterThan(10);
    expect(new Set(declared).size, 'an interval declared twice').toBe(declared.length);
    // The barrel exports exactly the declared ones (the table above is built from the barrel).
    expect([...declared].sort()).toEqual(Object.keys(CONFIG_INTERVALS).sort());
  });

  it('defines no interval anywhere else in src, and no refetchInterval carries a number of its own', () => {
    const everywhere = walkFiles(join(WEB_ROOT, 'src'), (p) => /\.(ts|tsx)$/.test(p))
      .filter((path) => !path.endsWith(join('shared', 'config', 'polling.ts')))
      .map((path) => ({ path, text: readText(path) }));
    expect(everywhere.length).toBeGreaterThan(sources.length);
    expect(everywhere.filter((file) => definesInterval(code(file))).map((file) => file.path)).toEqual([]);
    const literal = sources.flatMap((file) =>
      refetchIntervalValues(code(file)).filter(carriesNumberOfItsOwn).map((value) => `${file.path}: ${value}`));
    expect(literal).toEqual([]);
    // A name used in a refetchInterval is one the file imports from the config, never one it defines.
    const unimported = sources.flatMap((file) => {
      const imported = importedFromConfig(code(file));
      return refetchIntervalValues(code(file)).flatMap(intervalNames).filter((name) => !imported.includes(name)).map((name) => `${file.path}: ${name}`);
    });
    expect(unimported).toEqual([]);
  });

  it('can tell a local interval, a bare number and a missing import from the real thing', () => {
    expect(definesInterval('export const STAGE_REVIEW_POLL_MS = 1500;')).toBe(true);
    expect(definesInterval('const POLL_MS: number = 1500;')).toBe(true);
    expect(definesInterval("import { STAGE_REVIEW_POLL_MS } from '@/shared/config';\nrefetchInterval: () => STAGE_REVIEW_POLL_MS")).toBe(false);
    const bare = refetchIntervalValues('useQuery({ refetchInterval: () => (open ? 3000 : false), retry: false })');
    expect(bare).toEqual(['() => (open ? 3000 : false)']);
    expect(bare.some(carriesNumberOfItsOwn)).toBe(true);
    expect(refetchIntervalValues('x({ refetchInterval: (q) => (q.state.data ? 3_000 : false) })').some(carriesNumberOfItsOwn)).toBe(true);
    expect(refetchIntervalValues('x({ refetchInterval: () => (open ? SPECIFICATION_POLL_MS : false) })').some(carriesNumberOfItsOwn)).toBe(false);
    // The last use of a query is cut at its own closing bracket, not at the end of the file; the background option is another option.
    expect(refetchIntervalValues("x({ refetchInterval: (q) => (a ? [1, 2].includes(q) : false) });\nconst y = 'false';\n")).toEqual([
      '(q) => (a ? [1, 2].includes(q) : false)',
    ]);
    expect(refetchIntervalValues('x({ refetchIntervalInBackground: false })')).toEqual([]);
    expect(importedFromConfig("import { A_POLL_MS, B_POLL_MS } from '@/shared/config';")).toEqual(['A_POLL_MS', 'B_POLL_MS']);
    expect(importedFromConfig("import { A_POLL_MS } from './local';")).toEqual([]);
    expect(intervalNames('x ? STAGE_REVIEW_POLL_MS : OVERVIEW_IDLE_POLL_MS')).toEqual(['STAGE_REVIEW_POLL_MS', 'OVERVIEW_IDLE_POLL_MS']);
  });

  it('keeps every interval at the value it had when it was moved into the config', () => {
    expect(CONFIG_INTERVALS).toEqual({
      AGENT_INSTALL_POLL_MS: 3000,
      AGENT_STATUS_POLL_MS: 5000,
      AI_POLL_MS: 3000,
      AI_QUEUE_POLL_MS: 5000,
      MATRIX_BUILD_POLL_MS: 1500,
      OVERVIEW_BUSY_POLL_MS: 5000,
      OVERVIEW_IDLE_POLL_MS: 30000,
      PROBE_POLL_MS: 3000,
      SERIES_POLL_MS: 2000,
      SPECIFICATION_POLL_MS: 3000,
      STAGE_REVIEW_POLL_MS: 1500,
      STAGE_TEXT_POLL_MS: 1500,
      UPLOAD_POLL_MS: 2000,
    });
  });

  it('lets the section-analysis panel poll only through its bounded interval function, with no timer of its own', () => {
    const named = sources.filter(isAllowedExtendedReviewPoll);
    expect(named.map((f) => f.path)).toHaveLength(ALLOWED_EXTENDED_REVIEW_POLL.length);

    for (const file of named) {
      const text = code(file);
      expect(text, file.path).not.toMatch(/setInterval\s*\(|setTimeout\s*\(|refetchIntervalInBackground/);
      // Exactly one use of the option, and it is the function.
      expect(text.match(/refetchInterval/g), file.path).toHaveLength(1);
      expect(text, file.path).toMatch(
        /refetchInterval:\s*\(reading\)\s*=>\s*extendedReviewPollInterval\(active, terminalReads, reading\.state\.data\)/,
      );
      // The function: one arm that schedules nothing, and a bound on the reads after the run has ended.
      const body = text.match(/export function extendedReviewPollInterval[\s\S]*?\n\}/)?.[0] ?? '';
      expect(body, `${file.path}: the interval function`).toMatch(/\?\s*\d+\s*:\s*false\b/);
      expect(body, `${file.path}: the bound`).toContain('terminalReads < MAX_TERMINAL_REVIEW_READS');
      expect(text, file.path).toMatch(/export const MAX_TERMINAL_REVIEW_READS = \d+;/);
      // And it never reaches the run endpoint.
      expect(text, file.path).not.toMatch(/getRunStatus|pollRunStatus|listRuns/);
    }
  });

  it('lets the operational lists poll only through the policy function, only while visible, and only the queue, the journal, the worker list and the pause state (the menu’s counters are the next case)', () => {
    const named = sources.filter(isAllowedOperationalListPoll);
    expect(named.map((f) => f.path)).toHaveLength(ALLOWED_OPERATIONAL_LIST_POLL.length);
    for (const file of named) {
      const text = code(file);
      // No timer of its own: React Query owns the schedule and this module only answers "how long?".
      expect(text, file.path).not.toMatch(/setInterval\s*\(|setTimeout\s*\(/);
      // Exactly one use of the option, and it is the policy function; never in the background.
      expect(text.match(/refetchInterval\b/g), file.path).toHaveLength(1);
      expect(text, file.path).toMatch(/refetchInterval:\s*operationalListRefetchInterval,/);
      expect(text, file.path).toMatch(/refetchIntervalInBackground:\s*false,/);
      expect(text, file.path).toMatch(/operationalListInterval\(\{ failures: consecutiveFailures\(query\), visible: tabIsVisible\(\) \}\)/);
      // And it never reaches the run endpoint.
      expect(text, file.path).not.toMatch(/getRunStatus|pollRunStatus|listRuns/);
    }
    // The spread is in the queue, the journal, the worker list and the pause-state read (`R-151f`: the top strip
    // shows the pause state on every screen), and in nothing else of the entity.
    const hooks = sources.find((file) => file.path.endsWith(join('entities', 'execution', 'api', 'use-execution.ts')));
    expect(hooks).toBeDefined();
    const body = code(hooks!);
    expect(body.match(/\.\.\.OPERATIONAL_LIST_POLL\b/g)).toHaveLength(4);
    expect(body.match(/refetchInterval/g) ?? []).toHaveLength(0);
    const section = (name: string) => body.split(`export function ${name}`)[1]?.split('\nexport ')[0] ?? '';
    expect(section('queueQueryOptions')).toContain('...OPERATIONAL_LIST_POLL');
    expect(section('journalQueryOptions')).toContain('...OPERATIONAL_LIST_POLL');
    expect(section('workersQueryOptions')).toContain('...OPERATIONAL_LIST_POLL');
    expect(section('dispatchQueryOptions')).toContain('...OPERATIONAL_LIST_POLL');
    // The hooks over those options add nothing of their own, and the reads of other things in the entity are not polled.
    for (const hook of ['useExecutionQueue', 'useExecutionJournal', 'useWorkers', 'useWorkerLookup', 'useExecutionDispatch']) {
      expect(section(hook), hook).not.toMatch(/OPERATIONAL_LIST_POLL|refetchInterval/);
    }
  });

  it('lets the list of servers poll by the policy’s spread, once, with no timer and no interval of its own', () => {
    const named = sources.filter((file) => file.path.endsWith(join('entities', 'executor-host', 'api', 'use-executor-hosts.ts')));
    expect(named, 'the walk reads the servers\' hooks').toHaveLength(1);
    const text = code(named[0]!);
    expect(spreadsIn(text)).toBe(1);
    expect(text).not.toMatch(/setInterval\s*\(|setTimeout\s*\(|refetchInterval|refetchIntervalInBackground/);
    expect(text).not.toMatch(/getRunStatus|pollRunStatus|listRuns/);
    // The details of one server are read once and again on request, never on a timer.
    expect(text.split('export function executorHostDetailsQueryOptions')[1] ?? '').not.toContain('OPERATIONAL_LIST_POLL');
  });

  it('applies the operational-list spread only in the closed list of files', () => {
    expect(operationalSpreadOutsideTheList(sources)).toEqual([]);
    // The list must not rot into paths that no longer exist or no longer name the policy.
    for (const allowed of ALLOWED_OPERATIONAL_SPREAD) {
      const file = sources.find((candidate) => candidate.path.endsWith(allowed));
      expect(file, `${allowed} is read by the walk`).toBeDefined();
      expect(/\bOPERATIONAL_LIST_POLL\b/.test(code(file!)), `${allowed} names the policy`).toBe(true);
    }
  });

  it('can fail: a spread anywhere else is found, and a comment or the config’s name is not one', () => {
    const probe = (path: string, text: string) => ({ path: join('widgets', 'probe', path), text });
    expect(operationalSpreadOutsideTheList([probe('ui/poller.tsx', 'useQuery({ queryKey, ...OPERATIONAL_LIST_POLL })')])).toEqual([
      join('widgets', 'probe', 'ui/poller.tsx'),
    ]);
    expect(operationalSpreadOutsideTheList([probe('ui/import.ts', "import { OPERATIONAL_LIST_POLL } from '@/entities/execution';")])).toHaveLength(1);
    expect(operationalSpreadOutsideTheList([probe('ui/note.ts', '// follows OPERATIONAL_LIST_POLL\nconst x = 1;')])).toEqual([]);
    expect(operationalSpreadOutsideTheList([probe('ui/display.ts', "import { OPERATIONAL_LIST_POLLING } from '@/shared/config';")])).toEqual([]);
    expect(operationalSpreadOutsideTheList([{ path: join('_app', 'use-menu-badges.ts'), text: '...OPERATIONAL_LIST_POLL' }])).toEqual([]);
    expect(spreadsIn('{ ...OPERATIONAL_LIST_POLL, a: 1 }, { ...OPERATIONAL_LIST_POLL }')).toBe(2);
    expect(spreadsIn('{ ...OPERATIONAL_LIST_POLLING }')).toBe(0);
  });

  it('lets the side menu’s counters poll only by the policy’s spread, gated by the session’s menu, with no timer of their own', () => {
    const named = sources.filter((file) => file.path.endsWith(MENU_COUNTERS));
    expect(named, 'the walk reads _app/use-menu-badges.ts').toHaveLength(1);
    const text = code(named[0]!);
    // No schedule of its own: React Query owns it and the policy function answers "how long?".
    expect(text).not.toMatch(/setInterval\s*\(|setTimeout\s*\(|refetchInterval|refetchIntervalInBackground/);
    // Three places spell the spread: the knowledge base's total, the pending registrations and `queueCountOptions`, the one
    // helper the queue counter (the overview and the live failures, `D-395`) is built by; each also re-reads on the tab's return.
    expect(spreadsIn(text)).toBe(3);
    expect(text.match(/refetchOnWindowFocus:\s*'always'/g) ?? []).toHaveLength(3);
    // The queue counter reads one row (`D-350`), through that helper, and is not the queue screen's own page of 25.
    expect(text).toMatch(/useQuery<ExecutionQueuePage>\(queueCountOptions\(sources\.has\('queue'\)\)\)/);
    expect(text).toMatch(/QUEUE_PROBE\s*=\s*\{\s*limit:\s*1\s*\}/);
    expect(text).not.toMatch(/queueQueryOptions/);
    // Every counter is read only for a session whose menu holds the item it feeds.
    expect(text.match(/enabled:\s*sources\.has\('(?:knowledge-base|registrations)'\)/g) ?? []).toHaveLength(2);
    expect(text.match(/sources\.has\('queue'\)/g) ?? []).toHaveLength(1);
    // The reads are list operations and none of them is the run endpoint.
    expect(text).toMatch(/listExecutionQueue/);
    expect(text).toMatch(/listKnowledgeBaseEntries/);
    expect(text).toMatch(/listRegistrations/);
    expect(text).not.toMatch(/getRunStatus|pollRunStatus|listRuns/);
  });

  it('can fail: the menu counters’ shape is read from the source, so a counter that polls on its own is found', () => {
    const own = "useQuery({ queryKey, queryFn, refetchInterval: 5000, enabled: sources.has('registrations') })";
    expect(/refetchInterval/.test(own)).toBe(true);
    const ungated = "useQuery({ queryKey, queryFn, ...OPERATIONAL_LIST_POLL })";
    expect(ungated.match(/enabled:\s*sources\.has\('(?:queue|knowledge-base|registrations)'\)/g) ?? []).toHaveLength(0);
    // A queue counter built without the helper is not the shape this guard names.
    expect(/useQuery<ExecutionQueuePage>\(queueCountOptions\(sources\.has\('queue'\)\)\)/.test('useQuery<ExecutionQueuePage>({ ...queueQueryOptions(), enabled: true })')).toBe(false);
    expect(spreadsIn(ungated)).toBe(1);
  });

  it('lets the named probe poll schedule only its bounded 3 s refetch, and nothing else', () => {
    const named = sources.filter(isAllowedProbePoll);
    // The allowlist must not rot into a path that no longer exists or no longer polls.
    expect(named.map((f) => f.path)).toHaveLength(ALLOWED_BOUNDED_PROBE_POLL.length);

    for (const file of named) {
      const text = code(file);
      expect(text).not.toMatch(/setInterval\s*\(|setTimeout\s*\(|refetchIntervalInBackground/);
      // The interval is the config's, imported; the file defines no interval of its own.
      expect(importedFromConfig(text)).toContain('PROBE_POLL_MS');
      expect(definesInterval(text)).toBe(false);
      expect(CONFIG_INTERVALS.PROBE_POLL_MS).toBe(3000);
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
    // Re-audit also reads the selected terminal source once, before requesting its
    // fresh cost estimate; it uses a separate confirmation key and no poll schedule.
    const ALLOWED_ONE_SHOT = [
      join('entities', 'audit-run', 'api', 'run-status-query.ts'),
      join('features', 'reaudit-run', 'model', 'use-reaudit-cost-approval.ts'),
      // `UI-A-60` (`R-151i`): a start from a stage reads the ended source run once, as the re-audit above does, before it asks
      // what the stages it computes cost. A one-shot read, no schedule.
      join('features', 'start-run-from-stage', 'model', 'use-start-from-stage-cost-approval.ts'),
      // `8eb1f31f` (compare saved run results): reads each of the two runs once before its findings and once after,
      // and refuses the comparison when the run changed between the two reads. Two one-shot reads, no schedule.
      join('widgets', 'stage-comparison', 'api', 'read-saved-results.ts'),
    ];

    const direct = sources.filter((file) => /\bgetRunStatus\s*\(/.test(code(file)));
    const unexpected = direct.filter(
      (file) => !ALLOWED_ONE_SHOT.some((allowed) => file.path.includes(allowed)),
    );
    expect(unexpected.map((d) => d.path)).toEqual([]);

    // The allowlist must not rot into a list of files that no longer exist.
    for (const allowed of ALLOWED_ONE_SHOT) {
      const file = direct.find((candidate) => candidate.path.includes(allowed));
      expect(file).toBeDefined();
      expect(code(file!), allowed).not.toMatch(/setInterval\s*\(|setTimeout\s*\(|refetchInterval/);
    }
  });
});
