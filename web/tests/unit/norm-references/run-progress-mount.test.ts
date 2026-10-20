/**
 * `NORM-REFS-RUN-01`: «Нормативные ссылки» is part of a finished run's page and of no other.
 *
 * Rendered over a seeded cache, as `tests/unit/screens/run-progress.test.ts` does. A run that is
 * still in flight may not have reached its saved text layer yet, so «нет текстового слоя» would
 * be a claim about a run that has not got that far: the section is mounted only once the run
 * has stopped, whatever way it stopped, and asks for the run's own identity.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { RunState } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { RunProgress } from '@/widgets/run-progress';

import { PROJECT_UID, RUN_ID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';

function page(state: RunState, withReferences = false): string {
  const status = runStatus({ state });
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  if (withReferences) {
    client.setQueryData(queryKeys.runs.normReferences(status.run_id), {
      run_id: status.run_id, version_uid: status.version_uid, state: 'text_unavailable', page_count: 3,
    });
  }
  return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }));
}

describe('where the section appears', () => {
  it.each(['published', 'partial', 'failed', 'cancelled'] as const)('a %s run carries it', (state) => {
    const markup = page(state);
    expect(markup).toContain('data-norm-references=""');
    expect(markup).toContain('Нормативные ссылки');
  });

  it.each(['created', 'queued', 'running', 'validating'] as const)('a %s run does not', (state) => {
    const markup = page(state);
    expect(markup).toContain(`data-run-id="${RUN_ID}"`);
    expect(markup).not.toContain('data-norm-references');
    expect(markup).not.toContain('Нормативные ссылки');
  });

  it('says what stops the list once the run has stopped, from the run\'s own cache entry', () => {
    const markup = page('published', true);
    expect(markup).toContain('data-norm-references-state="text_unavailable"');
    expect(markup).toContain('нет сохранённого текстового слоя');
  });

  it('sits between the review link and the polling note, after the run\'s own facts', () => {
    const markup = page('published');
    const review = markup.indexOf('Разбор');
    const section = markup.indexOf('data-norm-references=""');
    const polling = markup.indexOf('Показание окончательное?');
    expect(review).toBeGreaterThan(-1);
    expect(section).toBeGreaterThan(review);
    expect(polling).toBeGreaterThan(section);
  });
});
