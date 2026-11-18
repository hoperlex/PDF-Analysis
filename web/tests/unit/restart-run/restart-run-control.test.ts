/**
 * `RUN-RESTART-01` / `R-155a`: «Перезапустить с этого этапа» in the dialog of a chip, live (state, effects and presses).
 *
 * What is measured: the button is drawn for a run that ended without a clean result to an expert and to nobody else; pressing it reads
 * a fresh price bound to this run and this chip (and nothing is sent before it is consented to); the confirmation says which chips are
 * taken and which are computed, what happens to the old run, and the norms warning from the critic on; one intent sends one command with
 * the exact consent and then opens the NEW run; a refusal is shown as a sentence and the dialog stays open; a stale digest reads the price
 * again and needs a new agreement.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const push = vi.fn();
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }), usePathname: () => '/', useSearchParams: () => new URLSearchParams() }));
vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  getRunStatus: vi.fn(), estimateRunCost: vi.fn(), restartRun: vi.fn(),
}));

import { ApiError, estimateRunCost, getRunStatus, queryKeys, restartRun } from '@/shared/api';
import type { RestartPoint, RunStatus } from '@/shared/api';
import { RestartRunControl, restartPointOf } from '@/features/restart-run';

import { newClient } from '../screens/harness';
import { PROJECT_UID, VERSION_UID, runStatus } from '../review/fixtures';
import { APPROVE_COST, COST_CONSENT, costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const NEW_RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8N';
const LOADING = 'Загрузка: оценка стоимости перезапуска';
let live: LiveRender | null = null;

const invalid = (details: Record<string, string>) => new ApiError(422, {
  contract_version: '1.60.0', error_code: 'analysis_input_invalid', message: 'x', correlation_id: 'refused', retryable: false, details,
}, 'refused');

const ALL: readonly RestartPoint[] = ['preparation', 'text', 'blocks', 'cross_check', 'merge', 'norms', 'review', 'correction'];

/** The price the server gives for the point the request names: the earlier chips taken, that one and the later ones computed. */
function estimateFor(body: { version_uid: string; start_from_run_id?: string; restart_point?: string }, point: RestartPoint = body.restart_point as RestartPoint) {
  const at = ALL.indexOf(point);
  const all = [...ALL];
  return { ...costEstimate({ version_uid: body.version_uid }), start_from_run_id: body.start_from_run_id,
    restart_point: body.restart_point, reused_restart_points: all.slice(0, at), computed_restart_points: all.slice(at) };
}

beforeEach(() => {
  vi.resetAllMocks();
  push.mockReset();
  vi.mocked(getRunStatus).mockImplementation(async ({ path }) => ({ data: {
    ...runStatus(), run_id: path.run_id, state: 'failed', version_uid: VERSION_UID } }) as never);
  vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: estimateFor(body as never) }) as never);
  vi.mocked(restartRun).mockResolvedValue({ data: { ...runStatus(), run_id: NEW_RUN, project_uid: PROJECT_UID, state: 'queued',
    started_from_run_id: RUN_ID, restart_point: 'blocks' } as RunStatus } as never);
});
afterEach(async () => { await live?.unmount(); live = null; });

async function mount(overrides: Partial<RunStatus> = {}, roles: string[] = ['expert'], point: RestartPoint = 'blocks') {
  const client = newClient();
  client.setQueryData(queryKeys.account.me(), { roles });
  const run = { ...runStatus(), run_id: RUN_ID, state: 'failed' as const, ...overrides };
  live = await mountLive(createElement(QueryClientProvider, { client }, createElement(RestartRunControl, { run, point })));
  return live;
}

async function settle(view: LiveRender, what = LOADING) {
  for (let tick = 0; tick < 20 && view.markup().includes(what); tick += 1) await view.settle(() => undefined);
  expect(view.markup()).not.toContain(what);
}

describe('who is offered it', () => {
  it('an expert, for a run that ended without a clean result', async () => {
    for (const state of ['partial', 'failed', 'cancelled'] as const) {
      const view = await mount({ state });
      expect(view.count('Перезапустить с этого этапа')).toBe(1);
      await view.unmount();
    }
  });

  it('an administrator too', async () => {
    expect((await mount({}, ['admin'])).count('Перезапустить с этого этапа')).toBe(1);
  });

  it('nobody, for a published run and for a run that is still going', async () => {
    for (const state of ['published', 'created', 'queued', 'running', 'validating'] as const) {
      const view = await mount({ state });
      expect(view.markup(), state).toBe('');
      await view.unmount();
    }
  });

  it('nobody, for a run a restart has replaced', async () => {
    expect((await mount({ replaced_by_run_id: NEW_RUN as never })).markup()).toBe('');
  });

  it('not a viewer', async () => {
    expect((await mount({}, ['viewer'])).markup()).toBe('');
  });
});

describe('the confirmation', () => {
  it('reads the price only after the button is pressed, bound to this run and the chip, and sends nothing without consent', async () => {
    const view = await mount();
    expect(estimateRunCost).not.toHaveBeenCalled();
    await view.press('Перезапустить с этого этапа');
    await settle(view);
    expect(estimateRunCost).toHaveBeenCalledWith(
      { body: { version_uid: VERSION_UID, start_from_run_id: RUN_ID, restart_point: 'blocks' } },
      expect.objectContaining({ signal: expect.anything() }));
    const markup = view.markup();
    expect(markup).toContain('data-run-restart="dialog"');
    expect(markup).toMatch(/data-restart-taken="">«Подготовка», «Текст»</);
    expect(markup).toMatch(/data-restart-computed="">«Блоки», «Сверка», «Свод», «Нормы», «Критик», «Уточнение»</);
    expect(markup).toContain('Старый прогон будет удалён после публикации нового. Решения эксперта перенесутся на находки, которые повторятся дословно.');
    expect(markup).not.toContain('data-restart-norms-warning');
    expect(markup).toContain('data-cost-approval');
    expect(await view.press('Перезапустить')).toBe(false);
    expect(restartRun).not.toHaveBeenCalled();
  });

  it('says nothing is taken for a restart from the preparation', async () => {
    const view = await mount({}, ['expert'], 'preparation');
    await view.press('Перезапустить с этого этапа');
    await settle(view);
    expect(view.markup()).not.toContain('data-restart-taken');
    expect(view.markup()).toContain('data-restart-computed');
  });

  it('warns about the norms from the critic on', async () => {
    for (const point of ['review', 'correction'] as const) {
      const view = await mount({}, ['expert'], point);
      await view.press('Перезапустить с этого этапа');
      await settle(view);
      expect(view.markup(), point).toContain('Если поиск норм даст другой результат, перезапуск остановится на этапе «Нормы» — тогда перезапустите с «Норм».');
      await view.unmount();
    }
  });

  it('sends the exact consent under one key, retried under the same key, and opens the new run', async () => {
    vi.mocked(restartRun).mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const view = await mount();
    await view.press('Перезапустить с этого этапа');
    await settle(view);
    await view.check(APPROVE_COST, true);
    await view.press('Перезапустить');
    const first = vi.mocked(restartRun).mock.calls[0]![0];
    expect(first).toEqual({ path: { run_id: RUN_ID }, body: { restart_point: 'blocks', cost_consent: COST_CONSENT }, idempotencyKey: expect.any(String) });
    expect(push).not.toHaveBeenCalled();
    expect(view.markup()).toContain('Перезапуск не выполнен:');

    await view.press('Перезапустить');
    expect(vi.mocked(restartRun).mock.calls[1]![0]).toEqual(first);
    expect(push).toHaveBeenCalledWith(`/projects/${PROJECT_UID}/runs/${NEW_RUN}`);
  });

  it('shows a refusal of the price as a sentence, with no price to consent to', async () => {
    vi.mocked(estimateRunCost).mockRejectedValueOnce(invalid({ reason: 'restart_reply_missing', restart_point: 'blocks', stage_id: 'block_analysis' }));
    const view = await mount();
    await view.press('Перезапустить с этого этапа');
    await settle(view);
    const markup = view.markup();
    expect(markup).toContain('data-restart-failure');
    expect(markup).toContain('Для этапа «Блоки» в исходном прогоне не сохранён ответ модели');
    expect(markup).not.toContain('data-cost-approval');
    expect(await view.press('Перезапустить')).toBe(false);
    expect(restartRun).not.toHaveBeenCalled();
  });

  it('shows a refusal at the command itself as a sentence and the dialog stays open', async () => {
    vi.mocked(restartRun).mockRejectedValueOnce(new ApiError(409, { contract_version: '1.60.0', error_code: 'conflict',
      message: 'x', correlation_id: 'c', retryable: false, details: { conflict_reason: 'restart_in_progress' } }, 'c'));
    const view = await mount();
    await view.press('Перезапустить с этого этапа');
    await settle(view);
    await view.check(APPROVE_COST, true);
    await view.press('Перезапустить');
    expect(view.markup()).toContain('Перезапуск этого прогона уже идёт.');
    expect(push).not.toHaveBeenCalled();
    expect(view.markup()).toContain('data-run-restart="dialog"');
  });

  it('refuses to price a run that is no longer restartable, in a sentence', async () => {
    vi.mocked(getRunStatus).mockImplementation(async ({ path }) => ({ data: {
      ...runStatus(), run_id: path.run_id, state: 'failed', version_uid: VERSION_UID, replaced_by_run_id: NEW_RUN } }) as never);
    const view = await mount();
    await view.press('Перезапустить с этого этапа');
    await settle(view);
    expect(view.markup()).toContain('Состояние прогона изменилось: перезапустить его уже нельзя.');
    expect(estimateRunCost).not.toHaveBeenCalled();
  });

  it('a stale digest reads the price again and needs a new agreement, under a new key', async () => {
    vi.mocked(restartRun).mockRejectedValueOnce(new ApiError(409, { contract_version: '1.60.0',
      error_code: 'conflict', message: 'stale', correlation_id: 'stale', retryable: false,
      details: { conflict_reason: 'run_cost_estimate_stale' } }, 'stale'));
    vi.mocked(estimateRunCost).mockResolvedValueOnce({ data: estimateFor({ version_uid: VERSION_UID, start_from_run_id: RUN_ID,
      restart_point: 'blocks' }, 'blocks') } as never);
    const view = await mount();
    await view.press('Перезапустить с этого этапа');
    await settle(view);
    await view.check(APPROVE_COST, true);
    await view.press('Перезапустить');
    await settle(view);
    expect(view.markup()).toContain('Оценка стоимости устарела. Показана новая: подтвердите её снова.');
    expect(estimateRunCost).toHaveBeenCalledTimes(2);
    // The agreement was withdrawn with the old price.
    expect(await view.press('Перезапустить')).toBe(false);
    await view.check(APPROVE_COST, true);
    await view.press('Перезапустить');
    expect(vi.mocked(restartRun).mock.calls).toHaveLength(2);
  });

  it('cancel closes it without sending anything, and the button is offered again', async () => {
    const view = await mount();
    await view.press('Перезапустить с этого этапа');
    await settle(view);
    await view.press('Отмена');
    expect(view.count('Перезапустить с этого этапа')).toBe(1);
    expect(view.markup()).not.toContain('data-run-restart="dialog"');
    expect(restartRun).not.toHaveBeenCalled();
  });

  it('offers one button for every chip, each bound to its own point', async () => {
    const view = await mount({}, ['expert'], restartPointOf('norms'));
    await view.press('Перезапустить с этого этапа');
    await settle(view);
    expect(vi.mocked(estimateRunCost).mock.calls[0]![0].body).toMatchObject({ restart_point: 'norms' });
  });
});
