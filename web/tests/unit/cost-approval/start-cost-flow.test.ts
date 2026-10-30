import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  estimateRunCost: vi.fn(), estimateArV3GroupCost: vi.fn(), startRun: vi.fn(), startArV3BetaGroup: vi.fn(),
}));

import { ApiError, estimateRunCost, estimateArV3GroupCost, startRun, startArV3BetaGroup } from '@/shared/api';
import { ANALYSIS_PRESETS_KEY } from '@/entities/analysis-preset';
import { StartRunControl } from '@/features/start-run';
import { StartArV3GroupControl, useArV3GroupStartIntent } from '@/features/start-ar-v3-group';

import { newClient } from '../screens/harness';
import { PROJECT_UID, VERSION_UID } from '../review/fixtures';
import { READY, SPARE, seedExecutors } from '../workers/executor-fixtures';
import { APPROVE_COST, COST_CONSENT, approveCost, costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';

const SINGLE = 'Запустить прогон';
const GROUP = 'Запустить шесть проверок АР v3';
const OTHER_VERSION = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
let live: LiveRender | null = null;

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body) }) as never);
  vi.mocked(estimateArV3GroupCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body, 'ar_v3_group') }) as never);
  vi.mocked(startRun).mockRejectedValue(new TypeError('Failed to fetch'));
  vi.mocked(startArV3BetaGroup).mockRejectedValue(new TypeError('Failed to fetch'));
});
afterEach(async () => { await live?.unmount(); live = null; });

function client() {
  const result = newClient();
  seedExecutors(result, [READY, SPARE]);
  result.setQueryData(ANALYSIS_PRESETS_KEY, { items: [] });
  return result;
}

describe('ordinary section start preflight', () => {
  it('requires an observed estimate and explicit approval, then sends the identical chosen options and cap', async () => {
    live = await mountLive(createElement(QueryClientProvider, { client: client() },
      createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    expect(await live.press(SINGLE)).toBe(false);
    await live.change('Исполнитель', READY.connection.connection_id);
    await live.check('Повышенные лимиты ИИ-анализа', true);
    await live.press('Оценить стоимость');
    expect(estimateRunCost).toHaveBeenCalledWith({ body: {
      version_uid: VERSION_UID, executor_connection_id: READY.connection.connection_id, relaxed_limits: true,
    } });
    expect(await live.press(SINGLE)).toBe(false);
    await live.check(APPROVE_COST, true);
    await live.press(SINGLE);
    const first = vi.mocked(startRun).mock.calls[0]![0];
    expect(first.body).toEqual({ version_uid: VERSION_UID, executor_connection_id: READY.connection.connection_id,
      relaxed_limits: true, cost_consent: COST_CONSENT });
    await live.press(SINGLE);
    expect(vi.mocked(startRun).mock.calls[1]![0].idempotencyKey).toBe(first.idempotencyKey);
    await live.check(APPROVE_COST, false);
    expect(await live.press(SINGLE)).toBe(false);
    await live.check(APPROVE_COST, true);
    await live.press(SINGLE);
    expect(vi.mocked(startRun).mock.calls[2]![0].idempotencyKey).toBe(first.idempotencyKey);
    await live.press('Оценить стоимость');
    expect(await live.press(SINGLE)).toBe(false);
    await live.check(APPROVE_COST, true);
    await live.press(SINGLE);
    expect(vi.mocked(startRun).mock.calls[3]![0].idempotencyKey).toBe(first.idempotencyKey);
  });

  it('a cap edit requires new agreement, while a changed executor requires a fresh estimate and key', async () => {
    live = await mountLive(createElement(QueryClientProvider, { client: client() },
      createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    await approveCost(live);
    await live.press(SINGLE);
    const first = vi.mocked(startRun).mock.calls[0]![0].idempotencyKey;
    await live.change('Лимит стоимости, USD', '1.1');
    expect(await live.check(APPROVE_COST, true)).toBe(false);
    expect(await live.press(SINGLE)).toBe(false);
    await live.change('Лимит стоимости, USD', '2.000001');
    expect(await live.press(SINGLE)).toBe(false);
    await live.check(APPROVE_COST, true);
    await live.press(SINGLE);
    const changedCap = vi.mocked(startRun).mock.calls[1]![0];
    expect(changedCap.body.cost_consent?.ceiling_micros).toBe(2_000_001);
    expect(changedCap.idempotencyKey).not.toBe(first);
    await live.change('Исполнитель', SPARE.connection.connection_id);
    expect(live.markup()).not.toContain('data-cost-approval');
    expect(await live.press(SINGLE)).toBe(false);
    await approveCost(live);
    await live.press(SINGLE);
    const changedExecutor = vi.mocked(startRun).mock.calls[2]![0];
    expect(changedExecutor.body.executor_connection_id).toBe(SPARE.connection.connection_id);
    expect(changedExecutor.idempotencyKey).not.toBe(changedCap.idempotencyKey);
  });

  it('a failed or absent legacy estimate endpoint cannot enable start', async () => {
    vi.mocked(estimateRunCost).mockRejectedValue(new Error('legacy endpoint unavailable'));
    live = await mountLive(createElement(QueryClientProvider, { client: client() },
      createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    await live.press('Оценить стоимость');
    expect(live.markup()).toContain('Стоимость не оценена');
    expect(live.markup()).not.toContain('data-cost-approval');
    expect(await live.press(SINGLE)).toBe(false);
    expect(startRun).not.toHaveBeenCalled();
  });

  it('explains a comparison-only PDF refusal and stops repeat cost requests', async () => {
    vi.mocked(estimateRunCost).mockRejectedValue(new ApiError(422, {
      contract_version: '1.14.0', error_code: 'analysis_input_invalid', message: 'comparison-only PDF',
      correlation_id: 'cid-comparison-only', retryable: false,
      details: { reason: 'comparison_only_version' },
    }, 'cid-comparison-only'));
    live = await mountLive(createElement(QueryClientProvider, { client: client() },
      createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    await live.press('Оценить стоимость');
    expect(live.markup()).toContain('Сервер не принимает этот PDF');
    expect(live.markup()).toContain('href="/stage-comparison"');
    expect(live.markup()).toContain('cid-comparison-only');
    expect(await live.press('Оценить стоимость')).toBe(false);
    expect(await live.press(SINGLE)).toBe(false);
    expect(estimateRunCost).toHaveBeenCalledTimes(1);
  });

  it('a server-reported stale digest clears approval and requires a new estimate', async () => {
    vi.mocked(startRun).mockRejectedValueOnce(new ApiError(409, { contract_version: '1.14.0',
      error_code: 'conflict', message: 'stale estimate', correlation_id: 'cost-stale', retryable: false,
      details: { conflict_reason: 'run_cost_estimate_stale' } }, 'cost-stale'));
    live = await mountLive(createElement(QueryClientProvider, { client: client() },
      createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    await approveCost(live);
    await live.press(SINGLE);
    expect(live.markup()).toContain('Оценка стоимости устарела.');
    expect(live.markup()).not.toContain('data-cost-approval');
    expect(await live.press(SINGLE)).toBe(false);
    vi.mocked(estimateRunCost).mockRejectedValueOnce(new TypeError('Failed to fetch'));
    await live.press('Оценить стоимость');
    expect(live.markup()).toContain('Стоимость не оценена');
    expect(await live.press(SINGLE)).toBe(false);
    expect(startRun).toHaveBeenCalledTimes(1);
  });

  it('does not approve a late reading for a previous version', async () => {
    let complete!: (value: never) => void;
    vi.mocked(estimateRunCost).mockReturnValueOnce(new Promise((resolve) => { complete = resolve; }));
    const cache = client();
    const tree = (versionUid: string) => createElement(QueryClientProvider, { client: cache },
      createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid }));
    live = await mountLive(tree(VERSION_UID));
    await live.press('Оценить стоимость');
    await live.update(tree(OTHER_VERSION));
    await live.settle(() => complete({ data: costEstimate({ version_uid: VERSION_UID }) } as never));
    expect(live.markup()).not.toContain('data-cost-approval');
    expect(await live.press(SINGLE)).toBe(false);
  });
});

describe('caller-owned AR v3 approval', () => {
  function Parent({ show = true }: { show?: boolean }) {
    const intent = useArV3GroupStartIntent(VERSION_UID);
    return show ? createElement(StartArV3GroupControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID, intent }) : null;
  }

  it('retains the exact consent and retry key while the control is temporarily unmounted', async () => {
    const cache = client();
    const tree = (show: boolean) => createElement(QueryClientProvider, { client: cache }, createElement(Parent, { show }));
    live = await mountLive(tree(true));
    expect(await live.press(GROUP)).toBe(false);
    await live.check('Повышенные лимиты ИИ-анализа', true);
    await approveCost(live);
    expect(estimateArV3GroupCost).toHaveBeenCalledWith({ body: { version_uid: VERSION_UID, relaxed_limits: true } });
    await live.press(GROUP);
    const sent = vi.mocked(startArV3BetaGroup).mock.calls[0]![0];
    expect(sent.body).toEqual({ version_uid: VERSION_UID, relaxed_limits: true, cost_consent: COST_CONSENT });
    await live.update(tree(false));
    await live.update(tree(true));
    await live.press(GROUP);
    expect(vi.mocked(startArV3BetaGroup).mock.calls[1]![0]).toEqual(sent);
  });

  it('requires explicit agreement even for an unmetered zero estimate', async () => {
    vi.mocked(estimateArV3GroupCost).mockImplementation(async ({ body }) => ({ data: {
      ...costEstimate(body, 'ar_v3_group'), billing: 'unmetered', estimated_cost_micros: 0, recommended_ceiling_micros: 0,
    } }) as never);
    live = await mountLive(createElement(QueryClientProvider, { client: client() }, createElement(Parent)));
    await live.press('Оценить стоимость шести проверок');
    expect(live.markup()).toContain('Подключение без тарификации в приложении');
    expect(await live.press(GROUP)).toBe(false);
    await live.check(APPROVE_COST, true);
    await live.press(GROUP);
    expect(vi.mocked(startArV3BetaGroup).mock.calls[0]![0].body.cost_consent?.ceiling_micros).toBe(0);
  });

  it('rejects a successful HTTP reading for the wrong operation scope', async () => {
    vi.mocked(estimateArV3GroupCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body, 'run') }) as never);
    live = await mountLive(createElement(QueryClientProvider, { client: client() }, createElement(Parent)));
    await live.press('Оценить стоимость шести проверок');
    expect(live.markup()).toContain('Стоимость не оценена');
    expect(await live.press(GROUP)).toBe(false);
  });
});
