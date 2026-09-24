/**
 * What two runs of one version can be said to agree and disagree on.
 *
 * `R-23`'s addendum is the whole subject of this file: *no invented numbers; an empty
 * screen is more honest than a plausible one.* On a comparison screen the invention is not
 * a fabricated figure — it is **an agreement that was never measured**. Two runs that both
 * omit a field have not been shown to agree about it, and a row saying «совпадает» there
 * is a sentence a reviewer would act on.
 *
 * So the four verdicts are held here one by one, and each case names the wrong answer it
 * refuses rather than only the right one it expects.
 */

import { describe, expect, it } from 'vitest';

import type { RunState, RunStatus, StageState } from '@/shared/api';
import {
  compareReadings,
  comparedCount,
  comparedFacts,
  comparedStages,
  defaultPair,
  differenceCount,
  runElapsedMs,
  terminalDetailDigest,
  terminalDetailKeys,
} from '@/entities/audit-run';

const RUN_A = 'run_01M2545JSD15ETSNNV904X991J';
const RUN_B = 'run_01M2545JSD15ETSNNV904X991K';

function reading(over: Partial<RunStatus> = {}): RunStatus {
  return {
    run_id: RUN_A,
    project_uid: 'prj_01M2545JSD15ETSNNV904X991J',
    version_uid: 'ver_01M2545JSD15ETSNNV904X991J',
    provider_mode: 'recorded',
    created_at: '2026-01-01T00:00:00Z',
    state: 'published' as RunState,
    stages: [],
    ...over,
  };
}

function stage(over: Partial<StageState> & Pick<StageState, 'stage_id' | 'status'>): StageState {
  return { started_at: null, finished_at: null, error_code: null, ...over };
}

function verdictOf(facts: ReturnType<typeof comparedFacts>, factId: string): string {
  const row = facts.find((candidate) => candidate.factId === factId);
  expect(row, `no compared fact ${factId}`).toBeDefined();
  return (row as { comparison: string }).comparison;
}

describe('a fact neither reading carries was not compared', () => {
  it('is `absent`, and is never `same`', () => {
    // THE CASE THIS FILE EXISTS FOR. `same` here would claim the two runs agree about a
    // failure neither of them had.
    expect(compareReadings(null, null)).toBe('absent');
    expect(compareReadings(undefined, undefined)).toBe('absent');
    expect(compareReadings(null, undefined)).toBe('absent');
    expect(compareReadings(null, null)).not.toBe('same');
  });

  it('is `absent` on two published runs, for the terminal reason and its detail', () => {
    const facts = comparedFacts(reading(), reading({ run_id: RUN_B }));
    expect(verdictOf(facts, 'terminal_reason')).toBe('absent');
    expect(verdictOf(facts, 'terminal_detail')).toBe('absent');
  });

  it('is excluded from the compared count, so a summary counts what was measured', () => {
    const facts = comparedFacts(reading(), reading({ run_id: RUN_B }));
    expect(comparedCount(facts)).toBeLessThan(facts.length);
    expect(facts.filter((row) => row.comparison === 'absent').length).toBeGreaterThan(0);
  });
});

describe('an absent figure and a reported zero are different facts', () => {
  it('reports `one_sided` where one run published nothing and the other never published', () => {
    // `published_finding_count: 0` is "this run published no findings"; the field's
    // absence is "this run never reached publication". Folding the second into the first
    // is the `D-3` class of invention.
    const zero = reading({ published_finding_count: 0 });
    const absent = reading({ run_id: RUN_B, state: 'failed', terminal_reason: 'analysis_failed' });
    const facts = comparedFacts(zero, absent);
    expect(verdictOf(facts, 'published_finding_count')).toBe('one_sided');
    expect(verdictOf(facts, 'published_finding_count')).not.toBe('differs');
    expect(verdictOf(facts, 'published_finding_count')).not.toBe('same');
  });

  it('reports `same` for two runs that both published nothing', () => {
    const facts = comparedFacts(
      reading({ published_finding_count: 0 }),
      reading({ run_id: RUN_B, published_finding_count: 0 }),
    );
    expect(verdictOf(facts, 'published_finding_count')).toBe('same');
  });

  it('counts `one_sided` as a difference and `absent` as nothing', () => {
    const facts = comparedFacts(
      reading({ published_finding_count: 0 }),
      reading({ run_id: RUN_B }),
    );
    expect(differenceCount(facts)).toBeGreaterThan(0);
    expect(differenceCount(facts)).toBeLessThanOrEqual(comparedCount(facts));
  });
});

describe('a cost is comparable only when the reading carries its call count', () => {
  it('treats a cost with no call count as absent rather than as a figure', () => {
    // `D-15`: the run total sums across retry attempts, so a figure with no count beside
    // it cannot be told apart from a first-try one. `runCost` calls that `unreadable`, and
    // a comparison must not print it against a real figure as though the two were peers.
    const unreadable = reading({ cost_micros: 1234 });
    const reported = reading({ run_id: RUN_B, cost_micros: 1234, model_call_count: 2 });
    const facts = comparedFacts(unreadable, reported);
    expect(verdictOf(facts, 'cost_micros')).toBe('one_sided');
    expect(verdictOf(facts, 'cost_micros')).not.toBe('same');
  });

  it('compares two well-formed costs on the figure', () => {
    const facts = comparedFacts(
      reading({ cost_micros: 1234, model_call_count: 2 }),
      reading({ run_id: RUN_B, cost_micros: 1234, model_call_count: 3 }),
    );
    expect(verdictOf(facts, 'cost_micros')).toBe('same');
    expect(verdictOf(facts, 'model_call_count')).toBe('differs');
  });

  it('keeps the basis a row of its own, so the same figure on two bases still differs', () => {
    const facts = comparedFacts(
      reading({ cost_micros: 1234, model_call_count: 2, cost_basis: 'measured' }),
      reading({ run_id: RUN_B, cost_micros: 1234, model_call_count: 2, cost_basis: 'estimated' }),
    );
    expect(verdictOf(facts, 'cost_micros')).toBe('same');
    expect(verdictOf(facts, 'cost_basis')).toBe('differs');
  });
});

describe('a run that finished before it started has no duration to compare', () => {
  it('reads `null` rather than a negative span', () => {
    const backwards = reading({
      created_at: '2026-01-01T00:05:00Z',
      terminal_at: '2026-01-01T00:00:00Z',
    });
    expect(runElapsedMs(backwards)).toBeNull();
  });

  it('is therefore `one_sided` against a run that has one', () => {
    const facts = comparedFacts(
      reading({ created_at: '2026-01-01T00:05:00Z', terminal_at: '2026-01-01T00:00:00Z' }),
      reading({ run_id: RUN_B, created_at: '2026-01-01T00:00:00Z', terminal_at: '2026-01-01T00:01:00Z' }),
    );
    expect(verdictOf(facts, 'duration')).toBe('one_sided');
  });
});

describe('the terminal detail is compared as a bag of classifiers, not as an object', () => {
  it('has no empty form: the schema forbids one and `null` is the only absence', () => {
    expect(terminalDetailKeys(reading())).toBeNull();
    expect(terminalDetailKeys(reading({ terminal_detail: {} }))).toBeNull();
    expect(terminalDetailDigest(reading({ terminal_detail: {} }))).toBeNull();
  });

  it('does not let key order make two identical details differ', () => {
    const facts = comparedFacts(
      reading({
        state: 'failed',
        terminal_reason: 'dependency_unavailable',
        terminal_detail: { dependency: 'provider', stage_id: 'text_analysis' },
      }),
      reading({
        run_id: RUN_B,
        state: 'failed',
        terminal_reason: 'dependency_unavailable',
        terminal_detail: { stage_id: 'text_analysis', dependency: 'provider' },
      }),
    );
    expect(verdictOf(facts, 'terminal_detail')).toBe('same');
  });

  it('does report a real disagreement between two details', () => {
    const facts = comparedFacts(
      reading({ state: 'failed', terminal_reason: 'dependency_unavailable', terminal_detail: { dependency: 'provider' } }),
      reading({ run_id: RUN_B, state: 'failed', terminal_reason: 'dependency_unavailable', terminal_detail: { dependency: 'object_storage' } }),
    );
    expect(verdictOf(facts, 'terminal_detail')).toBe('differs');
  });
});

describe('a stage only one run reported is one-sided, not different', () => {
  it('says `one_sided` and leaves the other side empty', () => {
    const rows = comparedStages(
      reading({ stages: [stage({ stage_id: 'block_analysis', status: 'succeeded' })] }),
      reading({ run_id: RUN_B, stages: [] }),
    );
    const block = rows.find((row) => row.stageId === 'block_analysis');
    expect(block?.comparison).toBe('one_sided');
    expect(block?.right.status).toBeNull();
    // And it is NOT one of the four PC-01 schedules, so it carries a dependency and no
    // ordinal -- the rule `run-presentation.ts` states and this screen inherits.
    expect(block?.ordinal).toBeNull();
    expect(block?.expected).toBe(false);
  });

  it('says `absent` for a scheduled stage neither run has reported', () => {
    const rows = comparedStages(reading({ stages: [] }), reading({ run_id: RUN_B, stages: [] }));
    expect(rows.map((row) => row.stageId)).toEqual([
      'source_preparation',
      'page_geometry_extraction',
      'document_context_build',
      'text_analysis',
    ]);
    expect(rows.every((row) => row.comparison === 'absent')).toBe(true);
  });

  it('compares the status and the elapsed span separately', () => {
    // Two stages can both succeed and take very different times, and a screen that folded
    // the two questions into one verdict would say they agree.
    const rows = comparedStages(
      reading({
        stages: [
          stage({
            stage_id: 'text_analysis',
            status: 'succeeded',
            started_at: '2026-01-01T00:00:00Z',
            finished_at: '2026-01-01T00:00:01Z',
          }),
        ],
      }),
      reading({
        run_id: RUN_B,
        stages: [
          stage({
            stage_id: 'text_analysis',
            status: 'succeeded',
            started_at: '2026-01-01T00:00:00Z',
            finished_at: '2026-01-01T00:00:09Z',
          }),
        ],
      }),
    );
    const text = rows.find((row) => row.stageId === 'text_analysis');
    expect(text?.comparison).toBe('same');
    expect(text?.durationComparison).toBe('differs');
  });
});

describe('the default pair is the server order, not a second opinion about it', () => {
  it('takes the first two items, because `listRuns` answers newest first', () => {
    const newest = reading({ run_id: RUN_A, created_at: '2026-01-02T00:00:00Z' });
    const previous = reading({ run_id: RUN_B, created_at: '2026-01-01T00:00:00Z' });
    const third = reading({ run_id: 'run_01M2545JSD15ETSNNV904X991M', created_at: '2026-01-03T00:00:00Z' });
    // The third item carries the LATEST `created_at` on purpose: a pair that re-sorted by
    // timestamp would pick it, and the contract's order is the authority here.
    const pair = defaultPair([newest, previous, third]);
    expect(pair?.[0].run_id).toBe(RUN_B);
    expect(pair?.[1].run_id).toBe(RUN_A);
  });

  it('is null below two runs, which is a screen state and not an error', () => {
    expect(defaultPair([])).toBeNull();
    expect(defaultPair([reading()])).toBeNull();
  });
});
