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
 * (§3.2), and this session renders it in three places — the review header, the export panel
 * and the evidence viewer's provenance line — because the reviewer should not have to
 * scroll to learn which they are looking at, and because the CSV they are about to hand
 * someone carries `provider_mode` as its own column.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { observationProviderMode } from '@/entities/finding-observation';
import { EvidenceViewer } from '@/widgets/evidence-viewer';
import { ExportPanel } from '@/widgets/export-panel';
import { CSV_COLUMNS } from '@/shared/api';

import { RUN_ID, observation, provenance, render } from './fixtures';

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

describe('the export panel carries the run provider mode', () => {
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
