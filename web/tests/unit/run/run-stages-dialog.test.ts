/**
 * `RUN-STAGES-WEB-01` — «Этапы анализа раздела» says, for each chip, the model of every plan cell with its effort, answer limit
 * and (to the reader who may see it) the server and the access, and then the facts: state, calls, tokens, cost, times, error.
 *
 * Rendered over a stages answer the way `getRunStages` states it, so the words a reader sees are the words asserted. Each state
 * the window can be in has a case: the plan the run froze (a blocks ensemble), a run that froze none, the viewer, a chip taken
 * from an earlier run, and the reading before the answer or after its failure, which draw what the window drew before the answer
 * existed. The rail's line is the same answer read through `RunProgress`.
 */

import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import type { RunStage, RunStageCell, RunStageFacts, RunStages, RunStatus } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { DIGIT_GROUP_SEPARATOR, runStagesKey } from '@/entities/audit-run';
import type { RunStagesView } from '@/entities/audit-run';
import { RunProgress } from '@/widgets/run-progress';

import { PROJECT_UID, RUN_ID, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';
import { runDialog } from './run-dialog-fixture';

const G = DIGIT_GROUP_SEPARATOR;

const FACTS: RunStageFacts = {
  state: 'done', calls_succeeded: 0, calls_failed: 0, calls_retried: 0, input_tokens: 0, output_tokens: 0,
  subscription_input_tokens: 0, subscription_output_tokens: 0, cost_micros: 0,
};
const cell = (role: RunStageCell['role'], model_id: string, extra: Partial<RunStageCell> = {}): RunStageCell => ({
  role, model_id, effort: 'medium', max_output_tokens: 6000, timeout_seconds: 900, ...extra,
});
const stage = (chip: RunStage['chip'], plan: RunStageCell[], facts: Partial<RunStageFacts> = {}): RunStage => ({
  chip, stage_ids: ['x'], plan, facts: { ...FACTS, ...facts },
});
const stages = (items: RunStage[], plan_source: RunStages['plan_source'] = 'stage_plan', state: RunStages['state'] = 'running'): RunStagesView => ({
  phase: 'read', stages: { run_id: RUN_ID, state, plan_source, items },
});

/** A run that has done its preparation and its text analysis and is on the blocks. */
const RUNNING: Partial<RunStatus> = {
  state: 'running', terminal_at: null,
  stages: [
    { stage_id: 'source_preparation', status: 'succeeded', error_code: null },
    { stage_id: 'page_geometry_extraction', status: 'succeeded', error_code: null },
    { stage_id: 'document_context_build', status: 'succeeded', error_code: null },
    { stage_id: 'text_analysis', status: 'succeeded', error_code: null },
    { stage_id: 'block_analysis', status: 'succeeded', error_code: null },
  ],
};

const BLOCKS_ENSEMBLE = stage('blocks', [
  cell('leg1', 'claude-opus-5-5', { cell_key: 'blocks:leg1', access: 'subscription', server: 'adm1.hlab.kz' }),
  cell('judge', 'claude-sonnet-5-5', { cell_key: 'blocks:judge', access: 'api', max_output_tokens: 12000 }),
], {
  state: 'running', calls_succeeded: 12, calls_failed: 1, calls_retried: 2, input_tokens: 102400, output_tokens: 18800,
  subscription_input_tokens: 90000, subscription_output_tokens: 15000, cost_micros: 412000, started_at: '2026-11-10T09:06:41Z',
  planned: 40, completed: 12,
});

const dialog = (view: RunStagesView | undefined, over: Partial<RunStatus> = {}, selected: Parameters<typeof runDialog>[1] = { selected: 'blocks' }) =>
  runDialog(runStatus({ ...RUNNING, ...over }), { ...selected, ...(view === undefined ? {} : { stages: view }) });

describe('the plan of a chip with a blocks ensemble (a run that froze its stage plan)', () => {
  const markup = dialog(stages([BLOCKS_ENSEMBLE]));

  it('has one line for each plan cell, named by its part, in the order the answer gives them', () => {
    expect(markup.match(/data-plan-row="cell"/g)).toHaveLength(2);
    expect(markup).toMatch(/data-plan-cell="blocks:leg1"[^>]*data-stage-role="leg1"/);
    expect(markup).toMatch(/data-plan-cell="blocks:judge"[^>]*data-stage-role="judge"/);
    expect(markup.indexOf('Первая ветка')).toBeLessThan(markup.indexOf('Судья'));
    expect(markup).not.toContain('data-plan-row="model"');
    expect(markup).toContain('data-plan-source="stage_plan"');
  });

  it('says the model, the effort and the answer limit of each cell, and the server and access of the ones that have them', () => {
    // The short name only; the pin is the tooltip, never a second chip beside it.
    expect(markup).toContain('<strong title="claude-opus-5-5">Opus 5.5</strong> · усилие');
    expect(markup).toContain('<strong title="claude-sonnet-5-5">Sonnet 5.5</strong> · усилие');
    expect(markup).not.toContain('<code');
    expect(markup).toContain(`усилие: среднее · ответ до 6${G}000 токенов · сервер adm1.hlab.kz · по подписке`);
    // The judge is bound to no server yet: its access is said and the server is said not to be chosen, nothing is invented.
    expect(markup).toContain(`ответ до 12${G}000 токенов · по ключу API · сервер не назначен`);
  });

  it('says the facts: state, batches, calls, tokens with the subscription part, cost, start and the end not yet reached', () => {
    expect(markup).toMatch(/data-fact-row="state"[^>]*>[\s\S]*?<td[^>]*>идёт<\/td>/);
    expect(markup).toMatch(/data-fact-row="progress"[\s\S]*?12 из 40/);
    expect(markup).toContain('успешно 12 · с ошибкой 1 · повторов 2');
    expect(markup).toContain(`входных 102${G}400 · выходных 18${G}800 · по подписке: входных 90${G}000 · выходных 15${G}000`);
    expect(markup).toContain('0.412000 единиц валюты провайдера');
    expect(markup).toMatch(/data-fact-row="started"[\s\S]*?2026-11-10 09:06:41 UTC/);
    expect(markup).toMatch(/data-fact-row="finished"[\s\S]*?<td>—<\/td>/);
    // The note that the server does not say time and tokens is gone: it does.
    expect(markup).not.toContain('Время и токены по этому этапу сервер пока не передаёт.');
  });
});

describe('the reader who may not see the server', () => {
  it('is shown the model and the effort of each cell and no server, no access and no «не назначен»', () => {
    const markup = dialog(stages([BLOCKS_ENSEMBLE]), {}, { selected: 'blocks', showServer: false });
    expect(markup.match(/data-plan-row="cell"/g)).toHaveLength(2);
    expect(markup).toContain('Opus 5.5');
    expect(markup).toContain(`усилие: среднее · ответ до 6${G}000 токенов</td>`);
    for (const hidden of ['adm1.hlab.kz', 'сервер', 'по ключу API', 'не назначен']) expect(markup, hidden).not.toContain(hidden);
  });
});

describe('a run that froze no stage plan (`run_binding`)', () => {
  const run = stages([stage('text', [{ role: 'main', model_id: 'claude-sonnet-5-5' }], { calls_succeeded: 3, input_tokens: 30100, output_tokens: 4200 })], 'run_binding', 'published');

  it('keeps the one line, «Модель (прогона)», and draws no cell lines', () => {
    const markup = dialog(run, { state: 'published', executor: { connection_id: 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', display_name: 'Основной', pin_id: 'claude-sonnet-5-5' } }, { selected: 'text' });
    expect(markup).toContain('data-plan-row="model"');
    expect(markup).toContain('Модель (прогона)');
    expect(markup).not.toContain('data-plan-row="cell"');
    expect(markup).toContain('data-plan-source="run_binding"');
    // The facts are still the answer's: they do not depend on where the plan came from.
    expect(markup).toContain(`входных 30${G}100 · выходных 4${G}200`);
  });
});

describe('before the answer, and when it failed: what the window drew before it existed', () => {
  const today = (view: RunStagesView | undefined) => dialog(view, {}, { selected: 'text' });

  it.each([['absent', undefined], ['loading', { phase: 'loading' } as RunStagesView]])('%s: the run\'s model line, the chip\'s own facts, no cell and no invented figure', (_name, view) => {
    const markup = today(view);
    expect(markup).toContain('data-plan-row="model"');
    expect(markup).toContain('Модель (прогона)');
    expect(markup).toContain('data-fact-row="state"');
    for (const absent of ['data-plan-row="cell"', 'data-fact-row="calls"', 'data-fact-row="tokens"', 'data-fact-row="cost"', 'data-run-stages-failed']) {
      expect(markup, absent).not.toContain(absent);
    }
    expect(markup).not.toContain('data-plan-source');
  });

  it('error: the same, and a line that says the models by stage could not be read', () => {
    const markup = today({ phase: 'error' });
    expect(markup).toContain('data-run-stages-failed');
    expect(markup).toContain('Модели по этапам прочитать не удалось');
    expect(markup).toContain('data-plan-row="model"');
    expect(markup).not.toContain('data-plan-row="cell"');
  });

  it('a chip the answer does not list is drawn as before, while the chips it does list are drawn from it', () => {
    const view = stages([BLOCKS_ENSEMBLE]);
    const unlisted = dialog(view, {}, { selected: 'text' });
    expect(unlisted).toContain('data-plan-row="model"');
    expect(unlisted).not.toContain('data-plan-source');
    expect(dialog(view, {}, { selected: 'blocks' })).toContain('data-plan-row="cell"');
  });
});

describe('the facts of other kinds of chip', () => {
  it('a chip that calls no model has no model line, and no calls, tokens or cost', () => {
    const markup = dialog(stages([stage('preparation', [], { state: 'done', started_at: '2026-11-10T09:00:03Z', finished_at: '2026-11-10T09:01:12Z' })]), {}, { selected: 'preparation' });
    expect(markup).toContain('этап не вызывает модель');
    expect(markup).not.toContain('data-plan-row="cell"');
    for (const absent of ['data-fact-row="calls"', 'data-fact-row="tokens"', 'data-fact-row="cost"']) expect(markup, absent).not.toContain(absent);
    expect(markup).toMatch(/data-fact-row="elapsed"[\s\S]*?1 мин 9 с/);
  });

  it('a model chip that has made no call says zeros, and states no cost it does not have', () => {
    const markup = dialog(stages([stage('text', [cell('main', 'claude-sonnet-5-5')], { state: 'pending' })]), {}, { selected: 'text' });
    expect(markup).toContain('успешно 0 · с ошибкой 0 · повторов 0');
    expect(markup).toContain('входных 0 · выходных 0');
    expect(markup).not.toContain('data-fact-row="cost"');
    expect(markup).not.toContain('по подписке:');
  });

  it('a chip served wholly by a subscription says it is not priced, never a zero', () => {
    const markup = dialog(stages([stage('text', [cell('main', 'claude-sonnet-5-5')], {
      calls_succeeded: 5, input_tokens: 61240, output_tokens: 9310, subscription_input_tokens: 61240, subscription_output_tokens: 9310,
    })]), {}, { selected: 'text' });
    expect(markup).toContain('по подписке, не считается');
    expect(markup).not.toContain('0.000000');
  });

  it('a metered chip states the price as the integer millionths are, with no float in between', () => {
    const markup = dialog(stages([stage('text', [cell('main', 'claude-sonnet-5-5')], { calls_succeeded: 1, input_tokens: 10, output_tokens: 5, cost_micros: 1 })]), {}, { selected: 'text' });
    expect(markup).toContain('0.000001 единиц валюты провайдера');
  });

  it('a failed chip says its last error code, and a procedure that did not complete says why', () => {
    const failed = stage('text', [cell('main', 'claude-sonnet-5-5')], { state: 'failed', last_error_code: 'dependency_unavailable', reason: 'corpus_unavailable', calls_failed: 2 });
    const markup = dialog(stages([failed]), {}, { selected: 'text' });
    expect(markup).toMatch(/data-fact-row="error"[\s\S]*?<code>dependency_unavailable<\/code>/);
    // The reason is said in the plan list's own words, never as the bare code.
    expect(markup).toMatch(/data-fact-row="reason"[\s\S]*?<td>В этом прогоне нет доступного нормативного корпуса\. Проверка ссылок не выполнена\.<\/td>/);
    expect(markup).not.toContain('<code>corpus_unavailable</code>');
    expect(markup).toMatch(/data-fact-row="state"[\s\S]*?отказ/);
    const quiet = dialog(stages([stage('text', [cell('main', 'claude-sonnet-5-5')])]), {}, { selected: 'text' });
    expect(quiet).not.toContain('data-fact-row="error"');
    expect(quiet).not.toContain('data-fact-row="reason"');
  });

  it('a chip taken from an earlier run says so, and has no duration of its own', () => {
    const reused = stage('text', [cell('main', 'claude-sonnet-5-5')], {
      state: 'done', reused_from_run_id: 'run_01M2545JSD15ETSNNV904X991L', started_at: '2026-11-09T11:00:00Z', calls_succeeded: 3,
    });
    const markup = dialog(stages([reused]), {}, { selected: 'text' });
    expect(markup).toContain('выполнен · взят из исходного прогона');
    expect(markup).toMatch(/data-fact-row="elapsed"[\s\S]*?<td>из прогона<\/td>/);
    const own = dialog(stages([stage('text', [cell('main', 'claude-sonnet-5-5')], { started_at: '2026-11-10T09:00:00Z', finished_at: '2026-11-10T09:00:42Z' })]), {}, { selected: 'text' });
    expect(own).not.toContain('взят из исходного прогона');
    expect(own).toMatch(/data-fact-row="elapsed"[\s\S]*?<td>42 с<\/td>/);
  });
});

/**
 * The owner's minimisation priority: the right side says a thing once. The executor is the plan's model and server (no line of its
 * own above the table), the model is its short name, the table of code stages is for a chip that has several, and the one-line list of
 * procedures that only repeats the chip's own state is left out once the stages are read.
 */
describe('nothing is said twice', () => {
  const EXECUTOR = { connection_id: 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', display_name: 'adm1.hlab.kz', pin_id: 'claude-opus-5-5' };
  const PROCEDURES = [{ id: 'block_analysis', title: 'Анализ блоков', status: 'completed' as const, reason: null, dependency: null, errorCode: null }];

  it('has no «Исполнитель» line above «План + Факт», with or without the stages, and the server is in the plan', () => {
    for (const view of [undefined, stages([BLOCKS_ENSEMBLE]), { phase: 'error' } as RunStagesView]) {
      const markup = dialog(view, { executor: EXECUTOR, state: 'published', terminal_at: '2026-09-10T08:04:00.000Z' }, { selected: 'blocks' });
      expect(markup).not.toContain('Исполнитель');
      expect(markup).not.toContain('data-run-executor');
      expect(markup).not.toContain('<code');
    }
    const fallback = dialog(undefined, { executor: EXECUTOR }, { selected: 'text' });
    expect(fallback).toContain('<strong title="claude-opus-5-5">Opus 5.5</strong>');
    expect(fallback).toMatch(/data-plan-row="server"[\s\S]*?adm1\.hlab\.kz/);
  });

  it('keeps the preset line, which is nowhere else', () => {
    const preset = { preset_id: 'pre_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', revision_no: 2, name: 'Быстрый черновик' } as never;
    expect(dialog(undefined, { preset }, { selected: 'text' })).toContain('<dt>Пресет</dt>');
  });

  it('draws the table of code stages only for a chip that has two or more', () => {
    const several = dialog(undefined, {}, { selected: 'preparation' });
    expect(several).toContain('Подробности этапов');
    expect(several).toContain('data-stage-id="source_preparation"');
    for (const selected of ['text', 'blocks'] as const) {
      const one = dialog(undefined, {}, { selected });
      expect(one, selected).not.toContain('Подробности этапов');
      expect(one, selected).not.toContain('data-stage-id=');
      expect(one, selected).toContain('data-fact-row="state"');
    }
  });

  it('leaves out the one-line procedure list where the read stages say the same, and keeps it where they are not read', () => {
    const read = dialog(stages([BLOCKS_ENSEMBLE]), {}, { selected: 'blocks', procedures: PROCEDURES });
    expect(read).not.toContain('data-extended-procedure-plan');
    for (const view of [undefined, { phase: 'loading' } as RunStagesView, { phase: 'error' } as RunStagesView]) {
      const markup = dialog(view, {}, { selected: 'blocks', procedures: PROCEDURES });
      expect(markup).toContain('data-extended-procedure-plan');
      expect(markup).toContain('data-extended-procedure="block_analysis"');
    }
  });

  it('keeps «Как устроен этап» collapsed', () => {
    const markup = dialog(stages([BLOCKS_ENSEMBLE]), {}, { selected: 'blocks' });
    expect(markup).toMatch(/<details[^>]*data-stage-algorithm="blocks"[^>]*><summary>Как устроен этап<\/summary>/);
    expect(markup).not.toMatch(/<details[^>]*data-stage-algorithm[^>]*open/);
  });
});

describe('the rail: one short line under a chip, from the same answer', () => {
  function rail(view: RunStages | null, over: Partial<RunStatus> = {}): string {
    const status = runStatus({ ...RUNNING, ...over });
    const client = newClient();
    client.setQueryData(queryKeys.runs.detail(status.run_id), status);
    if (view !== null) client.setQueryData(runStagesKey(RUN_ID), view);
    return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }));
  }
  const lineOf = (markup: string, chip: string) => markup.match(new RegExp(`data-run-chip="${chip}"[\\s\\S]*?</button>`))?.[0] ?? '';
  const read = (view: RunStagesView) => (view.phase === 'read' ? view.stages : null);

  it('names the one model of a chip, «2 модели» for an ensemble, and nothing for a chip that calls none', () => {
    const answer = read(stages([
      stage('preparation', []),
      stage('text', [cell('main', 'claude-sonnet-5-5')]),
      BLOCKS_ENSEMBLE,
    ]));
    const markup = rail(answer);
    expect(lineOf(markup, 'text')).toContain('>Sonnet 5.5</span>');
    expect(lineOf(markup, 'blocks')).toContain('>2 модели</span>');
    expect(lineOf(markup, 'blocks')).toContain('title="Opus 5.5 · Sonnet 5.5"');
    expect(lineOf(markup, 'preparation')).not.toContain('data-chip-model');
    // One line per chip and no other new text on the rail: the chip keeps its name, its state and its time.
    expect(markup.match(/data-chip-model/g)).toHaveLength(2);
  });

  it('is the run\'s own model until the answer is read, as before, and is not drawn for a chip ruled out', () => {
    const executor = { connection_id: 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', display_name: 'Основной', pin_id: 'claude-sonnet-5-5' };
    const before = rail(null, { executor });
    expect(lineOf(before, 'text')).toContain('>Sonnet 5.5</span>');
    expect(lineOf(before, 'blocks')).toContain('>Sonnet 5.5</span>');
    expect(lineOf(before, 'preparation')).not.toContain('data-chip-model');
    // Once the answer is read the chip says its own model, not the run's.
    const after = rail(read(stages([stage('text', [cell('main', 'gpt-6-sol')]), BLOCKS_ENSEMBLE])), { executor });
    expect(lineOf(after, 'text')).toContain('>GPT 6 sol</span>');
    expect(lineOf(after, 'text')).not.toContain('Sonnet 5.5');
  });

  it('draws no line on a chip the answer lists without a model, rather than the run\'s model', () => {
    const executor = { connection_id: 'exc_01J9ZQ8K7NHVXW3T2R5M6P4Q8F', display_name: 'Основной', pin_id: 'claude-sonnet-5-5' };
    const markup = rail(read(stages([stage('text', [])])), { executor });
    expect(lineOf(markup, 'text')).not.toContain('data-chip-model');
    expect(lineOf(markup, 'blocks')).not.toContain('data-chip-model');
  });
});
