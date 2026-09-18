/**
 * `widgets/run-progress` — the screen PC-01 criterion 4 is about, and the screen no test
 * reached.
 *
 * `W12-WEB` §10 ran ten mutations inside the region `web/tests` does not import. Three of
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
    expect(markup.toLowerCase()).toContain('loading');
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
    expect(markup).toContain('not reported');
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
    expect(markup).toContain('It is not');
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
    expect(markup).toContain('This reading is final.');
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
    expect(markup).toContain('Review findings');
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
    expect(markup).toContain('There is nothing to review.');
    expect(markup).toContain(`<code>${state}</code>`);
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
    const linkTail = markup.slice(markup.indexOf('Review findings'));
    expect(linkTail).toContain('<strong>recorded</strong>');
  });
});

/** The state vocabulary is the contract's word: no "in progress", no "done", no "OK". */
describe('the run state is rendered as the contract names it', () => {
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

  it.each(ALL)('%s appears on the badge as itself', (state) => {
    const markup = screen({ state, published_finding_count: 0 });
    expect(markup).toContain(`data-run-state="${state}"`);
    expect(markup).toContain(`>${state}</span>`);
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
      'Published findings',
    );
    expect(screen({ state: 'published', published_finding_count: 7 })).toContain('7');
  });

  it('published with an unreported count says so rather than showing zero', () => {
    const markup = screen({ state: 'published', published_finding_count: null as never });
    expect(markup).toContain('not reported');
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
    expect(markup).toContain('carries no degradation set');
    expect(markup).not.toContain('data-run-outcome="published"');
  });

  it('cancelled published nothing and says so', () => {
    const markup = screen({ state: 'cancelled', published_finding_count: 0 });
    expect(markup).toContain('data-run-outcome="cancelled"');
    expect(markup).toContain('Nothing was published.');
    expect(markup).not.toContain('Published findings');
  });

  it('an open run implies no result', () => {
    const markup = screen({ state: 'running', terminal_at: null });
    expect(markup).toContain('data-run-outcome="in_flight"');
    expect(markup).toContain('No result has been published yet');
  });
});
