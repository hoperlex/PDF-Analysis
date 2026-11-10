/**
 * `UI-A-60` / `R-151i`: «Запустить с этапа» on the run page, live (state, effects and presses).
 *
 * What is measured: the control is drawn for an ended run of the standard analysis to an expert and to nobody else; a stage
 * choice reads a fresh price bound to this run and that stage (and nothing is sent before it is consented to); one intent sends
 * one command with the exact consent and then opens the NEW run; a stage the server cannot take is shown as the server said it,
 * with no price to consent to; a stale digest needs a fresh reading and a new agreement.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const push = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }), usePathname: () => '/', useSearchParams: () => new URLSearchParams() }));
vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  getRunStatus: vi.fn(), estimateRunCost: vi.fn(), startRunFromStage: vi.fn(),
}));

import { ApiError, estimateRunCost, getRunStatus, queryKeys, startRunFromStage } from '@/shared/api';
import type { RunStatus } from '@/shared/api';
import { StartRunFromStageControl } from '@/features/start-run-from-stage';

import { newClient } from '../screens/harness';
import { PROJECT_UID, VERSION_UID, runStatus } from '../review/fixtures';
import { APPROVE_COST, COST_CONSENT, costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const NEW_RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8N';
let live: LiveRender | null = null;

const refusal = (reason: string, stage = 'page_geometry_extraction') => new ApiError(422, {
  contract_version: '1.49.0', error_code: 'analysis_input_invalid', message: 'x', correlation_id: 'refused', retryable: false,
  details: { stage_id: stage, reason },
}, 'refused');

function estimateFor(body: { version_uid: string; start_from_run_id?: string; start_stage_id?: string }, reused: string[], computed: string[]) {
  return { ...costEstimate({ version_uid: body.version_uid }), start_from_run_id: body.start_from_run_id,
    start_stage_id: body.start_stage_id, reused_stage_ids: reused, computed_stage_ids: computed };
}

beforeEach(() => {
  vi.resetAllMocks();
  push.mockReset();
  vi.mocked(getRunStatus).mockImplementation(async ({ path }) => ({ data: {
    ...runStatus(), run_id: path.run_id, state: 'published', version_uid: VERSION_UID } }) as never);
  vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: estimateFor(
    body as never, ['source_preparation', 'page_geometry_extraction', 'document_context_build'], ['text_analysis']) }) as never);
  vi.mocked(startRunFromStage).mockResolvedValue({ data: { ...runStatus(), run_id: NEW_RUN, project_uid: PROJECT_UID,
    started_from_run_id: RUN_ID, start_stage_id: 'text_analysis' } as RunStatus } as never);
});
afterEach(async () => { await live?.unmount(); live = null; });

async function mount(overrides: Partial<RunStatus> = {}, roles: string[] = ['expert']) {
  const client = newClient();
  client.setQueryData(queryKeys.runs.detail(RUN_ID as never), { ...runStatus(), run_id: RUN_ID, state: 'published', ...overrides });
  client.setQueryData(queryKeys.account.me(), { roles });
  live = await mountLive(createElement(QueryClientProvider, { client }, createElement(StartRunFromStageControl, { runId: RUN_ID })));
  return live;
}

async function settle(view: LiveRender, what = 'Загрузка: оценка стоимости запуска с этапа') {
  for (let tick = 0; tick < 20 && view.markup().includes(what); tick += 1) await view.settle(() => undefined);
  expect(view.markup()).not.toContain(what);
}

describe('who is offered it', () => {
  it('an expert, for an ended run', async () => {
    for (const state of ['published', 'partial', 'failed', 'cancelled'] as const) {
      const view = await mount({ state });
      expect(view.count('Запустить с этапа')).toBe(1);
      await view.unmount();
    }
  });

  it('nobody, for a run that is still going', async () => {
    for (const state of ['created', 'queued', 'running', 'validating'] as const) {
      const view = await mount({ state });
      expect(view.markup()).toBe('');
      await view.unmount();
    }
  });

  it('not a viewer', async () => {
    expect((await mount({}, ['viewer'])).markup()).toBe('');
  });
});

describe('the dialog', () => {
  it('reads the price only after a stage is chosen, bound to this run and that stage, and starts nothing without consent', async () => {
    const view = await mount();
    await view.press('Запустить с этапа');
    expect(estimateRunCost).not.toHaveBeenCalled();
    expect(view.markup()).toContain('Этот прогон не меняется.');
    expect(await view.press('Запустить')).toBe(false);

    await view.change('Этап', 'text_analysis');
    await settle(view);
    expect(estimateRunCost).toHaveBeenCalledWith(
      { body: { version_uid: VERSION_UID, start_from_run_id: RUN_ID, start_stage_id: 'text_analysis' } },
      expect.objectContaining({ signal: expect.anything() }));
    const markup = view.markup();
    expect(markup).toContain('Берутся из этого прогона: «Подготовка источника», «Извлечение геометрии страниц и блоков», «Построение контекста документа».');
    expect(markup).toContain('Будут выполнены: «Анализ текста». Оценка и согласие — для них.');
    expect(await view.press('Запустить')).toBe(false);
    expect(startRunFromStage).not.toHaveBeenCalled();
  });

  it('sends the exact consent under one key, retried under the same key, and opens the new run', async () => {
    vi.mocked(startRunFromStage).mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const view = await mount();
    await view.press('Запустить с этапа');
    await view.change('Этап', 'text_analysis');
    await settle(view);
    await view.check(APPROVE_COST, true);
    await view.press('Запустить');
    const first = vi.mocked(startRunFromStage).mock.calls[0]![0];
    expect(first).toEqual({ path: { run_id: RUN_ID }, body: { stage_id: 'text_analysis', cost_consent: COST_CONSENT }, idempotencyKey: expect.any(String) });
    expect(push).not.toHaveBeenCalled();
    expect(view.markup()).toContain('Прогон не запущен:');

    await view.press('Запустить');
    expect(vi.mocked(startRunFromStage).mock.calls[1]![0]).toEqual(first);
    expect(push).toHaveBeenCalledWith(`/projects/${PROJECT_UID}/runs/${NEW_RUN}`);
  });

  it('a stage the server cannot take is shown as it said, with no price to consent to', async () => {
    vi.mocked(estimateRunCost).mockRejectedValueOnce(refusal('source_stage_version_changed'));
    const view = await mount();
    await view.press('Запустить с этапа');
    await view.change('Этап', 'document_context_build');
    await settle(view);
    const markup = view.markup();
    expect(markup).toContain('data-start-from-stage-refusal');
    expect(markup).toContain('«Извлечение геометрии страниц и блоков» получен более старой версией этапа');
    expect(markup).not.toContain('data-cost-approval');
    expect(await view.press('Запустить')).toBe(false);
    expect(startRunFromStage).not.toHaveBeenCalled();
  });

  it('a refusal at the start itself is shown as it said and the dialog stays open', async () => {
    vi.mocked(startRunFromStage).mockRejectedValueOnce(refusal('source_artifact_unavailable', 'source_preparation'));
    const view = await mount();
    await view.press('Запустить с этапа');
    await view.change('Этап', 'text_analysis');
    await settle(view);
    await view.check(APPROVE_COST, true);
    await view.press('Запустить');
    expect(view.markup()).toContain('Сохранённый результат этапа «Подготовка источника» исходного прогона недоступен.');
    expect(push).not.toHaveBeenCalled();
    expect(view.markup()).toContain('data-run-start-from-stage="dialog"');
  });

  it('a stale digest needs a fresh reading and a new agreement, under a new key', async () => {
    vi.mocked(startRunFromStage).mockRejectedValueOnce(new ApiError(409, { contract_version: '1.49.0',
      error_code: 'conflict', message: 'stale', correlation_id: 'stale', retryable: false,
      details: { conflict_reason: 'run_cost_estimate_stale' } }, 'stale'));
    const view = await mount();
    await view.press('Запустить с этапа');
    await view.change('Этап', 'text_analysis');
    await settle(view);
    await view.check(APPROVE_COST, true);
    await view.press('Запустить');
    expect(view.markup()).toContain('Оценка стоимости устарела.');
    expect(await view.press('Запустить')).toBe(false);
    await view.press('Обновить оценку стоимости');
    await settle(view);
    expect(estimateRunCost).toHaveBeenCalledTimes(2);
    await view.check(APPROVE_COST, true);
    await view.press('Запустить');
    expect(vi.mocked(startRunFromStage).mock.calls[1]![0].idempotencyKey)
      .not.toBe(vi.mocked(startRunFromStage).mock.calls[0]![0].idempotencyKey);
  });

  it('choosing another stage reads another price and cancel closes it without sending anything', async () => {
    const view = await mount();
    await view.press('Запустить с этапа');
    await view.change('Этап', 'text_analysis');
    await settle(view);
    await view.change('Этап', 'page_geometry_extraction');
    await settle(view);
    expect(vi.mocked(estimateRunCost).mock.calls.map((call) => (call[0].body as { start_stage_id?: string }).start_stage_id))
      .toEqual(['text_analysis', 'page_geometry_extraction']);
    await view.press('Отмена');
    expect(view.count('Запустить с этапа')).toBe(1);
    expect(startRunFromStage).not.toHaveBeenCalled();
  });
});
