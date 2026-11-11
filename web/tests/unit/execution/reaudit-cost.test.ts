/**
 * `RUN-START-ONE-01b` (plan v3 §8): a repeated Run is started by one click on «Повторный аудит».
 *
 * Mounted live and pressed, because what is claimed is a sequence: the click reads the source Run and the estimate; an estimate that
 * charges nothing is agreed to by the click and the re-audit is sent with no panel and no tick-box; one that can charge opens ONE dialog
 * (the start control's own) whose «Запустить» is the agreement; an answer that the estimate changed is estimated again and shown.
 * Each claim has a negative that can fail: what must not be sent is read off the mocked call list, and what must not be drawn off the markup.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  getRunStatus: vi.fn(), estimateRunCost: vi.fn(), reauditRun: vi.fn(), cancelRun: vi.fn(),
}));
vi.mock('@/widgets/execution-queue', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(), ComparisonQueueBlock: () => null,
}));

import { ApiError, cancelRun, estimateRunCost, getRunStatus, queryKeys, reauditRun } from '@/shared/api';
import type { ExecutionQueueItem, RunCostEstimate, RunCostEstimateRequest } from '@/shared/api';
import { QueuePage } from '@/_pages/queue';

import { newClient } from '../screens/harness';
import { VERSION_UID, runStatus } from '../review/fixtures';
import { COST_CONSENT, costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import { QUEUE_WORK } from './queue-work';
import type { LiveRender } from '../analysis-settings/live-render';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const OTHER_RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
const NEW_RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8H';
const JOB_ID = 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const FREE_DIGEST = 'c'.repeat(64);
const CHANGED = 'Оценка изменилась с прошлого раза';
const item = (runId = RUN_ID, state = 'failed'): ExecutionQueueItem => ({
  run_id: runId, job_id: JOB_ID, state, priority: 0, available_at: '2026-10-30T00:00:00Z', created_at: '2026-10-30T00:00:00Z', ...QUEUE_WORK,
});
let live: LiveRender | null = null;

/** The estimate of a connection the application does not bill: 0, and a ceiling of 0. */
function free(body: RunCostEstimateRequest, digest = FREE_DIGEST): RunCostEstimate {
  return { ...costEstimate(body), billing: 'unmetered', estimated_cost_micros: 0, recommended_ceiling_micros: 0, estimate_digest: digest };
}

const stale = () => new ApiError(409, { contract_version: '1.53.0', error_code: 'conflict', message: 'stale',
  correlation_id: 'reaudit-stale', retryable: false, details: { conflict_reason: 'run_cost_estimate_stale' } }, 'reaudit-stale');
const bindingChanged = () => new ApiError(422, { contract_version: '1.53.0', error_code: 'analysis_input_invalid', message: 'binding',
  correlation_id: 'reaudit-binding', retryable: false, details: { reason: 'cost_estimate_binding_changed' } }, 'reaudit-binding');

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getRunStatus).mockImplementation(async ({ path }) => ({ data: {
    ...runStatus(), run_id: path.run_id, state: 'failed', version_uid: VERSION_UID,
  } }) as never);
  vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body) }) as never);
  // Unless a test says otherwise the send is lost on the way: the outcome is unknown.
  vi.mocked(reauditRun).mockRejectedValue(new TypeError('Failed to fetch'));
  vi.mocked(cancelRun).mockResolvedValue({ data: { ...runStatus(), run_id: RUN_ID, state: 'cancelled' } } as never);
});
afterEach(async () => { await live?.unmount(); live = null; });

async function mount(state = 'failed') {
  const client = newClient();
  client.setQueryData(queryKeys.execution.queue(), { items: [item(RUN_ID, state)], page: { next_cursor: null }, paused: false });
  client.setQueryData(queryKeys.account.me(), { roles: ['expert'] });
  live = await mountLive(createElement(QueryClientProvider, { client }, createElement(QueuePage)));
  return { client, view: live };
}

/** Let the reads and the effects they cause run until `condition` holds. */
async function until(view: LiveRender, condition: () => boolean, what: string) {
  for (let tick = 0; tick < 30 && !condition(); tick += 1) await view.settle(() => undefined);
  expect(condition(), what).toBe(true);
}

async function settleCost(view: LiveRender) {
  await until(view, () => !view.markup().includes('Загрузка: стоимость повторного аудита'), 'the estimate is read');
}

const dialogs = (view: LiveRender) => view.markup().match(/data-start-run-dialog/g)?.length ?? 0;
const sent = (index = -1) => vi.mocked(reauditRun).mock.calls.at(index)![0];
const resolveWith = (runId = NEW_RUN) =>
  vi.mocked(reauditRun).mockResolvedValue({ data: { ...runStatus(), run_id: runId, state: 'queued' } } as never);

describe('an estimate that can charge asks once, in one dialog', () => {
  it('reads only after the terminal command is selected, sends nothing until the dialog\'s «Запустить», and sends its exact cap', async () => {
    resolveWith();
    const { view } = await mount();
    expect(estimateRunCost).not.toHaveBeenCalled();
    await view.press('Повторный аудит');
    await settleCost(view);
    expect(getRunStatus).toHaveBeenCalledWith({ path: { run_id: RUN_ID } }, expect.objectContaining({ signal: expect.anything() }));
    expect(estimateRunCost).toHaveBeenCalledWith({ body: { version_uid: VERSION_UID, reaudit_of_run_id: RUN_ID } }, expect.objectContaining({ signal: expect.anything() }));
    // The figure is shown and nothing is sent: the dialog is the question.
    expect(dialogs(view)).toBe(1);
    expect(reauditRun).not.toHaveBeenCalled();
    // None of the old panel: no tick-box fieldset, no «Подтвердить», no «Обновить оценку стоимости», no second dialog.
    const markup = view.markup();
    expect(markup).not.toContain('data-cost-approval');
    expect(markup).not.toContain('data-execution-intent="reaudit"');
    expect(view.count('Подтвердить')).toBe(0);
    expect(view.count('Обновить оценку стоимости')).toBe(0);
    // It names the run it repeats, and holds the ceiling the estimate recommends.
    expect(markup).toContain(`Повторный аудит прогона ${RUN_ID}.`);
    expect(markup).toContain('Предварительная оценка: $1.2.');
    await view.press('Запустить');
    expect(reauditRun).toHaveBeenCalledTimes(1);
    expect(sent()).toEqual({ path: { run_id: RUN_ID }, body: { cost_consent: COST_CONSENT }, idempotencyKey: expect.any(String) });
    // It went: the dialog is gone and the page says so and links the new run.
    expect(dialogs(view)).toBe(0);
    expect(view.markup()).toContain('Команда выполнена.');
    expect(view.markup()).toContain(`Открыть прогон ${NEW_RUN}`);
  });

  it('sends the ceiling the person typed and refuses a ceiling below the estimate', async () => {
    resolveWith();
    const { view } = await mount();
    await view.press('Повторный аудит');
    await settleCost(view);
    await view.change('Лимит стоимости, $', '0.5');
    // Below the estimate of $1.2: the dialog will not send it.
    expect(await view.press('Запустить')).toBe(false);
    expect(reauditRun).not.toHaveBeenCalled();
    await view.change('Лимит стоимости, $', '2');
    await view.press('Запустить');
    expect(sent().body?.cost_consent).toEqual({ ...COST_CONSENT, ceiling_micros: 2_000_000 });
  });

  it('after a send whose outcome is unknown the dialog is gone, the failure is said, and the retry keeps the key', async () => {
    const { view } = await mount();
    await view.press('Повторный аудит');
    await settleCost(view);
    await view.press('Запустить');
    const first = sent();
    expect(first).toEqual({ path: { run_id: RUN_ID }, body: { cost_consent: COST_CONSENT }, idempotencyKey: expect.any(String) });
    expect(dialogs(view)).toBe(0);
    expect(view.markup()).toContain('Исход команды неизвестен');
    await view.press('Повторить с тем же ключом');
    expect(reauditRun).toHaveBeenCalledTimes(2);
    expect(sent(1)).toEqual(first);
    // The retry is the same send, not a new reading.
    expect(estimateRunCost).toHaveBeenCalledTimes(1);
    expect(getRunStatus).toHaveBeenCalledTimes(1);
  });

  it('«Отмена» sends nothing, and the next re-audit reads again', async () => {
    const { view } = await mount();
    await view.press('Повторный аудит');
    await settleCost(view);
    expect(dialogs(view)).toBe(1);
    await view.press('Отмена');
    expect(dialogs(view)).toBe(0);
    expect(reauditRun).not.toHaveBeenCalled();
    await view.press('Повторный аудит');
    await settleCost(view);
    expect(estimateRunCost).toHaveBeenCalledTimes(2);
    expect(dialogs(view)).toBe(1);
  });
});

describe('an estimate that charges nothing is agreed to by the click', () => {
  it('sends the re-audit at once with the consent of that estimate, once, and draws neither dialog nor panel', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: free(body) }) as never);
    resolveWith();
    const { view } = await mount();
    await view.press('Повторный аудит');
    await until(view, () => vi.mocked(reauditRun).mock.calls.length > 0, 'the re-audit is sent');
    await view.settle(() => undefined);
    await view.settle(() => undefined);
    expect(reauditRun).toHaveBeenCalledTimes(1);
    // No second press, no tick-box: the consent is the estimate's own digest and ceiling.
    expect(sent()).toEqual({ path: { run_id: RUN_ID },
      body: { cost_consent: { estimate_digest: FREE_DIGEST, ceiling_micros: 0, confirmed: true } }, idempotencyKey: expect.any(String) });
    const markup = view.markup();
    expect(dialogs(view)).toBe(0);
    expect(markup).not.toContain('data-cost-approval');
    expect(markup).not.toContain('data-execution-intent="reaudit"');
    expect(view.count('Подтвердить')).toBe(0);
    expect(markup).toContain('Команда выполнена.');
    expect(markup).toContain(`Открыть прогон ${NEW_RUN}`);
  });

  it('is sent once while it is on its way, however often the page is drawn meanwhile', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: free(body) }) as never);
    let finish!: (value: never) => void;
    vi.mocked(reauditRun).mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }));
    const { view } = await mount();
    await view.press('Повторный аудит');
    await until(view, () => vi.mocked(reauditRun).mock.calls.length > 0, 'the re-audit is sent');
    // The send has not answered: the page is drawn again (the mutation is pending) and must not send a second time.
    for (let draw = 0; draw < 4; draw += 1) await view.settle(() => undefined);
    expect(view.markup()).toContain('Загрузка: запрос на повторный прогон');
    expect(reauditRun).toHaveBeenCalledTimes(1);
    await view.settle(() => finish({ data: { ...runStatus(), run_id: NEW_RUN, state: 'queued' } } as never));
    expect(reauditRun).toHaveBeenCalledTimes(1);
    expect(view.markup()).toContain('Команда выполнена.');
  });

  it('a refusal of that send is said and is not followed by another send; a retry is the same call', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: free(body) }) as never);
    const { view } = await mount();
    await view.press('Повторный аудит');
    await until(view, () => vi.mocked(reauditRun).mock.calls.length > 0, 'the re-audit is sent');
    await view.settle(() => undefined);
    await view.settle(() => undefined);
    expect(reauditRun).toHaveBeenCalledTimes(1);
    expect(view.markup()).toContain('Исход команды неизвестен');
    const first = sent();
    await view.press('Повторить с тем же ключом');
    expect(reauditRun).toHaveBeenCalledTimes(2);
    expect(sent()).toEqual(first);
    expect(estimateRunCost).toHaveBeenCalledTimes(1);
  });

  it('«Отмена» while the estimate is read sends nothing, even when an estimate that charges nothing arrives late', async () => {
    let arrive!: (value: never) => void;
    vi.mocked(estimateRunCost).mockReturnValueOnce(new Promise((resolve) => { arrive = resolve; }));
    const { view } = await mount();
    await view.press('Повторный аудит');
    expect(view.markup()).toContain('Загрузка: стоимость повторного аудита');
    await view.press('Отмена');
    await view.settle(() => arrive({ data: free({ version_uid: VERSION_UID }) } as never));
    await view.settle(() => undefined);
    expect(reauditRun).not.toHaveBeenCalled();
    expect(dialogs(view)).toBe(0);
    expect(view.markup()).not.toContain('Загрузка: стоимость повторного аудита');
  });
});

describe('an estimate that changed is shown again, whatever its figure', () => {
  it('a stale digest re-reads the estimate by itself and asks in the dialog; the new send has a key of its own', async () => {
    vi.mocked(reauditRun).mockRejectedValueOnce(stale());
    resolveWith();
    const { view } = await mount();
    await view.press('Повторный аудит');
    await settleCost(view);
    expect(view.markup()).not.toContain(CHANGED);
    await view.press('Запустить');
    const first = sent();
    // No panel asking the person to refresh: the page asked again and shows the new estimate.
    await until(view, () => vi.mocked(estimateRunCost).mock.calls.length === 2 && dialogs(view) === 1, 'the estimate is read again and shown');
    expect(getRunStatus).toHaveBeenCalledTimes(2);
    expect(view.markup()).toContain(CHANGED);
    expect(view.count('Обновить оценку стоимости')).toBe(0);
    expect(reauditRun).toHaveBeenCalledTimes(1);
    await view.press('Запустить');
    expect(reauditRun).toHaveBeenCalledTimes(2);
    expect(sent().idempotencyKey).not.toBe(first.idempotencyKey);
    expect(view.markup()).toContain('Команда выполнена.');
  });

  it('a changed binding is answered the same way, and a new estimate that charges nothing is still shown before it is sent', async () => {
    vi.mocked(reauditRun).mockRejectedValueOnce(bindingChanged());
    resolveWith();
    const { view } = await mount();
    await view.press('Повторный аудит');
    await settleCost(view);
    // The second reading charges nothing; the person still sees it, because what they agreed to is not what will run.
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: free(body, 'e'.repeat(64)) }) as never);
    await view.press('Запустить');
    await until(view, () => vi.mocked(estimateRunCost).mock.calls.length === 2 && dialogs(view) === 1, 'the new estimate is shown');
    expect(view.markup()).toContain(CHANGED);
    expect(reauditRun).toHaveBeenCalledTimes(1);
    await view.press('Запустить');
    expect(sent().body?.cost_consent).toEqual({ estimate_digest: 'e'.repeat(64), ceiling_micros: 0, confirmed: true });
  });
});

describe('what cannot be read cannot be agreed to', () => {
  it('a failed estimate is said, nothing can be sent, and the person can read again or leave', async () => {
    vi.mocked(estimateRunCost).mockRejectedValueOnce(new TypeError('Failed to fetch'));
    resolveWith();
    const { view } = await mount();
    await view.press('Повторный аудит');
    await settleCost(view);
    expect(view.markup()).toContain('Стоимость повторного аудита не оценена');
    expect(dialogs(view)).toBe(0);
    expect(view.count('Запустить')).toBe(0);
    expect(reauditRun).not.toHaveBeenCalled();
    await view.press('Оценить снова');
    await settleCost(view);
    expect(estimateRunCost).toHaveBeenCalledTimes(2);
    expect(dialogs(view)).toBe(1);
    expect(reauditRun).not.toHaveBeenCalled();
    await view.press('Запустить');
    expect(reauditRun).toHaveBeenCalledTimes(1);
  });

  it('a late estimate of a source Run that was left cannot be sent for another source Run', async () => {
    resolveWith();
    let complete!: (value: never) => void;
    vi.mocked(estimateRunCost).mockReturnValueOnce(new Promise((resolve) => { complete = resolve; }));
    const { client, view } = await mount();
    await view.press('Повторный аудит');
    await view.press('Отмена');
    await view.settle(() => client.setQueryData(queryKeys.execution.queue(), { items: [item(OTHER_RUN)], page: { next_cursor: null }, paused: false }));
    await view.press('Повторный аудит');
    await settleCost(view);
    await view.settle(() => complete({ data: { ...costEstimate({ version_uid: VERSION_UID }), estimate_digest: 'b'.repeat(64) } } as never));
    expect(reauditRun).not.toHaveBeenCalled();
    await view.press('Запустить');
    expect(sent()).toEqual({ path: { run_id: OTHER_RUN }, body: { cost_consent: COST_CONSENT }, idempotencyKey: expect.any(String) });
  });
});

describe('cancel is not a start', () => {
  it('stays a separate confirmation without cost or a repeated-Run request', async () => {
    const { view } = await mount('queued');
    expect(view.count('Повторный аудит')).toBe(0);
    await view.press('Отменить прогон');
    expect(view.markup()).not.toContain('data-cost-approval');
    expect(dialogs(view)).toBe(0);
    await view.press('Подтвердить');
    expect(cancelRun).toHaveBeenCalledWith({ path: { run_id: RUN_ID }, idempotencyKey: expect.any(String) });
    expect(estimateRunCost).not.toHaveBeenCalled();
    expect(reauditRun).not.toHaveBeenCalled();
  });
});
