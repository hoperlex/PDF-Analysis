/**
 * `UI-A-60` / `R-151i` and `RUN-RESTART-01` / `R-155a`: a run started from a stage, or restarted from a chip, says so on its page, links the
 * run it took the first stages from, and marks those stages in the rail. A run started any other way shows none of it. The page of a run a
 * restart replaced says «Прогон перезапущен» and leads to the new run; a run the silence watchdog stopped says so in a sentence.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { queryKeys } from '@/shared/api';
import type { RunStatus } from '@/shared/api';
import { RunProgress } from '@/widgets/run-progress';
import { startedFrom } from '@/widgets/run-progress/model/started-from';

import { PROJECT_UID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';
import { runDialog } from '../run/run-dialog-fixture';

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
    expect(from?.kind).toBe('stage');
    expect(from?.kind === 'stage' ? from.ordinal : null).toBe(3);
    expect([...(from?.reusedStageIds ?? [])]).toEqual(['source_preparation', 'page_geometry_extraction']);
    expect(startedFrom({ started_from_run_id: SOURCE as never, start_stage_id: 'text_analysis' })?.reusedStageIds.size).toBe(3);
  });

  it('names the chips before the restart point as taken, for a restart', () => {
    const from = startedFrom({ started_from_run_id: SOURCE as never, restart_point: 'blocks' });
    expect(from?.kind).toBe('restart');
    expect(from?.kind === 'restart' ? from.point : null).toBe('blocks');
    expect([...(from?.reusedStageIds ?? [])]).toEqual([
      'source_preparation', 'page_geometry_extraction', 'document_context_build', 'text_analysis',
    ]);
    expect(startedFrom({ started_from_run_id: SOURCE as never, restart_point: 'preparation' })?.reusedStageIds.size).toBe(0);
  });

  it('is nothing for a run that was not started from a stage, or whose pair is broken', () => {
    expect(startedFrom({})).toBeNull();
    expect(startedFrom({ started_from_run_id: SOURCE as never })).toBeNull();
    expect(startedFrom({ start_stage_id: 'text_analysis' })).toBeNull();
    expect(startedFrom({ started_from_run_id: SOURCE as never, start_stage_id: 'block_analysis' })).toBeNull();
    expect(startedFrom({ restart_point: 'text' })).toBeNull();
  });
});

describe('the run page', () => {
  const FROM = { started_from_run_id: SOURCE as never, start_stage_id: 'text_analysis' as const };

  it('says the stage and links the earlier run, in the caption under the head', () => {
    const markup = page(FROM);
    expect(markup).toContain('data-run-started-from-note="text_analysis"');
    expect(markup).toContain('Запущен с этапа 4 «Анализ текста» из прогона');
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${SOURCE}"`);
    expect(markup).toContain(`data-run-started-from="${SOURCE}"`);
    // The caption is the one place; the facts no longer repeat it (`RUN-SCREEN-01a`).
    expect(markup).not.toContain('<dt>Запущен с этапа</dt>');
  });

  it('marks a chip as taken from the earlier run only when every stage of it was', () => {
    // Started from «Анализ текста»: the three stages of «Подготовка» are the earlier run\'s, the text stage is computed.
    const markup = page(FROM);
    expect(markup.match(/data-chip-reused/g)).toHaveLength(1);
    expect(markup).toMatch(/data-run-chip="preparation"[^>]*data-chip-reused/);
    expect(markup).not.toMatch(/data-run-chip="text"[^>]*data-chip-reused/);
    expect(markup).toMatch(/data-chip-took="из прогона"/);
    // The time sits on the state's row, opposite it (owner hotfix 2026-11-11), not on a line of its own: one wrapper holds the state and
    // the time and closes right after the time. On the old markup the state followed the name directly and the time ended the button.
    expect(markup).toMatch(/<span[^>]*><span[^>]*>[^<]+<\/span><span[^>]*data-chip-took="из прогона"[^>]*>из прогона<\/span><\/span>/);
    // Started from the third stage: two of the three preparation stages are taken, so the chip is not.
    const partly = page({ ...FROM, start_stage_id: 'document_context_build' });
    expect(partly).not.toContain('data-chip-reused');
  });

  it('shows none of it for a run started from a version', () => {
    const markup = page({});
    expect(markup).not.toContain('data-run-started-from');
    expect(markup).not.toContain('data-pipeline-reused');
    expect(markup).not.toContain('Запущен с этапа');
  });
});

describe('the run page of a restarted run', () => {
  const RESTARTED = { started_from_run_id: SOURCE as never, restart_point: 'blocks' as const };

  it('says the chip by its short name and links the run it was restarted from, in one line', () => {
    const markup = page(RESTARTED);
    expect(markup).toContain('data-run-restarted=""');
    expect(markup).toContain('data-run-started-from-note="blocks"');
    expect(markup).toMatch(/Перезапущен с этапа «Блоки» из прогона(?:<!-- -->)? (?:<!-- -->)?<a href="\/projects\/[^"]+\/runs\/run_01J9ZQ8K7NHVXW3T2R5M6P4Q8Z"/);
    expect(markup).toContain(`data-run-started-from="${SOURCE}"`);
    expect(markup).not.toContain('Запущен с этапа');
  });

  it('marks the chips taken from the source in the rail, and only those', () => {
    const markup = page({
      ...RESTARTED,
      stages: ['source_preparation', 'page_geometry_extraction', 'document_context_build', 'text_analysis'].map((stage_id) => ({
        stage_id: stage_id as never, status: 'succeeded' as const, error_code: null,
      })),
    });
    expect(markup).toMatch(/data-run-chip="preparation"[^>]*data-chip-reused/);
    expect(markup).toMatch(/data-run-chip="text"[^>]*data-chip-reused/);
  });

  it('says why a restart that could not replay a saved reply stopped, before any paid call', () => {
    const markup = page({
      ...RESTARTED, state: 'failed', terminal_reason: 'analysis_input_invalid',
      terminal_detail: { stage_id: 'norm_verification', reason: 'restart_request_changed' },
    });
    expect(markup).toContain('data-restart-refusal=""');
    expect(markup).toContain('Поиск норм дал другой результат');
    expect(markup).toContain('Перезапустите с «Норм».');
  });
});

describe('the run page of a run a restart replaced', () => {
  const NEW = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8N';

  it('says «Прогон перезапущен» at the top, with the way to the new run', () => {
    const markup = page({ state: 'partial', degradation_set: ['text_analysis'], replaced_by_run_id: NEW as never });
    expect(markup).toContain(`data-run-replaced="${NEW}"`);
    expect(markup).toContain('>Прогон перезапущен<');
    expect(markup).toContain(`href="/projects/${PROJECT_UID}/runs/${NEW}"`);
    expect(markup).toContain('Открыть новый прогон');
    // The notice comes before the head.
    expect(markup.indexOf('data-run-replaced=')).toBeLessThan(markup.indexOf('data-run-head'));
  });

  it('offers none of the actions of a live run: no review, no findings tile', () => {
    const base = { state: 'published' as const, published_finding_count: 3 };
    expect(page(base)).toContain('Разобрать замечания');
    expect(page(base)).toContain('data-run-findings-tile');
    const markup = page({ ...base, replaced_by_run_id: NEW as never });
    expect(markup).not.toContain('Разобрать замечания');
    expect(markup).not.toContain('data-run-findings-tile');
    expect(markup).not.toContain('в Разбор');
  });

  it('is not drawn for a run nobody replaced', () => {
    expect(page({ state: 'failed' })).not.toContain('data-run-replaced');
  });
});

describe('the run page of a run the silence watchdog stopped', () => {
  const STALLED = { state: 'failed' as const, interrupted_reason: 'attempt_stalled' };

  it('says it in a sentence, and names the chip when the run says which', () => {
    const plain = page(STALLED);
    expect(plain).toContain('Прогон остановлен: нет признаков работы 30 минут.');
    expect(plain).not.toContain('attempt_stalled</');
    const named = page({ ...STALLED, terminal_detail: { stage_id: 'block_analysis' } });
    expect(named).toContain('Прогон остановлен: нет признаков работы 30 минут на этапе «Блоки».');
  });

  it('keeps printing another reason as the server wrote it', () => {
    expect(page({ state: 'failed', interrupted_reason: 'attempt_budget_exhausted' })).toContain('Прогон был прерван и сверен: attempt_budget_exhausted.');
  });
});

/**
 * `D-412` (lane J4): the details table read «0 ms» for a stage taken by reference -- its row has one instant for start and finish,
 * the moment of the reuse -- where the rail already read «из прогона». The duration cell now says where the result came from.
 */
describe('the stage table of a run started from a stage, in «Этапы анализа раздела»', () => {
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
  const dialog = (over: Partial<RunStatus>, selected: 'preparation' | 'text') =>
    runDialog(runStatus({ state: 'published', ...over }), { selected });
  const row = (markup: string, stageId: string): string => {
    const found = new RegExp(`<tr data-stage-id="${stageId}"[^>]*>.*?</tr>`, 's').exec(markup);
    if (found === null) throw new Error(`no row for ${stageId}`);
    return found[0];
  };

  it('says «из прогона» for each stage taken by reference, and no duration of nothing', () => {
    const markup = dialog({ ...FROM, stages: STAGES }, 'preparation');
    for (const taken of ['source_preparation', 'page_geometry_extraction', 'document_context_build']) {
      const cells = row(markup, taken);
      expect(cells).toContain('data-stage-reused=""');
      expect(cells).toMatch(/<td[^>]*data-stage-elapsed="reused"[^>]*>\s*из прогона\s*<\/td>/);
      expect(cells).not.toContain('0 ms');
      expect(cells).not.toContain('data-stage-elapsed="0"');
    }
    expect(markup.match(/data-stage-elapsed="reused"/g)).toHaveLength(3);
    // The chip itself was taken whole, so it has no duration of its own to state.
    expect(markup).toContain('<th scope="row">Длительность</th><td>из прогона</td>');
  });

  it('keeps the measured duration of the stage this run computed', () => {
    // «Текст» has one code stage, so the window draws no table of stages for it (`RUN-STAGES-WEB-01`): the measured duration is the
    // chip's own fact, and it is not «из прогона».
    const markup = dialog({ ...FROM, stages: STAGES }, 'text');
    expect(markup).not.toContain('data-stage-id=');
    const duration = /data-fact-row="elapsed"[^>]*><th scope="row">Длительность<\/th><td>([^<]*)<\/td>/.exec(markup)?.[1];
    expect(duration).toBe('2,5 с');
    expect(markup).not.toContain('data-stage-reused');
  });

  it('marks only the stages before the start stage when the run started from an earlier one', () => {
    const markup = dialog({ ...FROM, start_stage_id: 'document_context_build', stages: STAGES }, 'preparation');
    expect(markup.match(/data-stage-elapsed="reused"/g)).toHaveLength(2);
    expect(row(markup, 'document_context_build')).not.toContain('data-stage-reused');
  });

  it('is unchanged for a run that was not started from a stage', () => {
    const markup = dialog({ stages: STAGES }, 'preparation');
    expect(markup).not.toContain('data-stage-reused');
    expect(markup).not.toContain('data-stage-elapsed="reused"');
    expect(row(markup, 'source_preparation')).toContain('data-stage-elapsed="0"');
  });
});
