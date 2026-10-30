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
import type { ExecutionQueueItem } from '@/shared/api';
import { QueuePage } from '@/_pages/queue';

import { newClient } from '../screens/harness';
import { VERSION_UID, runStatus } from '../review/fixtures';
import { APPROVE_COST, COST_CONSENT, costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';

const RUN_ID = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const OTHER_RUN = 'run_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
const JOB_ID = 'job_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const item = (runId = RUN_ID, state = 'failed'): ExecutionQueueItem => ({
  run_id: runId, job_id: JOB_ID, state, priority: 0, available_at: '2026-10-30T00:00:00Z', created_at: '2026-10-30T00:00:00Z',
});
let live: LiveRender | null = null;

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getRunStatus).mockImplementation(async ({ path }) => ({ data: {
    ...runStatus(), run_id: path.run_id, state: 'failed', version_uid: VERSION_UID,
  } }) as never);
  vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body) }) as never);
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

async function settleCost(view: LiveRender) {
  for (let tick = 0; tick < 20 && view.markup().includes('Загрузка: стоимость повторного аудита'); tick += 1) {
    await view.settle(() => undefined);
  }
  expect(view.markup()).not.toContain('Загрузка: стоимость повторного аудита');
}

describe('fresh cost consent for repeated paid Runs', () => {
  it('reads only after the terminal command is selected and requires new approval before sending its exact cap', async () => {
    const { view } = await mount();
    expect(estimateRunCost).not.toHaveBeenCalled();
    await view.press('Повторный аудит');
    await settleCost(view);
    expect(getRunStatus).toHaveBeenCalledWith({ path: { run_id: RUN_ID } }, expect.objectContaining({ signal: expect.anything() }));
    expect(estimateRunCost).toHaveBeenCalledWith({ body: { version_uid: VERSION_UID, reaudit_of_run_id: RUN_ID } }, expect.objectContaining({ signal: expect.anything() }));
    expect(await view.press('Подтвердить')).toBe(false);
    expect(reauditRun).not.toHaveBeenCalled();
    await view.check(APPROVE_COST, true);
    await view.press('Подтвердить');
    const first = vi.mocked(reauditRun).mock.calls[0]![0];
    expect(first).toEqual({ path: { run_id: RUN_ID }, body: { cost_consent: COST_CONSENT }, idempotencyKey: expect.any(String) });
    await view.press('Повторить с тем же ключом');
    expect(vi.mocked(reauditRun).mock.calls[1]![0]).toEqual(first);
    expect(estimateRunCost).toHaveBeenCalledTimes(1);
    await view.change('Лимит стоимости, USD', '2');
    expect(await view.press('Повторить с тем же ключом')).toBe(false);
    await view.check(APPROVE_COST, true);
    await view.press('Повторить с тем же ключом');
    const changed = vi.mocked(reauditRun).mock.calls[2]![0];
    expect(changed.body?.cost_consent?.ceiling_micros).toBe(2_000_000);
    expect(changed.idempotencyKey).not.toBe(first.idempotencyKey);
  });

  it('a failed estimate cannot confirm a repeated Run', async () => {
    vi.mocked(estimateRunCost).mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const { view } = await mount();
    await view.press('Повторный аудит');
    await settleCost(view);
    expect(view.markup()).toContain('Стоимость повторного аудита не оценена');
    expect(view.markup()).not.toContain('data-cost-approval');
    expect(await view.press('Подтвердить')).toBe(false);
    expect(reauditRun).not.toHaveBeenCalled();
  });

  it('a stale digest requires a fresh reading and new agreement', async () => {
    vi.mocked(reauditRun).mockRejectedValueOnce(new ApiError(409, { contract_version: '1.14.0',
      error_code: 'conflict', message: 'stale', correlation_id: 'reaudit-stale', retryable: false,
      details: { conflict_reason: 'run_cost_estimate_stale' } }, 'reaudit-stale'));
    const { view } = await mount();
    await view.press('Повторный аудит');
    await settleCost(view);
    await view.check(APPROVE_COST, true);
    await view.press('Подтвердить');
    expect(view.markup()).toContain('Оценка стоимости устарела.');
    expect(await view.press('Подтвердить')).toBe(false);
    await view.press('Обновить оценку стоимости');
    await settleCost(view);
    expect(getRunStatus).toHaveBeenCalledTimes(2);
    expect(estimateRunCost).toHaveBeenCalledTimes(2);
    expect(await view.press('Подтвердить')).toBe(false);
    await view.check(APPROVE_COST, true);
    await view.press('Подтвердить');
    expect(vi.mocked(reauditRun).mock.calls[1]![0].idempotencyKey).not.toBe(vi.mocked(reauditRun).mock.calls[0]![0].idempotencyKey);
  });

  it('a cancelled dialog cannot transfer a late estimate or approval to another source Run', async () => {
    let complete!: (value: never) => void;
    vi.mocked(estimateRunCost).mockReturnValueOnce(new Promise((resolve) => { complete = resolve; }));
    const { client, view } = await mount();
    await view.press('Повторный аудит');
    await view.press('Отмена');
    await view.settle(() => client.setQueryData(queryKeys.execution.queue(), { items: [item(OTHER_RUN)], page: { next_cursor: null }, paused: false }));
    await view.press('Повторный аудит');
    await view.settle(() => complete({ data: { ...costEstimate({ version_uid: VERSION_UID }), estimate_digest: 'b'.repeat(64) } } as never));
    expect(await view.press('Подтвердить')).toBe(false);
    await view.check(APPROVE_COST, true);
    await view.press('Подтвердить');
    expect(vi.mocked(reauditRun).mock.calls[0]![0]).toEqual({ path: { run_id: OTHER_RUN },
      body: { cost_consent: COST_CONSENT }, idempotencyKey: expect.any(String) });
  });

  it('cancel remains a separate confirmation without cost or a repeated-Run request', async () => {
    const { view } = await mount('queued');
    expect(view.count('Повторный аудит')).toBe(0);
    await view.press('Отменить прогон');
    expect(view.markup()).not.toContain('data-cost-approval');
    await view.press('Подтвердить');
    expect(cancelRun).toHaveBeenCalledWith({ path: { run_id: RUN_ID }, idempotencyKey: expect.any(String) });
    expect(estimateRunCost).not.toHaveBeenCalled();
    expect(reauditRun).not.toHaveBeenCalled();
  });
});
