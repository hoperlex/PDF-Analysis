/**
 * A recorded run must never be presentable as a live one.
 *
 * A named PC-01 acceptance criterion, and not a cosmetic one: the whole value of a
 * recorded-provider run is that it is cheap and repeatable, and the whole danger of it is
 * that its output looks exactly like a live run's. If the screen does not say which it is,
 * a reviewer can accept findings from a fixture replay believing a model just produced
 * them.
 *
 * The seam puts `provider_mode` on the run badge rather than in a caption somewhere else
 * (§3.2), and «Разбор» renders it in two places — the header line of the page and the
 * evidence viewer's provenance line — because the reviewer should not have to scroll to
 * learn which they are looking at, and because the CSV they are about to hand someone carries
 * `provider_mode` as its own column. `UIP-S06-05` took the badge out of the file actions of
 * the page: the header (`UIP-S06-04`) is where the mode is said, and it is asserted there
 * below, not dropped with the badge. The card layout of the export panel, which the page no
 * longer draws, still carries it.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { observationProviderMode } from '@/entities/finding-observation';
import { ReviewPage } from '@/_pages/review';
import { EvidenceViewer } from '@/widgets/evidence-viewer';
import { ExportPanel } from '@/widgets/export-panel';
import { CSV_COLUMNS, queryKeys } from '@/shared/api';
import type { ProviderMode } from '@/shared/api';

import { newClient, renderWith } from '../screens/harness';
import { PROJECT_UID, RUN_ID, observation, provenance, render, runStatus } from './fixtures';

const OBJECT_URL = 'blob:https://app.test/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';

describe('the evidence viewer carries the observation provenance', () => {
  it.each(['recorded', 'live'] as const)('shows provider_mode %s', (mode) => {
    const observed = observation({ provenance: provenance({ provider_mode: mode }) });
    expect(observationProviderMode(observed)).toBe(mode);

    const markup = render(
      createElement(EvidenceViewer, {
        observation: observed,
        activePage: 7,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    expect(markup).toContain(`data-provider-mode="${mode}"`);
  });

  it('never labels a recorded observation live', () => {
    const markup = render(
      createElement(EvidenceViewer, {
        observation: observation({ provenance: provenance({ provider_mode: 'recorded' }) }),
        activePage: 7,
        onPageChange: () => {},
        documentUrl: OBJECT_URL,
      }),
    );

    expect(markup).toContain('data-provider-mode="recorded"');
    expect(markup).not.toContain('data-provider-mode="live"');
  });
});

/** The header line of «Разбор» over a run read in the given mode: from its opening tag to its closing one. */
function reviewHeader(mode: ProviderMode, state: 'published' | 'failed' = 'published'): string {
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(RUN_ID), runStatus({ run_id: RUN_ID, provider_mode: mode, state }));
  const markup = renderWith(client, createElement(ReviewPage, { projectUid: PROJECT_UID, runId: RUN_ID }));
  const from = markup.indexOf('data-review-header');
  expect(from).toBeGreaterThan(-1);
  return markup.slice(from, markup.indexOf('</header>', from));
}

describe('the header of the review page carries the run provider mode', () => {
  it.each(['recorded', 'live'] as const)('says %s on the run badge, beside the state', (mode) => {
    const header = reviewHeader(mode);
    expect(header).toContain('data-run-state="published"');
    expect(header).toContain(`data-provider-mode="${mode}"`);
    expect(header).toContain(mode === 'recorded' ? 'из записи' : 'живой вызов');
  });

  it('never presents a recorded run as live, or a live one as recorded', () => {
    expect(reviewHeader('recorded')).not.toContain('data-provider-mode="live"');
    expect(reviewHeader('recorded')).not.toContain('живой вызов');
    expect(reviewHeader('live')).not.toContain('data-provider-mode="recorded"');
    expect(reviewHeader('live')).not.toContain('из записи');
  });

  it('states the mode even when the run did not publish a result', () => {
    // The header must not carry the mode only for a run the file actions are offered for.
    const header = reviewHeader('recorded', 'failed');
    expect(header).toContain('data-run-state="failed"');
    expect(header).toContain('data-provider-mode="recorded"');
  });

  it('is the one place on the page that says it for the file actions: their bar draws no badge', () => {
    const bar = (state: 'published' | 'failed') => render(
      createElement(ExportPanel, { runId: RUN_ID, runState: state, providerMode: 'recorded', onExport: () => {}, layout: 'bar' }),
    );
    for (const state of ['published', 'failed'] as const) {
      expect(bar(state)).not.toContain('data-provider-mode');
    }
  });
});

describe('the card layout of the export panel carries the run provider mode', () => {
  it('renders it on the run badge, beside the state', () => {
    const markup = render(
      createElement(ExportPanel, {
        runId: RUN_ID,
        runState: 'published',
        providerMode: 'recorded',
        onExport: () => {},
      }),
    );

    expect(markup).toContain('data-run-state="published"');
    expect(markup).toContain('data-provider-mode="recorded"');
    expect(markup).not.toContain('data-provider-mode="live"');
  });

  it('states the mode even when the run is not exportable', () => {
    // The panel's other branch renders NotApplicable. It would be easy for the badge to
    // live only in the exportable branch, and then a `failed` recorded run would show no
    // mode at all.
    const markup = render(
      createElement(ExportPanel, {
        runId: RUN_ID,
        runState: 'failed',
        providerMode: 'recorded',
        onExport: () => {},
      }),
    );

    expect(markup).toContain('data-provider-mode="recorded"');
    expect(markup).toContain('data-exportable="false"');
  });

  it('keeps provider_mode a CSV column, so the file says it too', () => {
    // The screen and the exported file have to agree. This asserts the column exists in
    // the frozen list rather than restating the list.
    expect(CSV_COLUMNS).toContain('provider_mode');
    expect(CSV_COLUMNS).toContain('run_state');
  });
});
