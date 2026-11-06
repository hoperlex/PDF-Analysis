/**
 * `UI-A-65`: the open run's live line, and the time each stage took on the rail (the original's stage cards and
 * live banner, as far as the reading states them). A closed run has neither the line nor a clock.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { stageRows } from '@/entities/audit-run';
import { RunLiveLineView, RunProgress, liveStageOf } from '@/widgets/run-progress';

import { PROJECT_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';

function screen(overrides: Partial<RunStatus> = {}): string {
  const status = runStatus(overrides);
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }));
}

describe('the live line of an open run', () => {
  it('names the first scheduled stage the run has not reported, and none when all are reported', () => {
    const open = stageRows({ stages: [{ stage_id: 'source_preparation', status: 'succeeded', error_code: null }] });
    expect(liveStageOf(open)?.stageId).toBe('page_geometry_extraction');
    const done = stageRows({
      stages: open.map((row) => ({ stage_id: row.stageId, status: 'succeeded' as const, error_code: null })),
    });
    expect(liveStageOf(done)).toBeNull();
  });

  it('says the stage and the elapsed time, and «—» before the clock is read', () => {
    const rows = stageRows({ stages: [] });
    const markup = renderToStaticMarkup(createElement(RunLiveLineView, { stage: liveStageOf(rows), elapsed: '—' }));
    expect(markup).toContain('data-run-live="source_preparation"');
    expect(markup).toContain('Сейчас:');
    expect(markup).toContain('идёт —');
  });

  it('is drawn for an open run and not for a closed one', () => {
    expect(screen({ state: 'running', terminal_at: null })).toContain('data-run-live=');
    expect(screen({ state: 'published' })).not.toContain('data-run-live=');
    expect(screen({ state: 'running', terminal_at: null, interrupted_reason: 'worker_lost' })).not.toContain('data-run-live=');
  });
});

describe('the time a stage took, on the rail', () => {
  it('states it under a stage that has both ends, and nothing under one that has not', () => {
    const markup = screen({
      stages: [
        { stage_id: 'source_preparation', status: 'succeeded', error_code: null, started_at: '2026-11-06T10:00:00.000Z', finished_at: '2026-11-06T10:00:00.030Z' },
        { stage_id: 'page_geometry_extraction', status: 'succeeded', error_code: null },
      ],
    });
    expect(markup).toMatch(/data-pipeline-stage="source_preparation"[^>]*>.*?data-pipeline-took="30 ms"/s);
    expect((markup.match(/data-pipeline-took=/g) ?? []).length).toBe(1);
  });
});
