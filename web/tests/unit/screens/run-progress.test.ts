/**
 * `widgets/run-progress` — the screen PC-01 criterion 4 is about, and the screen no test
 * reached.
 *
 * `W12-WEB` §10 ran ten mutations inside the region `web/tests` does not import { STATE_LABELS } from '@/shared/ui';
import. Three of
 * them are in this file's subject and all three survived with the whole frontend suite
 * green:
 *
 *   U-01  the terminal reason is replaced by the constant `redacted`;
 *   U-02  the activity indicator keeps running on a stopped run (`animating = true`);
 *   U-03  the review link is offered for every run, including `failed`.
 *
 * `terminal_reason` reaches a user in exactly one line of this application and that line
 * could be made to print a constant with 498 tests green. Each `it` below names the
 * mutation it exists to redden; the session report records which ones it does redden,
 * measured by re-running `W12-WEB`'s `b8.json`.
 *
 * Rendered with `renderToStaticMarkup` over a seeded query cache — see `./harness.ts`.
 * The hook reads the cache in a `useState` initialiser, before any effect, which is why
 * one server pass is enough to see a real reading on screen.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { ErrorCode, RunState, RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { STATE_LABELS } from '@/shared/ui';
import { RunProgress } from '@/widgets/run-progress';

import { PROJECT_UID, RUN_ID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from './harness';

/** Render the widget over a cache seeded with one reading. */
function screen(overrides: Partial<RunStatus> = {}): string {
  const status = runStatus(overrides);
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  return renderWith(
    client,
    createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }),
  );
}

describe('the harness reaches this widget at all', () => {
  it('renders a real reading, not a spinner, when the cache carries one', () => {
    const markup = screen({ state: 'published' });
    expect(markup).toContain(`data-run-id="${RUN_ID}"`);
    expect(markup).not.toContain('am-state__title">Loading');
  });

  it('renders the loading state when the cache carries nothing', () => {
    const markup = renderWith(
      newClient(),
      createElement(RunProgress, { projectUid: PROJECT_UID, runId: RUN_ID }),
    );
    expect(markup).not.toContain(`data-run-id="${RUN_ID}"`);
    expect(markup.toLowerCase()).toContain('загрузка');
  });
});

/**
 * U-01. The assertion is on the value, and on two different values, so a mutation that
 * prints any constant — `redacted`, or the first reason this suite happens to use — is
 * red rather than green.
 */
describe('a failed run states the catalog code it terminated with (U-01)', () => {
  // Three real codes from the frozen catalog, not invented ones: `tsc` rejects a
  // `terminal_reason` that is not an `ErrorCode`, which is how the first draft of this
  // suite learned that `analysis_provider_unavailable` is not a code.
  const REASONS: readonly ErrorCode[] = [
    'analysis_failed',
    'storage_integrity_error',
    'dependency_credential_refused',
  ];

  it.each(REASONS)('renders %s as itself', (reason) => {
    const markup = screen({ state: 'failed', terminal_reason: reason, published_finding_count: 0 });
    expect(markup).toContain(`data-terminal-reason="${reason}"`);
    // The attribute alone would survive a mutation that emptied the visible text, so the
    // text between the tags is asserted too.
    expect(markup).toContain(`>${reason}</code>`);
  });

  it('does not print any other reason alongside it', () => {
    const markup = screen({
      state: 'failed',
      terminal_reason: 'analysis_failed',
      published_finding_count: 0,
    });
    expect(markup).not.toContain('redacted');
    expect(markup).not.toContain('storage_integrity_error');
  });

  it('says the reason was not reported rather than inventing one', () => {
    const markup = screen({ state: 'failed', terminal_reason: null, published_finding_count: 0 });
    expect(markup).toContain('data-run-outcome="failed"');
    expect(markup).toContain('не сообщено');
    expect(markup).not.toContain('data-terminal-reason=');
  });

  it('states the interrupted reason on a reconciled failure', () => {
    const markup = screen({
      state: 'failed',
      terminal_reason: 'internal_error',
      interrupted_reason: 'worker_lost',
      published_finding_count: 0,
    });
    expect(markup).toContain('data-interrupted-reason="worker_lost"');
    expect(markup).toContain('Сейчас он не выполняется');
  });
});

/**
 * U-02. `animating` is `isRunAnimating(status)`; the mutation pins it to `true`. On a
 * terminal reading the widget must say it is not polling, because it is not.
 */
describe('motion stops when the run stops (U-02)', () => {
  const TERMINAL: readonly RunState[] = ['published', 'partial', 'failed', 'cancelled'];

  it.each(TERMINAL)('a %s run shows no activity indicator', (state) => {
    const markup = screen({ state, published_finding_count: state === 'published' ? 1 : 0 });
    expect(markup).toContain('data-run-activity="stopped"');
    expect(markup).not.toContain('data-run-activity="polling"');
    expect(markup).toContain('показание окончательное');
  });

  it('an open run does show it, so the assertion is not vacuously true of every run', () => {
    const markup = screen({ state: 'running', terminal_at: null });
    expect(markup).toContain('data-run-activity="polling"');
    expect(markup).not.toContain('data-run-activity="stopped"');
  });

  it('a reconciled run is not animated even though its state is open', () => {
    const markup = screen({ state: 'running', terminal_at: null, interrupted_reason: 'worker_lost' });
    expect(markup).toContain('data-run-activity="stopped"');
    expect(markup).toContain('data-interrupted-reason="worker_lost"');
  });
});

/**
 * U-03. The review entry point is criterion 7's surface. The mutation offers it for every
 * run; a run that published nothing has nothing to review and must say so as a distinct
 * state, not as an empty review screen one click away.
 */
describe('review is offered only by a run that published a result (U-03)', () => {
  const REVIEWABLE: readonly RunState[] = ['published', 'partial'];
  const NOT_REVIEWABLE: readonly RunState[] = [
    'created',
    'queued',
    'running',
    'validating',
    'failed',
    'cancelled',
  ];

  it.each(REVIEWABLE)('a %s run links to review', (state) => {
    const markup = screen({ state });
    expect(markup).toContain(`/projects/${PROJECT_UID}/runs/${RUN_ID}/review`);
    expect(markup).toContain('Разобрать находки');
  });

  it.each(NOT_REVIEWABLE)('a %s run offers no review link and says why', (state) => {
    const markup = screen({
      state,
      published_finding_count: 0,
      ...(state === 'failed' ? { terminal_reason: 'analysis_failed' as ErrorCode } : {}),
      ...(state === 'created' || state === 'queued' || state === 'running' || state === 'validating'
        ? { terminal_at: null }
        : {}),
    });
    expect(markup).not.toContain(`/runs/${RUN_ID}/review`);
    expect(markup).toContain('Разбирать нечего.');
    // Used to assert `<code>${state}</code>`. Under the owner's 2026-09-22 ruling the state
    // is rendered as its Russian label, and the contract value keeps its home in
    // `data-run-state` -- which is what `PA-01` criterion 4 was re-driven against, so the
    // certification is unaffected. Both halves are asserted: a reader sees the label, and a
    // machine still finds the value. Asserting only the label would let the attribute be
    // dropped, which is what the journey and the certification read.
    expect(markup).toContain(`data-run-state="${state}"`);
    expect(markup).toContain(STATE_LABELS[state]);
    expect(markup).not.toContain(`<code>${state}</code>`);
  });
});

/**
 * Criterion 4's other half. A recorded run must never read as a live one, and a reading
 * that carries no recognised mode says `unknown` — never `live`.
 */
describe('the provider mode is on screen, twice, and is never guessed', () => {
  it.each(['live', 'recorded'] as const)('renders %s on the badge and as a sentence', (mode) => {
    const markup = screen({ provider_mode: mode });
    expect(markup).toContain(`data-provider-mode="${mode}"`);
    // Once on the badge qualifier, once in the sentence beside it.
    expect(markup.split(`data-provider-mode="${mode}"`).length - 1).toBe(2);
    expect(markup).toContain(`<strong>${mode}</strong>`);
  });

  it('calls an unrecognised mode unknown rather than live', () => {
    const markup = screen({ provider_mode: 'turbo' as never });
    expect(markup).toContain('data-provider-mode="unknown"');
    expect(markup).not.toContain('data-provider-mode="live"');
    expect(markup).not.toContain('>live<');
  });

  it('names the mode again beside the review link, so a reviewer cannot miss it', () => {
    const markup = screen({ state: 'published', provider_mode: 'recorded' });
    const linkTail = markup.slice(markup.indexOf('Разобрать находки'));
    expect(linkTail).toContain('<strong>recorded</strong>');
  });
});

/** The state vocabulary is the contract's word: no "in progress", no "done", no "OK". */
describe('the run state is labelled in Russian and carries the contract value', () => {
  const ALL: readonly RunState[] = [
    'created',
    'queued',
    'running',
    'validating',
    'published',
    'partial',
    'failed',
    'cancelled',
  ];

  /**
   * The owner ruled by direct poll on 2026-09-21 that a reviewer reads Russian, and the
   * contract value lives in the attribute. This suite asserted the opposite until then —
   * `>${state}</span>` — so its premise was overturned rather than its wording.
   *
   * BOTH halves are asserted, and the second is the load-bearing one: `W30-CERT3`
   * re-drove `PA-01` criterion 4 by reading `[data-run-state]`, and the browser journey
   * reads it too. A later change that translates the attribute reddens here.
   */
  it.each(ALL)('%s carries its contract value in the attribute', (state) => {
    const markup = screen({ state, published_finding_count: 0 });
    expect(markup).toContain(`data-run-state="${state}"`);
  });

  it.each(ALL)('%s is labelled in Russian, not as its identifier', (state) => {
    const markup = screen({ state, published_finding_count: 0 });
    expect(markup).not.toContain(`>${state}</span>`);
    expect(markup).toMatch(/<span class="am-badge__label">[а-яё]/i);
  });

  it('invents no friendly synonym anywhere on the screen', () => {
    for (const state of ALL) {
      const markup = screen({ state, published_finding_count: 0 }).toLowerCase();
      expect(markup).not.toContain('in progress');
      expect(markup).not.toContain('>done<');
    }
  });
});

/** `published` is the success terminal; `partial` and `failed` borrow nothing from it. */
describe('the three terminals are three different claims', () => {
  it('published states its finding count', () => {
    expect(screen({ state: 'published', published_finding_count: 7 })).toContain(
      'Опубликованных находок',
    );
    expect(screen({ state: 'published', published_finding_count: 7 })).toContain('7');
  });

  it('published with an unreported count says so rather than showing zero', () => {
    const markup = screen({ state: 'published', published_finding_count: null as never });
    expect(markup).toContain('не сообщено');
    expect(markup).not.toContain('Published findings: 0');
  });

  it('partial lists the degradation set it recorded', () => {
    const markup = screen({
      state: 'partial',
      degradation_set: ['text_analysis', 'page_geometry_extraction'] as never,
    });
    expect(markup).toContain('data-run-outcome="partial"');
    expect(markup).toContain('data-degraded-stage="text_analysis"');
    expect(markup).toContain('data-degraded-stage="page_geometry_extraction"');
  });

  it('partial with an empty set says the reading carries none, and does not pretend to be published', () => {
    const markup = screen({ state: 'partial', degradation_set: [] });
    expect(markup).toContain('data-run-outcome="partial"');
    expect(markup).toContain('не содержит списка деградаций');
    expect(markup).not.toContain('data-run-outcome="published"');
  });

  it('cancelled published nothing and says so', () => {
    const markup = screen({ state: 'cancelled', published_finding_count: 0 });
    expect(markup).toContain('data-run-outcome="cancelled"');
    // Translated by `W33-SECT`; the claim is the same one and the machine value is
    // still `data-run-outcome`, which is what an instrument reads.
    expect(markup).toContain('Ничего не опубликовано.');
    expect(markup).not.toContain('Опубликованных находок');
  });

  it('an open run implies no result', () => {
    const markup = screen({ state: 'running', terminal_at: null });
    expect(markup).toContain('data-run-outcome="in_flight"');
    expect(markup).toContain('Результат ещё не опубликован');
  });
});

// ======================================================================================
// W19-RUN — the timings, the counts and the cost the response has carried since W18-SEAL
// and no screen rendered.
//
//   M-3  the absent-cost and zero-cost branches render the same sentence;
//   M-4  the cost is rendered without the call count it sums;
//   M-6  the diagnostic count is rendered as the finding count, collapsing the two;
//   M-7  an `estimated` basis is rendered as a warning;
//   M-9  the cost section is dropped from the screen.
// ======================================================================================

/** A reading that made provider calls, for the cases that need one. */
function priced(overrides: Partial<RunStatus> = {}): Partial<RunStatus> {
  return { state: 'published', cost_micros: 0, cost_basis: 'measured', model_call_count: 2, ...overrides };
}

/**
 * M-3. `D-3` is this programme's record of what inventing the flattering state costs.
 * The two states must reach the user as different sentences, not as the same number.
 */
describe('a run that spent nothing and a run that called nothing read differently (M-3)', () => {
  it('says a run with no provider call has no cost to report, and does not say zero', () => {
    const markup = screen({ state: 'published', published_finding_count: 3 });
    expect(markup).toContain('data-run-cost="absent"');
    expect(markup).toContain('не обращался к провайдеру');
    // The flattering invention this test exists to prevent.
    expect(markup).not.toContain('data-run-cost="reported"');
    expect(markup).not.toContain('data-cost-micros="0"');
  });

  it('says a run whose calls were free was charged nothing, and shows the zero', () => {
    const markup = screen(priced({ published_finding_count: 3 }));
    expect(markup).toContain('data-run-cost="reported"');
    expect(markup).toContain('data-cost-micros="0"');
    expect(markup).toContain('data-run-cost-zero="reported"');
    expect(markup).not.toContain('data-run-cost="absent"');
  });

  it('gives the two states markers that cannot both appear', () => {
    const absent = screen({ state: 'published', published_finding_count: 3 });
    const free = screen(priced({ published_finding_count: 3 }));
    expect(absent).not.toBe(free);
    expect(absent.includes('data-run-cost="absent"')).toBe(true);
    expect(free.includes('data-run-cost="absent"')).toBe(false);
  });
});

/**
 * M-4. `D-15` is open and this is the screen where it would be re-created: the total sums
 * retry attempts, so a figure printed without its span is the ambiguity `D-15` is about.
 */
describe('a cost is never shown without the call count it sums (M-4)', () => {
  it('prints the call count beside the figure', () => {
    const markup = screen(priced({ cost_micros: 4_500_000, model_call_count: 3 }));
    expect(markup).toContain('data-model-call-count="3"');
    expect(markup).toContain('data-cost-micros="4500000"');
    expect(markup).toContain('4.500000');
  });

  it('distinguishes a first-try run from a retried one on the screen', () => {
    const first = screen(priced({ cost_micros: 1_000_000, model_call_count: 1 }));
    const retried = screen(priced({ cost_micros: 1_000_000, model_call_count: 4 }));
    expect(first).toContain('data-model-call-count="1"');
    expect(retried).toContain('data-model-call-count="4"');
    // Same money, different spans: the screens must not be identical.
    expect(first).not.toBe(retried);
  });

  it('shows no figure at all when the count did not arrive', () => {
    const markup = screen({
      state: 'published',
      published_finding_count: 3,
      cost_micros: 900 as never,
      cost_basis: 'estimated' as never,
    });
    expect(markup).toContain('data-run-cost="unreadable"');
    expect(markup).not.toContain('data-cost-micros');
    expect(markup).not.toContain('0.000900');
  });

  it('renders sub-cent money instead of rounding it away (M-1 on the screen)', () => {
    const markup = screen(priced({ cost_micros: 1, model_call_count: 1 }));
    expect(markup).toContain('0.000001');
    expect(markup).not.toContain('>0.00<');
  });
});

/**
 * M-6. The two counts are different facts and `findings/queries.py` keeps them apart on
 * purpose: a published finding is admitted evidence, a diagnostic observation is not.
 */
describe('findings and diagnostic observations are two counts, never one (M-6)', () => {
  it('renders both, with different values, under different labels', () => {
    const markup = screen({
      state: 'published',
      published_finding_count: 3,
      diagnostic_observation_count: 11,
    });
    expect(markup).toContain('Опубликованных находок');
    expect(markup).toContain('data-diagnostic-observation-count="11"');
    expect(markup).toContain('3');
    expect(markup).toContain('Диагностические наблюдения');
    // A mutation that printed the diagnostic count where the finding count goes, or that
    // summed them, cannot satisfy both of these.
    expect(markup).not.toContain('Published findings: 11');
    expect(markup).not.toContain('Published findings: 14');
  });

  it('says in words that an observation is not a finding', () => {
    const markup = screen({ state: 'published', published_finding_count: 1 }).toLowerCase();
    expect(markup).toContain('это не находка');
  });

  it('reports an unreported diagnostic count as unreported, not as zero', () => {
    const markup = screen({
      state: 'published',
      published_finding_count: 1,
      diagnostic_observation_count: null as never,
    });
    expect(markup).toContain('data-diagnostic-observation-count="not-reported"');
    expect(markup).not.toContain('data-diagnostic-observation-count="0"');
  });

  it('keeps the diagnostic count on a run that published nothing', () => {
    // A cancelled run has no findings to report but can still have observed something,
    // and the existing contract that it must not say "Published findings" still holds.
    const markup = screen({
      state: 'cancelled',
      published_finding_count: 0,
      diagnostic_observation_count: 2,
    });
    expect(markup).toContain('data-diagnostic-observation-count="2"');
    expect(markup).not.toContain('Опубликованных находок');
  });
});

/**
 * M-7. `W18-SEAL` notes the first live run is the first that can print `measured`, so
 * `estimated` is the ordinary case for this prototype. Rendering the ordinary case as a
 * warning trains a reviewer to ignore the one signal this field carries.
 */
describe('an estimated basis is the normal case, not a warning (M-7)', () => {
  it('renders the basis as itself', () => {
    expect(screen(priced({ cost_basis: 'estimated' }))).toContain('data-cost-basis="estimated"');
    expect(screen(priced({ cost_basis: 'measured' }))).toContain('data-cost-basis="measured"');
  });

  it('does not dress an estimated basis as an error or a warning', () => {
    const markup = screen(priced({ cost_basis: 'estimated', cost_micros: 250_000 }));
    const cost = markup.slice(markup.indexOf('data-run-cost="reported"'));
    for (const alarm of ['am-state--error', 'Warning', 'warning', 'Invalid', 'went wrong']) {
      expect(cost).not.toContain(alarm);
    }
    expect(markup.toLowerCase()).toContain('не неисправность');
  });

  it('does not default an unstated basis to measured', () => {
    const markup = screen({
      state: 'published',
      published_finding_count: 1,
      cost_micros: 5 as never,
      model_call_count: 1 as never,
    });
    expect(markup).toContain('data-cost-basis="unstated"');
    expect(markup).not.toContain('data-cost-basis="measured"');
  });
});

/** M-9. The section exists at all, on every terminal state. */
describe('the cost section is on the screen (M-9)', () => {
  it.each(['published', 'partial', 'failed', 'cancelled'] as const)(
    'renders a cost statement for a %s run',
    (state) => {
      const markup = screen({ state, published_finding_count: state === 'published' ? 1 : 0 });
      expect(markup).toContain('data-run-cost=');
      expect(markup).toContain('Диагностические наблюдения');
    },
  );
});

/**
 * M-13. The stage timings were rendered before this session and still said nothing: a run
 * finishes in about 360 ms and `formatInstant` prints to the second, so Started and
 * Finished were the same string on every row.
 */
describe('the stage timings carry a measurement, not two identical stamps (M-13)', () => {
  const stages = [
    {
      stage_id: 'source_preparation' as const,
      status: 'succeeded' as const,
      stage_version: '1.0.0',
      started_at: '2026-09-18T13:02:34.538Z',
      finished_at: '2026-09-18T13:02:34.653Z',
    },
  ];

  it('reports how long a sub-second stage took', () => {
    const markup = screen({ state: 'published', published_finding_count: 3, stages });
    expect(markup).toContain('data-stage-elapsed="115"');
    expect(markup).toContain('115 ms');
  });

  it('reports how long the whole run took', () => {
    const markup = screen({
      state: 'published',
      published_finding_count: 3,
      created_at: '2026-09-18T13:02:34.527Z',
      terminal_at: '2026-09-18T13:02:34.901Z',
    });
    expect(markup).toContain('data-run-elapsed="374"');
    expect(markup).toContain('374 ms');
  });

  it('says nothing rather than zero for a stage that never ran', () => {
    const markup = screen({ state: 'published', published_finding_count: 3, stages: [] });
    expect(markup).toContain('data-stage-elapsed="unknown"');
    expect(markup).not.toContain('data-stage-elapsed="0"');
  });
});
