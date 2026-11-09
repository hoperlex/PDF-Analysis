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

/**
 * `D-412` (lane J4): the details table read «0 ms» for a stage taken by reference -- its row has one instant for start and finish,
 * the moment of the reuse -- where the rail already read «из прогона». The duration cell now says where the result came from.
 */
describe('the details table of a run started from a stage', () => {
  const FROM = { started_from_run_id: SOURCE as never, start_stage_id: 'text_analysis' as const };
  const REUSED_AT = '2026-11-09T04:46:41.000Z';
  const stage = (stageId: 'source_preparation' | 'page_geometry_extraction' | 'document_context_build' | 'text_analysis', start: string, end: string) => ({
    stage_id: stageId, status: 'succeeded' as const, stage_version: '1.0.0', started_at: start, finished_at: end,
  });
  const STAGES = [
    stage('source_preparation', REUSED_AT, REUSED_AT),
    stage('page_geometry_extraction', REUSED_AT, REUSED_AT),
    stage('document_context_build', REUSED_AT, REUSED_AT),
    stage('text_analysis', '2026-11-09T04:46:41.000Z', '2026-11-09T04:46:43.500Z'),
  ];
  const row = (markup: string, stageId: string): string => {
    const found = new RegExp(`<tr data-stage-id="${stageId}"[^>]*>.*?</tr>`, 's').exec(markup);
    if (found === null) throw new Error(`no row for ${stageId}`);
    return found[0];
  };

  it('says «из прогона» for each stage taken by reference, and no duration of nothing', () => {
    const markup = page({ ...FROM, stages: STAGES });
    for (const taken of ['source_preparation', 'page_geometry_extraction', 'document_context_build']) {
      const cells = row(markup, taken);
      expect(cells).toContain('data-stage-reused=""');
      expect(cells).toMatch(/<td[^>]*data-stage-elapsed="reused"[^>]*>\s*из прогона\s*<\/td>/);
      expect(cells).not.toContain('0 ms');
      expect(cells).not.toContain('data-stage-elapsed="0"');
    }
    expect(markup.match(/data-stage-elapsed="reused"/g)).toHaveLength(3);
  });

  it('keeps the measured duration of the stage this run computed', () => {
    const cells = row(page({ ...FROM, stages: STAGES }), 'text_analysis');
    expect(cells).toContain('data-stage-elapsed="2500"');
    expect(cells).toContain('2.5 s');
    expect(cells).not.toContain('data-stage-reused');
    expect(cells).not.toContain('из прогона');
  });

  it('marks only the stages before the start stage when the run started from an earlier one', () => {
    const markup = page({ ...FROM, start_stage_id: 'document_context_build', stages: STAGES });
    expect(markup.match(/data-stage-elapsed="reused"/g)).toHaveLength(2);
    expect(row(markup, 'document_context_build')).not.toContain('data-stage-reused');
  });

  it('is unchanged for a run that was not started from a stage', () => {
    const markup = page({ stages: STAGES });
    expect(markup).not.toContain('data-stage-reused');
    expect(markup).not.toContain('data-stage-elapsed="reused"');
    expect(row(markup, 'source_preparation')).toContain('data-stage-elapsed="0"');
  });
});
