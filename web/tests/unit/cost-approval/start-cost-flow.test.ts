import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  estimateRunCost: vi.fn(), estimateArV3GroupCost: vi.fn(), startRun: vi.fn(), startArV3BetaGroup: vi.fn(),
}));

import { estimateRunCost, estimateArV3GroupCost, startRun, startArV3BetaGroup } from '@/shared/api';
import { ANALYSIS_PRESETS_KEY } from '@/entities/analysis-preset';
import { StartArV3GroupControl, useArV3GroupStartIntent } from '@/features/start-ar-v3-group';

import { newClient } from '../screens/harness';
import { PROJECT_UID, VERSION_UID } from '../review/fixtures';
import { READY, SPARE, seedExecutors } from '../workers/executor-fixtures';
import { APPROVE_COST, COST_CONSENT, approveCost, costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';

const GROUP = 'Запустить шесть проверок АР v3';
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

// The ordinary section start's preflight (an observed estimate before a send, the cap, the key, a stale digest,
// an unreadable endpoint, a comparison-only PDF, a late reading for another version) moved with the control to
// `../start-run/one-click-start.test.ts` (`RUN-START-ONE-01a`): the ordinary start no longer has a separate
// «Оценить стоимость» step to press, so its sequence is proved there. This file keeps the AR v3 group's, which has one.

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
