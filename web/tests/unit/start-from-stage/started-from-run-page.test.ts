/**
 * `UI-A-60` / `R-151i`: a run started from a stage says so on its page, links the run it took the first stages from, and marks
 * those stages in the rail. A run started any other way shows none of it.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import type { RunStatus } from '@/shared/api';
import { RunProgress } from '@/widgets/run-progress';
import { startedFrom } from '@/widgets/run-progress/model/started-from';

import { PROJECT_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';

const SOURCE = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z';

function page(overrides: Partial<RunStatus>): string {
  const status = runStatus({ state: 'published', ...overrides });
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(status.run_id), status);
  return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }));
}

describe('the model of a run started from a stage', () => {
  it('names the stages before the start stage as taken, and the rest as computed', () => {
    const from = startedFrom({ started_from_run_id: SOURCE as never, start_stage_id: 'document_context_build' });
    expect(from?.ordinal).toBe(3);
    expect([...(from?.reusedStageIds ?? [])]).toEqual(['source_preparation', 'page_geometry_extraction']);
    expect(startedFrom({ started_from_run_id: SOURCE as never, start_stage_id: 'text_analysis' })?.reusedStageIds.size).toBe(3);
  });

  it('is nothing for a run that was not started from a stage, or whose pair is broken', () => {
    expect(startedFrom({})).toBeNull();
    expect(startedFrom({ started_from_run_id: SOURCE as never })).toBeNull();
    expect(startedFrom({ start_stage_id: 'text_analysis' })).toBeNull();
    expect(startedFrom({ started_from_run_id: SOURCE as never, start_stage_id: 'block_analysis' })).toBeNull();
  });
});

describe('the run page', () => {
  const FROM = { started_from_run_id: SOURCE as never, start_stage_id: 'text_analysis' as const };

  it('says the stage and links the earlier run, in the sentence and in the facts', () => {
    const markup = page(FROM);
    expect(markup).toContain('data-run-started-from-note="text_analysis"');
    expect(markup).toContain('Запущен с этапа 4 «Анализ текста» из прогона');
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${SOURCE}"`);
    expect(markup).toContain('<dt>Запущен с этапа</dt>');
    expect(markup).toContain(`data-run-started-from="${SOURCE}"`);
  });

  it('marks exactly the stages taken from the earlier run in the rail', () => {
    const markup = page({ ...FROM, start_stage_id: 'document_context_build' });
    expect(markup.match(/data-pipeline-reused/g)).toHaveLength(2);
    expect(markup).toMatch(/data-pipeline-stage="source_preparation"[^>]*data-pipeline-reused/);
    expect(markup).toMatch(/data-pipeline-stage="page_geometry_extraction"[^>]*data-pipeline-reused/);
    expect(markup).not.toMatch(/data-pipeline-stage="document_context_build"[^>]*data-pipeline-reused/);
    expect(markup).not.toMatch(/data-pipeline-stage="text_analysis"[^>]*data-pipeline-reused/);
  });

  it('shows none of it for a run started from a version', () => {
    const markup = page({});
    expect(markup).not.toContain('data-run-started-from');
    expect(markup).not.toContain('data-pipeline-reused');
    expect(markup).not.toContain('Запущен с этапа');
  });
});
