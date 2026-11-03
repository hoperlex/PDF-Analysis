/**
 * `EXEC2-WEB-GROUPS-01` — how a run is started: «Автоматически (по типу задачи)», «Группа исполнителей»
 * and «Конкретное подключение», and the rule that **exactly one selector is sent** (ADR-0026 decisions
 * 12 to 14; `startRun` and `estimateRunCost` of API 1.16.0 refuse a group beside a connection or a
 * preset). Written under `R-149d` and not run in EXEC-2; none of it needs PostgreSQL.
 *
 * Three layers, each able to fail on its own: the pure choice (`startSelectors`, `startRunBody`,
 * `startRunIntent`), the control rendered once, and the control mounted live and pressed.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  startRun: vi.fn(),
  estimateRunCost: vi.fn(),
}));

import { estimateRunCost, startRun } from '@/shared/api';
import { ANALYSIS_PRESETS_KEY } from '@/entities/analysis-preset';
import {
  AUTOMATIC_CHOICE, START_MODES, START_MODE_LABELS, StartRunControl, chooseMode, selectorCount,
  startChoiceComplete, startRunBody, startRunIntent, startSelectors,
} from '@/features/start-run';
import type { StartChoice, StartMode, StartRunCommand } from '@/features/start-run';

import { PROJECT_UID, VERSION_UID } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';
import { COST_CONSENT, approveCost, costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { MAIN_GROUP, READY, SPARE, groupId, seedGroups } from './executor-groups-fixtures';

const GROUP = groupId(1);
const CONNECTION = READY.connection.connection_id;
const PRESET = 'pre_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

function choice(mode: StartMode, over: Partial<StartChoice> = {}): StartChoice {
  return { mode, groupId: null, connectionId: null, presetId: null, ...over };
}

describe('the choice becomes at most one selector', () => {
  const grids: StartChoice[] = [];
  for (const mode of START_MODES) {
    for (const withGroup of [false, true]) {
      for (const withConnection of [false, true]) {
        for (const withPreset of [false, true]) {
          grids.push(choice(mode, {
            groupId: withGroup ? GROUP : null,
            connectionId: withConnection ? CONNECTION : null,
            presetId: withPreset ? PRESET : null,
          }));
        }
      }
    }
  }

  it('is never more than one, whatever the control still holds from another mode', () => {
    expect(grids).toHaveLength(24);
    for (const one of grids) expect(selectorCount(one), JSON.stringify(one)).toBeLessThanOrEqual(1);
  });

  it('sends nothing for «Автоматически», even over leftovers', () => {
    for (const one of grids.filter((item) => item.mode === 'auto')) {
      expect(startSelectors(one)).toEqual({ executorGroupId: null, executorConnectionId: null, presetId: null });
    }
  });

  it('sends only the group for «Группа исполнителей»', () => {
    for (const one of grids.filter((item) => item.mode === 'group')) {
      expect(startSelectors(one)).toEqual({
        executorGroupId: one.groupId, executorConnectionId: null, presetId: null,
      });
    }
  });

  it('sends the preset, else the connection, for «Конкретное подключение», and never the group', () => {
    for (const one of grids.filter((item) => item.mode === 'connection')) {
      const selectors = startSelectors(one);
      expect(selectors.executorGroupId).toBeNull();
      if (one.presetId !== null) {
        expect(selectors).toEqual({ executorGroupId: null, executorConnectionId: null, presetId: PRESET });
      } else {
        expect(selectors.presetId).toBeNull();
        expect(selectors.executorConnectionId).toBe(one.connectionId);
      }
    }
  });

  it('calls a mode without its own choice incomplete, since it would send nothing', () => {
    expect(startChoiceComplete(AUTOMATIC_CHOICE)).toBe(true);
    expect(startChoiceComplete(choice('group'))).toBe(false);
    expect(startChoiceComplete(choice('group', { groupId: GROUP }))).toBe(true);
    expect(startChoiceComplete(choice('connection'))).toBe(false);
    expect(startChoiceComplete(choice('connection', { connectionId: CONNECTION }))).toBe(true);
    expect(startChoiceComplete(choice('connection', { presetId: PRESET }))).toBe(true);
    // A leftover of another mode does not complete this one.
    expect(startChoiceComplete(choice('group', { connectionId: CONNECTION, presetId: PRESET }))).toBe(false);
    expect(startChoiceComplete(choice('connection', { groupId: GROUP }))).toBe(false);
  });

  it('drops what belongs to another mode when the mode is picked', () => {
    const held = choice('connection', { connectionId: CONNECTION, presetId: PRESET });
    expect(chooseMode(held, 'group')).toEqual(choice('group'));
    expect(chooseMode(held, 'auto')).toEqual(AUTOMATIC_CHOICE);
    expect(chooseMode(held, 'connection')).toEqual(held);
    const grouped = choice('group', { groupId: GROUP });
    expect(chooseMode(grouped, 'connection')).toEqual(choice('connection'));
    expect(chooseMode(grouped, 'group')).toEqual(grouped);
    // And back again: nothing of the connection survived the visit to the group.
    expect(chooseMode(chooseMode(held, 'group'), 'connection')).toEqual(choice('connection'));
  });

  it('has the three labels the owner worded', () => {
    expect(START_MODES.map((mode) => START_MODE_LABELS[mode])).toEqual([
      'Автоматически (по типу задачи)', 'Группа исполнителей', 'Конкретное подключение',
    ]);
  });
});

describe('the request carries one selector, even if the command holds more', () => {
  function body(over: Partial<StartRunCommand>): Record<string, unknown> {
    return startRunBody({ versionUid: VERSION_UID, idempotencyKey: 'ik', ...over }) as Record<string, unknown>;
  }

  it('prefers the group, then the preset, then the connection', () => {
    expect(body({ executorGroupId: GROUP, presetId: PRESET, executorConnectionId: CONNECTION }))
      .toEqual({ version_uid: VERSION_UID, executor_group_id: GROUP });
    expect(body({ presetId: PRESET, executorConnectionId: CONNECTION }))
      .toEqual({ version_uid: VERSION_UID, preset_id: PRESET });
    expect(body({ executorConnectionId: CONNECTION }))
      .toEqual({ version_uid: VERSION_UID, executor_connection_id: CONNECTION });
    expect(body({})).toEqual({ version_uid: VERSION_UID });
  });

  it('never holds two of the three keys, for every subset of the three', () => {
    for (const mask of Array.from({ length: 8 }, (_, index) => index)) {
      const request = body({
        ...((mask & 1) === 0 ? {} : { executorGroupId: GROUP }),
        ...((mask & 2) === 0 ? {} : { presetId: PRESET }),
        ...((mask & 4) === 0 ? {} : { executorConnectionId: CONNECTION }),
      });
      const keys = ['executor_group_id', 'preset_id', 'executor_connection_id'].filter((key) => key in request);
      expect(keys.length, `mask ${mask}`).toBeLessThanOrEqual(1);
    }
  });

  it('keeps the cost consent and the raised limit beside the selector', () => {
    expect(body({ executorGroupId: GROUP, relaxedLimits: true, costConsent: COST_CONSENT })).toEqual({
      version_uid: VERSION_UID, executor_group_id: GROUP, relaxed_limits: true, cost_consent: COST_CONSENT,
    });
  });
});

describe('the intent of a group start', () => {
  it('is a different intent from the same version without a group, and from another group', () => {
    const plain = startRunIntent(VERSION_UID, null);
    const grouped = startRunIntent(VERSION_UID, null, null, false, undefined, GROUP);
    const other = startRunIntent(VERSION_UID, null, null, false, undefined, groupId(2));
    expect(plain.signature).toBe(`start-run:${VERSION_UID}`);
    expect(grouped.signature).toBe(`start-run:${VERSION_UID}:group:${GROUP}`);
    expect(new Set([plain.signature, grouped.signature, other.signature]).size).toBe(3);
  });

  it('builds the command with the group alone, and keeps the old signatures word for word', () => {
    const grouped = startRunIntent(VERSION_UID, CONNECTION, PRESET, false, undefined, GROUP);
    expect(grouped.command('ik')).toEqual({ versionUid: VERSION_UID, idempotencyKey: 'ik', executorGroupId: GROUP });
    expect(startRunIntent(VERSION_UID, CONNECTION).signature).toBe(`start-run:${VERSION_UID}:executor:${CONNECTION}`);
    expect(startRunIntent(VERSION_UID, null, PRESET).signature).toBe(`start-run:${VERSION_UID}:preset:${PRESET}`);
  });
});

type Client = ReturnType<typeof newClient>;

function seeded(): Client {
  const client = newClient();
  seedGroups(client);
  client.setQueryData(ANALYSIS_PRESETS_KEY, { items: [] });
  return client;
}

describe('the control, rendered once', () => {
  const markup = renderWith(seeded(), createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));

  it('offers the three ways, «Автоматически» first and chosen', () => {
    expect(markup.match(/type="radio"/g)).toHaveLength(3);
    const at = START_MODES.map((mode) => markup.indexOf(`data-start-mode-choice="${mode}"`));
    expect(at.every((index) => index >= 0)).toBe(true);
    expect([...at].sort((a, b) => a - b)).toEqual(at);
    expect(markup).toContain('data-start-mode="auto"');
    expect(markup.match(/checked=""/g)).toHaveLength(1);
    for (const mode of START_MODES) expect(markup).toContain(START_MODE_LABELS[mode]);
  });

  it('keeps the connection and preset selects and draws no group select until the group is chosen', () => {
    expect(markup.match(/<select\b/g)).toHaveLength(2);
    expect(markup).toContain('data-preset-select');
    expect(markup).toContain('data-executor-select');
    expect(markup).not.toContain('data-group-select');
    expect(markup).not.toContain('data-start-choice-missing');
  });

  it('can start at once: «Автоматически» is complete', () => {
    expect(markup).toMatch(/<button type="button" class="am-button">Оценить стоимость<\/button>/);
  });
});

describe('the control, live', () => {
  let live: LiveRender | null = null;

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(startRun).mockResolvedValue({ data: { run_id: 'run_01M2545JSD15ETSNNV904X993K' } } as never);
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body) }) as never);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mount(): Promise<LiveRender> {
    live = await mountLive(createElement(QueryClientProvider, { client: seeded() },
      createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    return live;
  }

  const sent = (): Record<string, unknown> =>
    (vi.mocked(startRun).mock.calls.at(-1)![0] as { body: Record<string, unknown> }).body;

  it('sends the group and nothing else, estimate and start alike', async () => {
    const view = await mount();
    expect(await view.change('Группа исполнителей', 'group')).toBe(true);
    expect(view.markup()).toContain('data-group-select');
    expect(view.markup()).not.toContain('data-executor-select');
    expect(await view.change('Группа', GROUP)).toBe(true);
    expect(view.markup()).toContain(`Прогон принимает группа «${MAIN_GROUP.display_name}»`);
    await approveCost(view);
    expect(estimateRunCost).toHaveBeenCalledWith({ body: { version_uid: VERSION_UID, executor_group_id: GROUP } });
    await view.press('Запустить прогон');
    expect(startRun).toHaveBeenCalledTimes(1);
    expect(sent()).toEqual({ version_uid: VERSION_UID, executor_group_id: GROUP, cost_consent: COST_CONSENT });
  });

  it('keeps both buttons disabled while the group is not chosen, and says what is missing', async () => {
    const view = await mount();
    await view.change('Группа исполнителей', 'group');
    expect(view.markup()).toContain('data-start-choice-missing="group"');
    expect(view.markup()).toContain('Выберите группу');
    expect(await view.press('Оценить стоимость')).toBe(false);
    expect(await view.press('Запустить прогон')).toBe(false);
    expect(estimateRunCost).not.toHaveBeenCalled();
    expect(startRun).not.toHaveBeenCalled();
  });

  it('keeps both buttons disabled on «Конкретное подключение» until a connection or a preset is chosen', async () => {
    const view = await mount();
    await view.change('Конкретное подключение', 'connection');
    expect(view.markup()).toContain('data-start-choice-missing="connection"');
    expect(await view.press('Оценить стоимость')).toBe(false);
    await view.change('Исполнитель', CONNECTION);
    expect(view.markup()).not.toContain('data-start-choice-missing');
    await approveCost(view);
    await view.press('Запустить прогон');
    expect(sent()).toEqual({ version_uid: VERSION_UID, executor_connection_id: CONNECTION, cost_consent: COST_CONSENT });
  });

  it('forgets a connection chosen before the group: only the group goes out', async () => {
    const view = await mount();
    await view.change('Исполнитель', SPARE.connection.connection_id);
    expect(view.markup()).toContain('data-start-mode="connection"');
    await view.change('Группа исполнителей', 'group');
    await view.change('Группа', GROUP);
    await approveCost(view);
    await view.press('Запустить прогон');
    expect(sent()).toEqual({ version_uid: VERSION_UID, executor_group_id: GROUP, cost_consent: COST_CONSENT });
    expect(sent()).not.toHaveProperty('executor_connection_id');
  });

  it('forgets the group on «Автоматически»: no selector goes out', async () => {
    const view = await mount();
    await view.change('Группа исполнителей', 'group');
    await view.change('Группа', GROUP);
    await view.change('Автоматически (по типу задачи)', 'auto');
    expect(view.markup()).not.toContain('data-group-select');
    await approveCost(view);
    await view.press('Запустить прогон');
    expect(sent()).toEqual({ version_uid: VERSION_UID, cost_consent: COST_CONSENT });
  });

  it('moves the radio with the selects: a connection is «Конкретное подключение», and taking it off is «Автоматически»', async () => {
    const view = await mount();
    await view.change('Исполнитель', CONNECTION);
    expect(view.markup()).toContain('data-start-mode="connection"');
    await view.change('Исполнитель', '');
    expect(view.markup()).toContain('data-start-mode="auto"');
  });

  it('uses another key for another group, and the same key to repeat one', async () => {
    const view = await mount();
    await view.change('Группа исполнителей', 'group');
    await view.change('Группа', GROUP);
    await approveCost(view);
    await view.press('Запустить прогон');
    await view.press('Запустить прогон');
    const keys = vi.mocked(startRun).mock.calls.map((call) => (call[0] as { idempotencyKey: string }).idempotencyKey);
    expect(keys).toHaveLength(2);
    expect(keys[0]).toBe(keys[1]);
  });
});
