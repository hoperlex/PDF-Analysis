/**
 * The stage-comparison screen, rendered.
 *
 * `R-23`'s addendum — *no invented numbers; an empty screen is more honest than a
 * plausible one* — is a claim about **markup**, not about a model, so it is held here
 * against what a browser would show rather than against the functions behind it.
 * `tests/unit/run/run-comparison.test.ts` holds the verdicts; this file holds what each
 * verdict puts on a screen.
 *
 * Three properties, and each has a defect behind it that this programme has already paid
 * for:
 *
 *   1. **A fact neither run carries prints nothing.** Not `0`, not `—` beside a number
 *      that came from somewhere else. `D-3`.
 *   2. **No machine word reaches the reviewer.** A stage id is `data-stage-id` and a
 *      Russian label is the text. `D-62` was opened by a person reading the screen,
 *      because the guard that should have caught it had the schema on an allowlist.
 *   3. **Each of the four screen states is the state it claims to be.** A version with one
 *      run is not-applicable and not empty; a failed query is an error and not an empty
 *      list. `W32-SEE` found an English sentence in a branch nothing rendered, and three
 *      fixtures in `tests/unit/styles/screens.ts` were named for states they never
 *      reached.
 *
 * The expected counts below are LITERALS. `OPERATING_CONSTRAINTS.md` §12: an expectation
 * built out of `comparedFacts` would move with the thing it measures and could not see it
 * being wrong.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { AppRouterContext } from 'next/dist/shared/lib/app-router-context.shared-runtime';
import type { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

import type { ErrorCode, ErrorEnvelope, RunStatus, StageState } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { RUN_PAGE_LIMIT } from '@/entities/audit-run';
import { StageComparisonPage } from '@/_pages/stage-comparison';

import { newClient, renderWith, seedError } from './harness';

const PROJECT_UID = 'prj_01M2545JSD15ETSNNV904X991J';
const VERSION_UID = 'ver_01M2545JSD15ETSNNV904X991J';
const NEWER = 'run_01M2545JSD15ETSNNV904X991J';
const OLDER = 'run_01M2545JSD15ETSNNV904X991K';

function stubRouter(): AppRouterInstance {
  return {
    push: () => {}, replace: () => {}, back: () => {}, forward: () => {},
    refresh: () => {}, prefetch: () => {},
  } as unknown as AppRouterInstance;
}

function screen(seed: (client: ReturnType<typeof newClient>) => void, versionUid = VERSION_UID): string {
  const client = newClient();
  seed(client);
  return renderWith(
    client,
    createElement(
      AppRouterContext.Provider,
      { value: stubRouter() },
      createElement(StageComparisonPage, { projectUid: PROJECT_UID, versionUid }),
    ),
  );
}

function stage(over: Partial<StageState> & Pick<StageState, 'stage_id' | 'status'>): StageState {
  return { started_at: null, finished_at: null, error_code: null, ...over };
}

function base(over: Partial<RunStatus>): RunStatus {
  return {
    run_id: NEWER,
    project_uid: PROJECT_UID,
    version_uid: VERSION_UID,
    provider_mode: 'recorded',
    created_at: '2026-01-01T00:00:00Z',
    state: 'published',
    stages: [],
    ...over,
  };
}

/**
 * The pair every case below compares, newest first, as `listRuns` answers.
 *
 * Chosen so all four verdicts appear once: `differs` five times, `same` on the provider
 * mode, `one_sided` five times, and `absent` on the cost basis — which neither run
 * reports, so nothing was compared and the row must say so.
 */
const NEWER_RUN: RunStatus = base({
  run_id: NEWER,
  state: 'failed',
  terminal_reason: 'dependency_unavailable' as ErrorCode,
  terminal_detail: { dependency: 'provider' },
  published_finding_count: 0,
  diagnostic_observation_count: 2,
  model_call_count: 4,
  cost_micros: 1234,
  created_at: '2026-01-02T00:00:00Z',
  terminal_at: '2026-01-02T00:02:30Z',
  stages: [
    stage({ stage_id: 'source_preparation', status: 'succeeded', started_at: '2026-01-02T00:00:00Z', finished_at: '2026-01-02T00:00:30Z' }),
    stage({ stage_id: 'text_analysis', status: 'failed', error_code: 'analysis_failed' }),
  ],
});

const OLDER_RUN: RunStatus = base({
  run_id: OLDER,
  state: 'published',
  published_finding_count: 3,
  created_at: '2026-01-01T00:00:00Z',
  terminal_at: '2026-01-01T00:04:00Z',
  stages: [stage({ stage_id: 'source_preparation', status: 'succeeded', started_at: '2026-01-01T00:00:00Z', finished_at: '2026-01-01T00:00:30Z' })],
});

function seedRuns(items: readonly RunStatus[]) {
  return (client: ReturnType<typeof newClient>): void => {
    client.setQueryData(queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT), {
      items,
      page: { next_cursor: null },
    });
  };
}

/** The text a browser would show: tags removed, entities decoded, whitespace collapsed. */
function visible(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, ' ')
    .replace(/&#x27;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/&#(\d+);/g, (_, d: string) => String.fromCharCode(Number(d)))
    .replace(/\s+/g, ' ')
    .trim();
}

/** One row of the fact table, by the `data-fact` it carries. */
function factRow(markup: string, factId: string): string {
  const opening = markup.indexOf(`data-fact="${factId}"`);
  expect(opening, `no row for ${factId}`).toBeGreaterThan(-1);
  const start = markup.lastIndexOf('<tr', opening);
  const end = markup.indexOf('</tr>', opening);
  return markup.slice(start, end);
}

describe('the four states of a comparison screen are four different states', () => {
  it('renders a loading state while the runs are in flight', () => {
    const markup = screen(() => {});
    expect(visible(markup)).toContain('Загрузка');
    expect(markup).not.toContain('data-fact=');
  });

  it('renders an empty state — not a comparison — when the version has no runs', () => {
    const markup = screen(seedRuns([]));
    expect(visible(markup)).toContain('прогонов не запускалось');
    expect(markup).not.toContain('data-fact=');
  });

  it('renders a NOT-APPLICABLE state, not an empty one, when the version has one run', () => {
    // A version with one run is not a version with nothing: the question does not apply
    // yet. `shared/ui`'s five states keep those apart and this screen must not collapse
    // them, because "there is nothing here" would send a reviewer looking for a defect.
    const markup = screen(seedRuns([NEWER_RUN]));
    expect(visible(markup)).toContain('Для сравнения нужны два прогона');
    expect(visible(markup)).not.toContain('прогонов не запускалось');
    expect(markup).not.toContain('data-fact=');
  });

  it('renders an error state — not an empty list — when the request failed', () => {
    const envelope: ErrorEnvelope = {
      contract_version: '1.0.0-draft.1',
      error_code: 'dependency_unavailable',
      message: 'Одна безопасная для вызывающей стороны фраза.',
      correlation_id: 'cid-comparison-1',
      retryable: true,
    };
    const markup = screen((client) =>
      seedError(
        client,
        queryKeys.runs.list(VERSION_UID, undefined, RUN_PAGE_LIMIT),
        new ApiError(503, envelope, 'cid-comparison-1'),
      ),
    );
    expect(markup).toContain('data-list-failure=');
    expect(markup).not.toContain('data-fact=');
    expect(visible(markup)).not.toContain('прогонов не запускалось');
  });

  it('refuses an address that is not an identifier, and makes no request', () => {
    const markup = screen(seedRuns([NEWER_RUN, OLDER_RUN]), 'not-an-identifier');
    expect(visible(markup)).toContain('Это не адрес версии');
    expect(markup).not.toContain('data-fact=');
  });
});

describe('a fact neither run carries prints nothing at all', () => {
  const markup = screen(seedRuns([NEWER_RUN, OLDER_RUN]));

  it('marks it `absent` and puts a dash on both sides', () => {
    const row = factRow(markup, 'cost_basis');
    expect(row).toContain('data-comparison="absent"');
    // Neither side may carry a digit: a basis that was never reported has no value, and
    // the nearest plausible one -- the other run's -- is the invention this refuses.
    const cells = visible(row).replace('Основание стоимости', '');
    expect(cells).not.toMatch(/\d/);
    expect(cells).toContain('не сообщается ни одним прогоном');
  });

  it('does not call it agreement', () => {
    expect(factRow(markup, 'cost_basis')).not.toContain('data-comparison="same"');
    expect(visible(factRow(markup, 'cost_basis'))).not.toContain('совпадает');
  });

  it('keeps a one-sided reading separate from a difference', () => {
    // One run recorded a terminal reason and the other had none to record. That is a
    // difference in what was written down, and phrasing it as «отличается» would say the
    // two runs stopped for different reasons.
    const row = factRow(markup, 'terminal_reason');
    expect(row).toContain('data-comparison="one_sided"');
    expect(visible(row)).toContain('есть только у одного прогона');
  });

  it('counts only what it compared', () => {
    // LITERALS, per §12: eleven of the twelve facts were comparable (the cost basis was
    // not), and ten of those eleven disagree.
    expect(markup).toContain('data-compared-count="11"');
    expect(markup).toContain('data-difference-count="10"');
  });
});

describe('the machine vocabulary stays in the attributes', () => {
  const markup = screen(seedRuns([NEWER_RUN, OLDER_RUN]));

  it('renders a stage id as a Russian label and keeps the contract value in `data-`', () => {
    expect(markup).toContain('data-stage-id="text_analysis"');
    expect(visible(markup)).toContain('Анализ текста');
    expect(visible(markup)).not.toContain('text_analysis');
  });

  it('renders a run state as a Russian label and keeps the contract value in `data-`', () => {
    expect(markup).toContain('data-run-state="failed"');
    expect(markup).toContain('data-run-state="published"');
    expect(visible(markup)).not.toContain('published');
  });

  it('carries `terminal_detail` as an attribute and a count, never as prose', () => {
    // `D-46`'s classifiers come from the catalog's `safe_detail_keys`, which no contract
    // `enum` publishes -- so there is no derived label map for them and printing them
    // raw would be `D-62` again.
    expect(markup).toContain('data-terminal-detail="dependency=provider"');
    expect(visible(markup)).toContain('уточнений: 1');
    expect(visible(markup)).not.toContain('dependency=provider');
  });

  it('names both runs on the element, so an instrument can say which pair it read', () => {
    expect(markup).toContain(`data-left-run="${OLDER}"`);
    expect(markup).toContain(`data-right-run="${NEWER}"`);
  });
});

describe('the comparison reads the server order rather than re-deriving it', () => {
  it('puts the newest run on the right, whatever the timestamps say', () => {
    // The OLDER-stamped run is served first here, which no real answer would do -- and
    // that is the point: the screen must follow `listRuns`' declared order, not a
    // comparator of its own. A screen that sorted would swap these two.
    const markup = screen(seedRuns([OLDER_RUN, NEWER_RUN]));
    expect(markup).toContain(`data-left-run="${NEWER}"`);
    expect(markup).toContain(`data-right-run="${OLDER}"`);
  });
});

describe('the screen says what is missing without explaining the transport', () => {
  const text = visible(screen(seedRuns([NEWER_RUN, OLDER_RUN])));

  it('tells the reviewer that deeper comparison arrives later', () => {
    expect(text).toContain('появится позже');
  });

  it('names no operation, field or schema to the reviewer', () => {
    // `R-18`, and `D-58` was closed by deleting exactly this. The sentence belongs in a
    // comment; a reviewer has no use for it.
    for (const word of ['listRuns', 'getRunStatus', 'RunStatus', 'API', 'endpoint']) {
      expect(text).not.toContain(word);
    }
  });
});
