/**
 * `ANALYSIS-PRESETS-01` (`R-146av`): the presets of how a run starts, in «Настройки анализа», at run
 * start and on the run.
 *
 * What is proved here, in the order a person meets it:
 *
 * - the settings section: the list for any role, the controls for an administrator only, an archive
 *   apart, a preset whose executor cannot serve said so, and the failure/empty states;
 * - the commands, live: a save sends exactly `{name, executor_connection_id}` under one key, a repeat
 *   after a failure reuses the key, an edit is another key; a revision names its preset in the path;
 * - the start control: «Пресет» comes before «Исполнитель», a preset that cannot serve is listed
 *   disabled with the reason, a chosen preset locks the executor select, and the request carries
 *   `preset_id` and never the executor beside it;
 * - the run: the preset shows beside the executor when the run has one and nowhere when it has none.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    archiveAnalysisPreset: vi.fn(),
    createAnalysisPreset: vi.fn(),
    listAnalysisPresets: vi.fn(),
    reviseAnalysisPreset: vi.fn(),
    startRun: vi.fn(),
  };
});

import {
  ApiError, archiveAnalysisPreset, createAnalysisPreset, listAnalysisPresets, queryKeys, reviseAnalysisPreset, startRun,
} from '@/shared/api';
import type { AnalysisPreset, ErrorEnvelope, RunStatus } from '@/shared/api';
import { ANALYSIS_PRESETS_KEY, presetBlocker, presetChoices, presetFailure, presetOptionLabel } from '@/entities/analysis-preset';
import { RunRow, classifyRunFailure, runPresetLine, runPresetSentence, runPresetValue } from '@/entities/audit-run';
import { executorChoices } from '@/entities/executor-connection';
import { StartRunControl, startRunBody, startRunIntent } from '@/features/start-run';
import { RunProgress } from '@/widgets/run-progress';
import { AnalysisPresets } from '@/widgets/analysis-presets';

import { PROJECT_UID, VERSION_UID, render, runStatus } from '../review/fixtures';
import { newClient, renderWith } from '../screens/harness';
import { READY, SPARE, ALL_CASES, executorCase, seedExecutors } from '../workers/executor-fixtures';
import { mountLive } from './live-render';
import type { LiveRender } from './live-render';

type Client = ReturnType<typeof newClient>;

const ulid = (n: number): string => `01M2545JSD15ETSNNV904X${String(n).padStart(4, '0')}`.slice(0, 26);
const presetId = (n: number): string => `evt_${ulid(n)}`;
const ADMIN_UID = 'usr_01J9ZQ8K7NHVXW3T2R5M6P4Q8F';

function preset(n: number, over: Partial<AnalysisPreset> = {}): AnalysisPreset {
  return {
    preset_id: presetId(n),
    revision_id: presetId(n + 100),
    revision_no: 1,
    name: `Пресет ${n}`,
    executor_connection_id: READY.connection.connection_id,
    state: 'active',
    created_at: '2026-10-27T10:00:00Z',
    revised_at: '2026-10-27T11:00:00Z',
    revised_by: ADMIN_UID,
    ...over,
  };
}

function seeded(items: readonly AnalysisPreset[]): Client {
  const client = newClient();
  seedExecutors(client, ALL_CASES);
  client.setQueryData(ANALYSIS_PRESETS_KEY, { items: [...items] });
  return client;
}

const section = (client: Client, roles: readonly ('admin' | 'expert')[]): string =>
  renderWith(client, createElement(AnalysisPresets, { roles }));

const choices = executorChoices(
  ALL_CASES.map((one) => one.connection),
  new Map(ALL_CASES.map((one) => [one.connection.connection_id, one.detail] as const)),
);
const BLOCKED = ALL_CASES.find((one) => {
  const blocker = choices.find((c) => c.connectionId === one.connection.connection_id)?.blocker;
  return blocker !== undefined && blocker !== null;
});

function apiError(status: number, errorCode: string, details: Record<string, unknown> = {}): ApiError {
  const envelope = {
    error_code: errorCode, message: 'x', retryable: false, correlation_id: 'cid-0123456789abcdef', details,
    contract_version: '1.11.0',
  } as unknown as ErrorEnvelope;
  return new ApiError(status, envelope, null);
}

// -- the settings section ---------------------------------------------------------------------

describe('the section «Пресеты запуска», as markup', () => {
  it('says what a preset is and what it is not, in plain words and without an identifier', () => {
    const markup = section(seeded([preset(1)]), ['expert']);
    expect(markup).toContain('Пресеты запуска');
    expect(markup).toContain('название и исполнитель');
    expect(markup).toContain('Предел стоимости прогона задаётся на стенде один для всех прогонов и в пресет не входит.');
    expect(markup).not.toMatch(/evt_|exc_|excr_/);
  });

  it('lists a preset with its name, its state, its version and its executor, to any role', () => {
    for (const roles of [['expert'], ['admin'], []] as const) {
      const markup = section(seeded([preset(1, { name: 'Быстрый черновик', revision_no: 3 })]), roles);
      expect(markup).toContain('data-preset-name');
      expect(markup).toContain('Быстрый черновик');
      expect(markup).toContain('Действует');
      expect(markup).toContain('версия');
      expect(markup).toContain('Исполнитель: «');
    }
  });

  it('offers the controls to an administrator only', () => {
    const items = [preset(1)];
    const admin = section(seeded(items), ['admin']);
    expect(admin).toContain('data-preset-create');
    expect(admin).toContain('data-preset-revise');
    expect(admin).toContain('В архив');
    expect(admin).toContain('Сохранить пресет');
    for (const roles of [['expert'], []] as const) {
      const markup = section(seeded(items), roles);
      expect(markup).not.toContain('data-preset-create');
      expect(markup).not.toContain('data-preset-revise');
      expect(markup).not.toContain('В архив');
      expect(markup).not.toContain('<form');
    }
  });

  it('keeps an archived preset apart, without a control, and says it is archived', () => {
    const markup = section(seeded([preset(1), preset(2, { state: 'archived', name: 'Старый', revision_no: 2 })]), ['admin']);
    expect(markup).toContain('data-preset-archive-list');
    expect(markup).toContain('Архив пресетов (1)');
    expect(markup).toContain('В архиве');
    expect(markup).toContain('Убран в архив');
    // the archived one has no «Изменить» and no «В архив» of its own: only the active one does
    expect(markup.match(/data-preset-revise/g)).toHaveLength(1);
  });

  it('says why a preset whose executor cannot serve now cannot start a run', () => {
    expect(BLOCKED, 'the fixtures hold a connection that cannot serve').toBeDefined();
    const blocked = preset(4, { executor_connection_id: BLOCKED!.connection.connection_id });
    const markup = section(seeded([preset(1), blocked]), ['expert']);
    expect(markup).toContain('data-preset-blocker');
    expect(markup).toContain('Сейчас этим пресетом прогон не запустить: исполнитель недоступен');
    expect(markup.match(/data-preset-blocker/g)).toHaveLength(1);
  });

  it('says so when the executor of a preset is not among the connections', () => {
    const lost = preset(5, { executor_connection_id: 'exc_01M2545JSD15ETSNNV904X9999' });
    const markup = section(seeded([lost]), ['expert']);
    expect(markup).toContain('исполнитель не найден в списке подключений');
  });

  it('shows the empty state to each audience in its own words', () => {
    expect(section(seeded([]), ['admin'])).toContain('Сохраните первый пресет ниже');
    expect(section(seeded([]), ['expert'])).toContain('Администратор ещё не сохранил ни одного пресета.');
  });

  it('shows a loading state and a failed read, with a retry and without an internal name', () => {
    const loading = renderWith(newClient(), createElement(AnalysisPresets, { roles: ['admin'] }));
    expect(loading).toContain('пресеты');
    const client = newClient();
    seedExecutors(client, ALL_CASES);
    client.getQueryCache().build(client, {
      queryKey: [...ANALYSIS_PRESETS_KEY],
      queryFn: async () => { throw apiError(503, 'dependency_unavailable'); },
    }).setState({
      data: undefined, status: 'error', error: apiError(503, 'dependency_unavailable'), errorUpdateCount: 1,
      fetchStatus: 'idle',
    } as never);
    const failed = renderWith(client, createElement(AnalysisPresets, { roles: ['admin'] }));
    expect(failed).toContain('Пресеты не прочитаны');
    expect(failed).toContain('data-analysis-presets-failure');
  });
});

// -- words ------------------------------------------------------------------------------------

describe('the entity decides what can start a run', () => {
  it('blocks an archived preset, an executor that is missing and one that cannot serve — and nothing else', () => {
    expect(presetBlocker(preset(1), choices)).toBeNull();
    expect(presetBlocker(preset(1, { state: 'archived' }), choices)).toBe('пресет в архиве');
    expect(presetBlocker(preset(1, { executor_connection_id: 'exc_01M2545JSD15ETSNNV904X9999' }), choices))
      .toBe('исполнитель не найден в списке подключений');
    expect(presetBlocker(preset(1, { executor_connection_id: BLOCKED!.connection.connection_id }), choices))
      .toMatch(/^исполнитель недоступен: /);
  });

  it('offers the active presets, and an archived one only while it is the one chosen', () => {
    const items = [preset(1), preset(2, { state: 'archived' })];
    expect(presetChoices(items, choices, null).map((c) => c.presetId)).toEqual([presetId(1)]);
    expect(presetChoices(items, choices, presetId(2)).map((c) => c.presetId)).toEqual([presetId(1), presetId(2)]);
    expect(presetChoices(items, choices, presetId(2))[1]?.blocker).toBe('пресет в архиве');
  });

  it('words an option with the reason when it cannot be chosen', () => {
    const [ok, blocked] = presetChoices([preset(1), preset(2, { state: 'archived' })], choices, presetId(2));
    expect(presetOptionLabel(ok!)).toBe('Пресет 1');
    expect(presetOptionLabel(blocked!)).toBe('Пресет 2 — недоступно: пресет в архиве');
  });

  it('words every refusal of a preset command in Russian and keeps an unknown outcome unknown', () => {
    const cases: Array<[string, Record<string, unknown>, RegExp]> = [
      ['validation_failed', { field: 'name', constraint: 'required' }, /нужно заполнить/],
      ['validation_failed', { field: 'name', constraint: 'max_length' }, /120 знаков/],
      ['validation_failed', { field: 'executor_connection_id', constraint: 'unknown_connection' }, /Такого исполнителя на стенде нет/],
      ['validation_failed', { field: 'name', constraint: 'differs_from_current' }, /Ничего не изменилось/],
      ['conflict', { conflict_reason: 'preset_name_in_use' }, /уже есть/],
      ['conflict', { conflict_reason: 'preset_limit_reached' }, /сто/],
      ['conflict', { conflict_reason: 'preset_archived' }, /в архиве/],
      ['conflict', { conflict_reason: 'connection_archived' }, /Исполнитель в архиве/],
    ];
    for (const [code, details, expected] of cases) {
      const failure = presetFailure(apiError(code === 'conflict' ? 409 : 422, code, details), true);
      expect(failure.detail).toMatch(expected);
      expect(failure.detail).not.toMatch(/[a-z]{4,}_[a-z]{3,}/);
    }
    expect(presetFailure(apiError(503, 'dependency_unavailable'), true).kind).toBe('unknown_outcome');
    expect(presetFailure(apiError(403, 'permission_denied'), true).kind).toBe('permission');
  });
});

// -- the commands, live -----------------------------------------------------------------------

describe('the commands, live', () => {
  let live: LiveRender | null = null;

  beforeEach(() => {
    vi.resetAllMocks();
    // a command refreshes the list, and the refresh is a read like any other: the transport is the mock
    vi.mocked(listAnalysisPresets).mockResolvedValue({ data: { items: [] } } as never);
    vi.mocked(createAnalysisPreset).mockResolvedValue({ data: preset(9) } as never);
    vi.mocked(reviseAnalysisPreset).mockResolvedValue({ data: preset(1, { revision_no: 2 }) } as never);
    vi.mocked(archiveAnalysisPreset).mockResolvedValue({ data: preset(1, { state: 'archived', revision_no: 2 }) } as never);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mount(items: readonly AnalysisPreset[]): Promise<LiveRender> {
    live = await mountLive(createElement(QueryClientProvider, { client: seeded(items) },
      createElement(AnalysisPresets, { roles: ['admin'] })));
    return live;
  }

  it('sends a save as exactly {name, executor_connection_id} and clears the form', async () => {
    const view = await mount([]);
    await view.change('Название пресета', 'Быстрый черновик');
    await view.change('Исполнитель', READY.connection.connection_id);
    expect(await view.press('Сохранить пресет')).toBe(true);
    expect(createAnalysisPreset).toHaveBeenCalledTimes(1);
    const call = vi.mocked(createAnalysisPreset).mock.calls[0]![0] as { body: Record<string, unknown>; idempotencyKey: string };
    expect(call.body).toEqual({ name: 'Быстрый черновик', executor_connection_id: READY.connection.connection_id });
    expect(call.idempotencyKey).toMatch(/\S{8,}/);
  });

  it('repeats a refused save under the same key and mints a new key once a save has settled', async () => {
    vi.mocked(createAnalysisPreset).mockRejectedValueOnce(apiError(503, 'dependency_unavailable'));
    const view = await mount([]);
    await view.change('Название пресета', 'Быстрый черновик');
    await view.change('Исполнитель', READY.connection.connection_id);
    await view.press('Сохранить пресет');
    expect(view.markup()).toContain('Исход команды неизвестен');
    await view.press('Сохранить пресет');
    // the form is empty after a save; the next one is another intent
    await view.change('Название пресета', 'Быстрый черновик');
    await view.change('Исполнитель', READY.connection.connection_id);
    await view.press('Сохранить пресет');
    const keys = vi.mocked(createAnalysisPreset).mock.calls.map((call) => (call[0] as { idempotencyKey: string }).idempotencyKey);
    expect(keys).toHaveLength(3);
    expect(keys[0]).toBe(keys[1]);
    expect(keys[2]).not.toBe(keys[1]);
  });

  it('does not send a save with an empty name', async () => {
    const view = await mount([]);
    expect(await view.press('Сохранить пресет')).toBe(false); // disabled: nothing to send
    expect(createAnalysisPreset).not.toHaveBeenCalled();
  });

  it('archives with exactly the preset in the path, a key, and no body, after one confirmation', async () => {
    const view = await mount([preset(1)]);
    await view.press('В архив');
    expect(view.markup()).toContain('уйдёт в архив насовсем');
    expect(archiveAnalysisPreset).not.toHaveBeenCalled();
    await view.press('Убрать в архив');
    expect(archiveAnalysisPreset).toHaveBeenCalledTimes(1);
    const call = vi.mocked(archiveAnalysisPreset).mock.calls[0]![0] as { path: { preset_id: string }; idempotencyKey: string };
    expect(call.path.preset_id).toBe(presetId(1));
    expect(call.idempotencyKey).toMatch(/\S{8,}/);
    expect(call).not.toHaveProperty('body');
  });

  it('shows the refusal of a command in words and offers no other action in its place', async () => {
    vi.mocked(archiveAnalysisPreset).mockRejectedValue(apiError(409, 'conflict', { conflict_reason: 'preset_archived' }));
    const view = await mount([preset(1)]);
    await view.press('В архив');
    await view.press('Убрать в архив');
    expect(view.markup()).toContain('Команда пресету не выполнена');
    expect(view.markup()).toContain('Пресет в архиве: его нельзя ни изменить, ни выбрать для прогона.');
  });
});

// -- run start --------------------------------------------------------------------------------

describe('the start request', () => {
  const version = VERSION_UID;

  it('carries the preset and not the executor, and is what it was without either', () => {
    expect(startRunBody(startRunIntent(version, null, null).command('k'))).toEqual({ version_uid: version });
    expect(startRunBody(startRunIntent(version, 'exc_X' as never, null).command('k'))).toEqual({
      version_uid: version, executor_connection_id: 'exc_X' });
    expect(startRunBody(startRunIntent(version, null, presetId(1) as never).command('k'))).toEqual({
      version_uid: version, preset_id: presetId(1) });
    // a preset wins: the control never offers both and the request never carries both
    expect(startRunBody(startRunIntent(version, 'exc_X' as never, presetId(1) as never).command('k'))).toEqual({
      version_uid: version, preset_id: presetId(1) });
  });

  it('never puts the executor beside the preset, whatever command it is handed', () => {
    const both = { versionUid: VERSION_UID, idempotencyKey: 'k', executorConnectionId: 'exc_X', presetId: presetId(1) };
    expect(startRunBody(both as never)).toEqual({ version_uid: VERSION_UID, preset_id: presetId(1) });
  });

  it('is another intent for another preset, and the signature without a preset is the one it always had', () => {
    const a = startRunIntent(version, null, presetId(1) as never).signature;
    const b = startRunIntent(version, null, presetId(2) as never).signature;
    expect(a).not.toBe(b);
    expect(startRunIntent(version, null).signature).toBe(`start-run:${version}`);
    expect(startRunIntent(version, 'exc_X' as never).signature).toBe(`start-run:${version}:executor:exc_X`);
    expect(a).not.toBe(startRunIntent(version, 'exc_X' as never).signature);
  });
});

describe('the start control', () => {
  const control = (client: Client): string =>
    renderWith(client, createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
  const options = (markup: string) =>
    [...markup.matchAll(/<option\b([^>]*)>([^<]*)<\/option>/g)].map((m) => [m[1] ?? '', m[2] ?? ''] as const);

  it('draws «Пресет» before «Исполнитель», both with their default option', () => {
    const markup = control(seeded([preset(1), preset(2, { state: 'archived' })]));
    expect(markup.match(/<select\b/g)).toHaveLength(2);
    expect(markup.indexOf('>Пресет</label>')).toBeGreaterThan(-1);
    expect(markup.indexOf('>Пресет</label>')).toBeLessThan(markup.indexOf('>Исполнитель</label>'));
    const labels = options(markup).map(([, text]) => text);
    expect(labels).toContain('Без пресета');
    expect(labels).toContain('По умолчанию (маршрут)');
    expect(labels).toContain('Пресет 1');
    expect(labels.join('|')).not.toContain('Пресет 2'); // an archived preset is not offered
  });

  it('lists a preset whose executor cannot serve disabled, with the reason', () => {
    const markup = control(seeded([preset(4, { name: 'Нерабочий', executor_connection_id: BLOCKED!.connection.connection_id })]));
    const [attrs, text] = options(markup).find(([, t]) => t.startsWith('Нерабочий')) ?? ['', ''];
    expect(attrs).toContain('disabled');
    expect(text).toContain('— недоступно: исполнитель недоступен');
  });

  it('says the presets are unread and still lets a run start without one', () => {
    const client = newClient();
    seedExecutors(client, [READY, SPARE]);
    client.getQueryCache().build(client, {
      queryKey: [...ANALYSIS_PRESETS_KEY], queryFn: async () => { throw apiError(503, 'dependency_unavailable'); },
    }).setState({
      data: undefined, status: 'error', error: apiError(503, 'dependency_unavailable'), errorUpdateCount: 1,
      fetchStatus: 'idle',
    } as never);
    const markup = control(client);
    expect(markup).toContain('data-preset-list-failure');
    expect(markup).toContain('Прогон можно запустить и без пресета.');
    expect(markup).toMatch(/<button type="button" class="am-button">Запустить прогон<\/button>/);
  });
});

describe('the start control, live', () => {
  let live: LiveRender | null = null;

  beforeEach(() => {
    vi.resetAllMocks();
    vi.mocked(startRun).mockResolvedValue({ data: { run_id: 'run_01M2545JSD15ETSNNV904X993K' } } as never);
  });

  afterEach(async () => {
    await live?.unmount();
    live = null;
  });

  async function mountControl(items: readonly AnalysisPreset[]): Promise<LiveRender> {
    live = await mountLive(createElement(QueryClientProvider, { client: seeded(items) },
      createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    return live;
  }

  const body = (): Record<string, unknown> =>
    (vi.mocked(startRun).mock.calls.at(-1)![0] as { body: Record<string, unknown> }).body;

  it('sends the preset and not the executor beside it, and locks the executor select while a preset is chosen', async () => {
    const view = await mountControl([preset(1, { name: 'Быстрый черновик' })]);
    expect(await view.change('Исполнитель', READY.connection.connection_id)).toBe(true); // a hand choice first
    expect(await view.change('Пресет', presetId(1))).toBe(true);
    expect(view.markup()).toContain('Исполнитель задан пресетом «Быстрый черновик». Чтобы выбрать другого, снимите пресет.');
    expect(await view.change('Исполнитель', SPARE.connection.connection_id)).toBe(false); // locked
    await view.press('Запустить прогон');
    expect(startRun).toHaveBeenCalledTimes(1);
    expect(body()).toEqual({ version_uid: VERSION_UID, preset_id: presetId(1) });
  });

  it('forgets the hand-chosen executor when a preset is chosen, and returns to the route when it is taken off', async () => {
    const view = await mountControl([preset(1)]);
    await view.change('Исполнитель', READY.connection.connection_id);
    await view.change('Пресет', presetId(1));
    await view.change('Пресет', '');
    await view.press('Запустить прогон');
    expect(body()).toEqual({ version_uid: VERSION_UID });
  });

  it('keeps the executor choice by hand when no preset is chosen', async () => {
    const view = await mountControl([preset(1)]);
    await view.change('Исполнитель', READY.connection.connection_id);
    await view.press('Запустить прогон');
    expect(body()).toEqual({ version_uid: VERSION_UID, executor_connection_id: READY.connection.connection_id });
  });

  it('uses one key for the same intent and another for another preset', async () => {
    const view = await mountControl([preset(1), preset(2)]);
    await view.change('Пресет', presetId(1));
    await view.press('Запустить прогон');
    await view.press('Запустить прогон');
    await view.change('Пресет', presetId(2));
    await view.press('Запустить прогон');
    const keys = vi.mocked(startRun).mock.calls.map((call) => (call[0] as { idempotencyKey: string }).idempotencyKey);
    expect(keys).toHaveLength(3);
    expect(keys[0]).toBe(keys[1]);
    expect(keys[2]).not.toBe(keys[0]);
  });

  it('sends the version alone when no preset and no executor was chosen, as it always did', async () => {
    live = await mountLive(createElement(QueryClientProvider, { client: seeded([preset(1)]) },
      createElement(StartRunControl, { projectUid: PROJECT_UID, versionUid: VERSION_UID })));
    await live.press('Запустить прогон');
    expect(startRun).toHaveBeenCalledTimes(1);
    const call = vi.mocked(startRun).mock.calls[0]![0] as { body: Record<string, unknown> };
    expect(call.body).toEqual({ version_uid: VERSION_UID });
  });
});

// -- the run ----------------------------------------------------------------------------------

describe('the preset on a run', () => {
  const run = (over: Partial<RunStatus>): Pick<RunStatus, 'preset'> => over as Pick<RunStatus, 'preset'>;

  it('shows the name the preset had and the version, and nothing for a run with none', () => {
    const line = runPresetLine(run({ preset: { preset_id: presetId(1), revision_no: 2, name: 'Быстрый черновик' } }));
    expect(line).toEqual({ name: 'Быстрый черновик', revisionNo: 2 });
    expect(runPresetValue(line!)).toBe('«Быстрый черновик», версия 2');
    expect(runPresetSentence(line!)).toBe('Пресет «Быстрый черновик», версия 2');
    expect(runPresetLine(run({}))).toBeNull();
    expect(runPresetLine(run({ preset: null }))).toBeNull();
    expect(runPresetLine(run({ preset: { preset_id: presetId(1), revision_no: 1, name: '  ' } }))).toBeNull();
  });
});

describe('the preset on the run page and the run row', () => {
  const PRESET = { preset_id: presetId(1), revision_no: 2, name: 'Быстрый черновик' };

  function page(over: Partial<RunStatus>): string {
    const status = runStatus(over);
    const client = newClient();
    client.setQueryData(queryKeys.runs.detail(status.run_id), status);
    return renderWith(client, createElement(RunProgress, { projectUid: PROJECT_UID, runId: status.run_id }));
  }

  it('names the preset and its version on the run page, beside the executor', () => {
    const markup = page({ preset: PRESET });
    expect(markup).toContain('<dt>Пресет</dt>');
    expect(markup).toContain('data-run-preset');
    expect(markup).toContain('«Быстрый черновик», версия 2');
    expect(markup).not.toMatch(/evt_/);
  });

  it('draws nothing for a run that had no preset', () => {
    for (const over of [{}, { preset: null }] as Partial<RunStatus>[]) {
      const markup = page(over);
      expect(markup).not.toContain('data-run-preset');
      expect(markup).not.toContain('<dt>Пресет</dt>');
    }
  });

  it('names the preset on the run list row, and nothing on a row without one', () => {
    const withPreset = render(createElement(RunRow, { run: runStatus({ preset: PRESET }), href: '/run' }));
    expect(withPreset).toContain('data-run-preset');
    expect(withPreset).toContain('Пресет «Быстрый черновик», версия 2');
    const without = render(createElement(RunRow, { run: runStatus({}), href: '/run' }));
    expect(without).not.toContain('data-run-preset');
  });
});

describe('a refused start names the preset as itself', () => {
  it('words the three refusals, offers no retry and never speaks of another preset or the route as a substitute', () => {
    const unknown = classifyRunFailure(apiError(422, 'validation_failed', { field: 'preset_id', constraint: 'unknown_preset' }));
    const archived = classifyRunFailure(apiError(409, 'conflict', { conflict_reason: 'preset_archived' }));
    const both = classifyRunFailure(apiError(422, 'validation_failed', { field: 'preset_id', constraint: 'conflicts_with_executor_connection_id' }));
    expect([unknown.kind, archived.kind, both.kind]).toEqual(['preset_unknown', 'preset_archived', 'preset_with_executor']);
    for (const failure of [unknown, archived, both]) {
      expect(failure.presentation).toBe('unsupported');
      expect(failure.detail).toContain('Прогон не запущен.');
    }
    expect(unknown.detail).toContain('не запускается ни с каким другим');
  });
});

void executorCase;
