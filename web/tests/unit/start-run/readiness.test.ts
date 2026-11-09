/**
 * `READINESS-WEB-01` (plan 2026-11-09 §8): the line under «Запустить», the blocked state, the plan window and the lines of the cost
 * dialog.
 *
 * The rules of the line are functions, so each is a call. The widget that mounts the control is read from a live mount over a seeded
 * cache (`getRunStartReadiness` is mocked where a read is the claim), and the states a cache holds after a refusal from a static
 * render. Each claim has a negative that can fail: a mutation that ignores `blockedReason`, draws «Изменить» for an expert, shows a
 * fact column in the plan window or keeps the old line after a 503 turns one of these red.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  estimateRunCost: vi.fn(),
  getRunStartReadiness: vi.fn(),
  startRun: vi.fn(),
}));

import { ApiError, estimateRunCost, getRunStartReadiness, queryKeys, startRun } from '@/shared/api';
import type { ErrorCode, Role, RunStartReadiness } from '@/shared/api';
import { readinessPlan } from '@/entities/stage-layout';
import {
  ACCESS_WORDS, CLIENT_DOCUMENTS_MARK, CONNECT_SERVER, CONTACT_ADMIN, LEGACY_ROUTE_NOTE, NOT_READY, StartRunCostDialogView,
  blockedModels, layoutNotAvailable, readinessLine, runStartReadinessKey,
} from '@/features/start-run';
import { MODELS_BY_STAGE_ADDRESS, StartRunWithReadiness } from '@/widgets/run-list';
import { PlanStagesDialog } from '@/widgets/run-stages-dialog';

import { PROJECT_UID, VERSION_UID } from '../review/fixtures';
import { newClient, renderScreen, seedError } from '../screens/harness';
import { costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import {
  CLAUDE_CELLS, DIGEST, ENSEMBLE_CELLS, READINESS_API, READINESS_LEGACY, READINESS_MIXED, blockedReadiness, missingCell, modelLines,
  readiness, readinessCell,
} from './readiness-fixtures';

const BUTTON = ['data-start-run-button', ''] as const;
const STAGES = ['data-readiness-stages', ''] as const;
const CLOSE = ['data-run-stages-close', ''] as const;
const RUN = { run_id: 'run_01M2545JSD15ETSNNV904X993K' };
const NNBSP = '\u202f';

/** The text of the line under the button, as a person reads it. */
function lineOf(markup: string): string {
  const found = /data-start-readiness="[^"]*">(.*?)<\/p>/s.exec(markup);
  if (found === null) throw new Error('no readiness line');
  return (found[1] ?? '').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
}

const reasonOf = (markup: string): string | null => {
  const found = /data-start-blocked="[^"]*">(.*?)<\/p>/s.exec(markup);
  return found === null ? null : (found[1] ?? '').replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
};

function refusal(status: number, code: ErrorCode, details: Record<string, string> = {}): ApiError {
  return new ApiError(status, {
    contract_version: '1.45.0', error_code: code, message: 'refused', correlation_id: 'cid-readiness', retryable: false, details,
  }, 'cid-readiness');
}

let live: LiveRender | null = null;

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getRunStartReadiness).mockResolvedValue({ data: readiness() } as never);
  vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body) }) as never);
  vi.mocked(startRun).mockResolvedValue({ data: RUN } as never);
});
afterEach(async () => { await live?.unmount(); live = null; });

function seededClient(roles: readonly Role[], answer: RunStartReadiness | null) {
  const cache = newClient();
  cache.setQueryData(queryKeys.account.me(), { roles });
  if (answer !== null) cache.setQueryData(runStartReadinessKey(VERSION_UID), answer);
  return cache;
}

async function mount(options: { roles?: readonly Role[]; answer?: RunStartReadiness | null; initiallyOpen?: boolean } = {}) {
  const cache = seededClient(options.roles ?? ['expert'], options.answer === undefined ? readiness() : options.answer);
  live = await mountLive(createElement(QueryClientProvider, { client: cache }, createElement(StartRunWithReadiness, {
    projectUid: PROJECT_UID, versionUid: VERSION_UID, ...(options.initiallyOpen === true ? { initiallyOpen: true } : {}),
  })));
  return { view: live, cache };
}

/** A static render of the widget over a cache the caller has filled, for the states a refusal leaves. */
function rendered(roles: readonly Role[], fill: (cache: ReturnType<typeof newClient>) => void): string {
  const cache = seededClient(roles, null);
  fill(cache);
  return renderScreen(cache, createElement(StartRunWithReadiness, { projectUid: PROJECT_UID, versionUid: VERSION_UID }));
}

describe('the words of the line', () => {
  it('names the set, how it is paid and nothing the answer did not say', () => {
    expect(readinessLine(readiness())).toEqual({ kind: 'plan', kit: 'Только Claude', access: 'по подписке' });
    expect(readinessLine(readiness({ kit: 'codex_only' }))).toEqual({ kind: 'plan', kit: 'Только Codex', access: 'по подписке' });
    expect(readinessLine(readiness({ kit: 'custom' }))).toEqual({ kind: 'plan', kit: 'Свой набор', access: 'по подписке' });
    // No set before the first revision, no total while a cell has no server: the line leaves them out rather than invent them.
    const bare = readiness();
    delete bare.kit;
    delete bare.access;
    expect(readinessLine(bare)).toEqual({ kind: 'plan', kit: null, access: null });
  });

  it('says a part by API as «часть по API — покажем оценку», and all of it as «по API — покажем оценку»', () => {
    expect(ACCESS_WORDS.subscription).toBe('по подписке');
    expect(ACCESS_WORDS.mixed).toBe('часть по API — покажем оценку');
    expect(ACCESS_WORDS.api).toBe('по API — покажем оценку');
    expect(readinessLine(READINESS_MIXED)).toMatchObject({ access: 'часть по API — покажем оценку' });
    expect(readinessLine(READINESS_API)).toMatchObject({ access: 'по API — покажем оценку' });
  });

  it('is «Маршрут: прежний» when the layout is off', () => {
    expect(readinessLine(READINESS_LEGACY)).toEqual({ kind: 'legacy' });
    expect(LEGACY_ROUTE_NOTE).toBe('Маршрут: прежний');
  });

  it('holds the D-291 mark short, and a typed 503 is the only answer that means «no layout»', () => {
    expect(CLIENT_DOCUMENTS_MARK).toBe('⚠ не для клиентских документов');
    expect(layoutNotAvailable(refusal(503, 'dependency_unavailable'))).toBe(true);
    expect(layoutNotAvailable(refusal(500, 'internal_error'))).toBe(false);
    expect(layoutNotAvailable(refusal(403, 'permission_denied'))).toBe(false);
    expect(layoutNotAvailable(new TypeError('Failed to fetch'))).toBe(false);
  });
});

describe('what blocks the start', () => {
  it('names the model that is missing and the row that needs it', () => {
    expect(blockedModels(blockedReadiness())).toBe('Нет Opus 5.5 — Анализ блоков');
  });

  it('says every missing model once, and a model both legs of a row name once for that row', () => {
    const cells = [
      readinessCell('text', 'claude-sonnet-5-5'),
      missingCell('blocks', 'gpt-6-astra', 'leg1'),
      missingCell('blocks', 'gpt-6-astra', 'leg2'),
      missingCell('norms', 'gpt-6-sol'),
    ];
    expect(blockedModels(readiness({ ready: false, cells }))).toBe('Нет gpt-6-astra — Анализ блоков; Нет gpt-6-sol — Нормы');
  });

  it('blocks nothing while the answer is ready, and nothing at all on the old route', () => {
    expect(blockedModels(readiness())).toBeNull();
    expect(blockedModels(READINESS_MIXED)).toBeNull();
    // `ready: false` with the layout off is not a reason: the route is the one as before.
    expect(blockedModels({ ...READINESS_LEGACY, ready: false })).toBeNull();
  });

  it('says so when the answer is not ready and names no cell, instead of hiding it', () => {
    expect(blockedModels(readiness({ ready: false }))).toBe(NOT_READY);
  });
});

describe('the plan the window shows', () => {
  it('lists the rows in the original\'s order and the cells of a row legs first, judge last', () => {
    const rows = readinessPlan(ENSEMBLE_CELLS);
    expect(rows.map((row) => row.row)).toEqual(['text', 'blocks']);
    expect(rows[1]?.cells.map((cell) => `${cell.role}:${cell.model}:${cell.effortLabel}`)).toEqual([
      'leg1:Opus 5.5:высокое', 'leg2:gpt-6-astra:среднее', 'judge:Sonnet 5.5:среднее',
    ]);
  });

  it('leaves out a row the run does not take, rather than inventing the six', () => {
    expect(readinessPlan(CLAUDE_CELLS).map((row) => row.row)).toEqual(['text', 'blocks', 'cross_check', 'norms']);
    expect(readinessPlan([])).toEqual([]);
  });
});

describe('the line under the button', () => {
  it('says the set, the access, the D-291 mark and the way to the stages, in one line', async () => {
    const { view } = await mount();
    expect(lineOf(view.markup())).toBe('Набор: Только Claude · по подписке · ⚠ не для клиентских документов · Модели по этапам ▸');
    expect(view.markup()).not.toContain('Маршрут:');
    expect(view.count('Запустить')).toBe(1);
  });

  it('says «часть по API — покажем оценку» for a part by API, and «по подписке» only when none is', async () => {
    const mixed = await mount({ answer: READINESS_MIXED });
    expect(lineOf(mixed.view.markup())).toContain('Набор: Только Claude · часть по API — покажем оценку · ');
    expect(lineOf(mixed.view.markup())).not.toContain('по подписке');
    await live?.unmount();
    const subscription = await mount();
    expect(lineOf(subscription.view.markup())).toContain('по подписке');
    expect(lineOf(subscription.view.markup())).not.toContain('API');
  });

  it('says «Маршрут: прежний», with no set, no mark and no way to the stages, when the layout is off', async () => {
    const { view } = await mount({ answer: READINESS_LEGACY });
    expect(lineOf(view.markup())).toBe('Маршрут: прежний');
    expect(view.markup()).not.toContain('data-readiness-stages');
    expect(view.markup()).not.toContain('data-readiness-d291');
    // Nothing blocks the old route: the button is the one it always was.
    expect(await view.pressMarked(...BUTTON)).toBe(true);
  });

  it('asks for the same body as the estimate and for nothing else', async () => {
    const { view } = await mount({ answer: null });
    await view.settle(() => undefined);
    expect(getRunStartReadiness).toHaveBeenCalledTimes(1);
    expect(getRunStartReadiness).toHaveBeenCalledWith({ body: { version_uid: VERSION_UID } });
    expect(Object.keys(vi.mocked(getRunStartReadiness).mock.calls[0]![0].body)).toEqual(['version_uid']);
    // The answer reaches the line.
    expect(lineOf(view.markup())).toContain('Набор: Только Claude');
  });

  it('reads nothing for the viewer, who is offered no start', async () => {
    const { view } = await mount({ roles: ['viewer'], answer: null });
    expect(getRunStartReadiness).not.toHaveBeenCalled();
    expect(view.markup()).toContain('Запускать анализ может эксперт.');
    expect(view.markup()).not.toContain('data-start-readiness');
  });

  it('is read again when the server sends the start back because the access changed', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({
      data: { ...costEstimate(body), billing: 'unmetered', estimated_cost_micros: 0, recommended_ceiling_micros: 0 },
    }) as never);
    vi.mocked(startRun).mockRejectedValueOnce(refusal(422, 'analysis_input_invalid', { reason: 'cost_estimate_binding_changed' }));
    vi.mocked(getRunStartReadiness).mockResolvedValue({ data: READINESS_MIXED } as never);
    const { view } = await mount();
    expect(getRunStartReadiness).not.toHaveBeenCalled();
    await view.pressMarked(...BUTTON);
    expect(getRunStartReadiness).toHaveBeenCalledTimes(1);
    expect(lineOf(view.markup())).toContain('часть по API — покажем оценку');
  });
});

describe('when the plan names a model no server has', () => {
  it('makes the button inactive, sends nothing, and says why to an expert', async () => {
    const { view } = await mount({ answer: blockedReadiness() });
    expect(await view.pressMarked(...BUTTON)).toBe(false);
    expect(estimateRunCost).not.toHaveBeenCalled();
    expect(startRun).not.toHaveBeenCalled();
    expect(reasonOf(view.markup())).toBe(`Нет Opus 5.5 — Анализ блоков · ${CONTACT_ADMIN}`);
    expect(reasonOf(view.markup())).toBe('Нет Opus 5.5 — Анализ блоков · обратитесь к администратору');
    // The second way to start the same run is not offered either, and the line still says the set and the way to the stages.
    expect(view.markup()).not.toContain('data-start-run-more');
    expect(lineOf(view.markup())).toContain('Набор: Только Claude');
    expect(lineOf(view.markup())).not.toContain('по подписке');
  });

  it('tells an administrator what to do, with the way there, instead of whom to ask', async () => {
    const { view } = await mount({ roles: ['admin', 'expert'], answer: blockedReadiness() });
    expect(await view.pressMarked(...BUTTON)).toBe(false);
    const reason = reasonOf(view.markup());
    expect(reason).toBe(`Нет Opus 5.5 — Анализ блоков · ${CONNECT_SERVER}`);
    expect(reason).not.toContain(CONTACT_ADMIN);
    expect(view.markup()).toContain('href="/workers"');
  });

  it('draws no reason and keeps the start while every cell has a server', async () => {
    const { view } = await mount({ answer: READINESS_MIXED });
    expect(view.markup()).not.toContain('data-start-blocked');
    expect(view.markup()).toContain('data-start-run-more');
    expect(await view.pressMarked(...BUTTON)).toBe(true);
    expect(estimateRunCost).toHaveBeenCalledTimes(1);
  });
});

describe('«Модели по этапам ▸» opens the stage window in plan mode', () => {
  it('opens it with the plan and no fact column, and closes it', async () => {
    const { view } = await mount();
    expect(view.markup()).not.toContain('data-stages-plan');
    expect(await view.pressMarked(...STAGES)).toBe(true);
    const markup = view.markup();
    expect(markup).toContain('data-stages-plan');
    expect(markup).toContain('Этапы анализа раздела');
    // The plan: the first stage with a model, with its model, its effort and how it is paid.
    expect(markup).toContain('data-plan-only');
    expect(markup).toContain('data-plan-cell="text:main"');
    expect(markup).toContain('Sonnet 5.5');
    expect(markup).toContain('среднее');
    expect(markup).toContain('по подписке');
    // No fact: no state, start, end, duration, tokens or error code, and no start from this stage.
    for (const fact of ['Факт', 'data-fact-row', 'Состояние', 'Начало', 'Окончание', 'Длительность', 'Код ошибки', 'Запустить с этого этапа']) {
      expect(markup, fact).not.toContain(fact);
    }
    expect(await view.pressMarked(...CLOSE)).toBe(true);
    expect(view.markup()).not.toContain('data-stages-plan');
  });

  it('is drawn with «Изменить» for an administrator, leading to «Исполнители → Модели по этапам», and for nobody else', async () => {
    const admin = await mount({ roles: ['admin', 'expert'], initiallyOpen: true });
    expect(MODELS_BY_STAGE_ADDRESS).toBe('/workers?tab=models');
    expect(admin.view.markup()).toContain('data-plan-edit=""');
    expect(admin.view.markup()).toContain('href="/workers?tab=models"');
    expect(admin.view.markup()).toContain('>Изменить</a>');
    await live?.unmount();
    const expert = await mount({ roles: ['expert'], initiallyOpen: true });
    expect(expert.view.markup()).toContain('data-stages-plan');
    expect(expert.view.markup()).not.toContain('data-plan-edit');
    expect(expert.view.markup()).not.toContain('Изменить');
  });

  it('is not offered, and not drawn, when the layout is off', async () => {
    const { view } = await mount({ answer: READINESS_LEGACY, initiallyOpen: true });
    expect(view.markup()).not.toContain('data-stages-plan');
    expect(view.markup()).not.toContain('data-readiness-stages');
  });
});

describe('the plan window, drawn open', () => {
  const draw = (cells: Parameters<typeof readinessPlan>[0], extra: { kit?: string | null; editHref?: string } = {}) => renderToStaticMarkup(
    createElement(PlanStagesDialog, { rows: readinessPlan(cells), kit: extra.kit ?? 'Только Claude', onClose: () => undefined, staticOpen: true, ...(extra.editHref === undefined ? {} : { editHref: extra.editHref }) }),
  );

  it('lists the eight stages and what each does without a model', () => {
    const markup = draw(CLAUDE_CELLS);
    for (const stage of ['preparation', 'text', 'blocks', 'cross_check', 'merge', 'norms', 'review', 'correction']) {
      expect(markup, stage).toContain(`data-stage-item="${stage}"`);
    }
    // A stage that is in no run of this kind says so on the left, and a stage without a model says that.
    expect(markup).toContain('без модели');
    expect(markup).toContain('не входит в запуск');
  });

  it('says a cell no server has as such, in the cell, and marks nothing else', () => {
    // The first stage with a model is open: it is served, and carries no mark.
    expect(draw([readinessCell('text', 'claude-sonnet-5-5'), missingCell('blocks', 'claude-opus-5-5')])).not.toContain('data-plan-missing');
    // The stage with the gap, open: the cell says so, and says no access.
    const blocks = draw([missingCell('blocks', 'claude-opus-5-5')], { kit: null });
    expect(blocks).toContain('data-plan-missing');
    expect(blocks).toContain('⚠ нет на серверах');
    expect(blocks).toContain('data-plan-access="none"');
    expect(blocks).not.toContain('data-plan-kit');
    // A served cell says how it is paid, and the set is said once the answer names one.
    const served = draw([readinessCell('text', 'claude-sonnet-5-5', { access: 'api' })]);
    expect(served).toContain('по ключу API');
    expect(served).toContain('data-plan-kit="">Набор: Только Claude</p>');
  });

  it('shows the legs and the judge of a scheme as the rows of one table, with the role in front', () => {
    const markup = renderToStaticMarkup(createElement(PlanStagesDialog, {
      rows: readinessPlan(ENSEMBLE_CELLS.filter((cell) => cell.row === 'blocks')), kit: 'Только Claude', onClose: () => undefined, staticOpen: true,
    }));
    expect(markup).toContain('первая ветка: Opus 5.5');
    expect(markup).toContain('вторая ветка: gpt-6-astra');
    expect(markup).toContain('судья: Sonnet 5.5');
    expect(markup.indexOf('первая ветка')).toBeLessThan(markup.indexOf('судья'));
  });

  it('draws «Изменить» only for the link it is given', () => {
    expect(draw(CLAUDE_CELLS, { editHref: MODELS_BY_STAGE_ADDRESS })).toContain('data-plan-edit');
    expect(draw(CLAUDE_CELLS)).not.toContain('data-plan-edit');
  });
});

describe('a server with no layout, and a read that failed', () => {
  it('says «Маршрут: автоматически» after a typed 503, and the start stays', () => {
    const markup = rendered(['expert'], (cache) => seedError(cache, runStartReadinessKey(VERSION_UID), refusal(503, 'dependency_unavailable')));
    expect(lineOf(markup)).toBe('Маршрут: автоматически');
    expect(markup).not.toContain('data-readiness-stages');
    expect(markup).not.toContain('data-start-blocked');
    expect(markup).not.toContain('Готовность запуска не прочитана');
    // Not an error for the person: no error state, and the button is not held.
    expect(markup).not.toContain('role="alert"');
    expect(/data-start-run-button=""[^>]*disabled/.test(markup)).toBe(false);
  });

  it('says that the readiness was not read after any other refusal, and still leaves the start to the server', () => {
    const markup = rendered(['expert'], (cache) => seedError(cache, runStartReadinessKey(VERSION_UID), refusal(500, 'internal_error')));
    expect(lineOf(markup)).toContain('Готовность запуска не прочитана');
    expect(lineOf(markup)).not.toContain('Маршрут: автоматически');
    expect(markup).toContain('data-readiness-retry');
    expect(/data-start-run-button=""[^>]*disabled/.test(markup)).toBe(false);
  });

  it('does not take a comparison PDF\'s refusal for a failure of the line', () => {
    const markup = rendered(['expert'], (cache) => seedError(
      cache, runStartReadinessKey(VERSION_UID), refusal(422, 'analysis_input_invalid', { reason: 'comparison_only_version' }),
    ));
    expect(lineOf(markup)).toBe('Маршрут: автоматически');
  });

  it('says that it is checking while nothing has answered', () => {
    const markup = rendered(['expert'], () => undefined);
    expect(lineOf(markup)).toBe('Проверяем готовность…');
    expect(/data-start-run-button=""[^>]*disabled/.test(markup)).toBe(false);
  });
});

describe('the lines of the cost dialog', () => {
  const dialog = (over: Partial<ReturnType<typeof costEstimate>> = {}) => renderToStaticMarkup(createElement(StartRunCostDialogView, {
    estimate: { ...costEstimate({ version_uid: VERSION_UID }), ...over }, relaxed: false, ceiling: '1.5', changed: false, busy: false, staticOpen: true,
    onCeilingChange: () => undefined, onConfirm: () => undefined, onCancel: () => undefined,
  }));

  it('shows a line for each model, with how it is paid and what it costs, and then the total', () => {
    const markup = dialog({ billing: 'mixed', models: modelLines(), calls: 10, estimate_digest: DIGEST });
    expect(markup).toContain('data-estimate-models');
    expect(markup).toContain('>Opus 5.5 · по подписке · $0</li>');
    expect(markup).toContain('>Sonnet 5.5 · по ключу API · $1.2</li>');
    expect(markup).toContain('data-estimate-total="">Итого: $1.2.</p>');
    expect(markup.indexOf('Opus 5.5')).toBeLessThan(markup.indexOf('Sonnet 5.5'));
    expect(markup.indexOf('Sonnet 5.5')).toBeLessThan(markup.indexOf('Итого'));
    // The one «Модель:» sentence is the old estimate's; the counts stay.
    expect(markup).not.toContain('Модель:');
    expect(markup).not.toContain('Предварительная оценка: $');
    expect(markup).toContain(`Страниц: 2; символов: 3${NNBSP}000; окон: 1; вызовов: 10.`);
  });

  it('is what it was when the estimate names no model', () => {
    const markup = dialog();
    expect(markup).not.toContain('data-estimate-models');
    expect(markup).not.toContain('Итого');
    expect(markup).toContain('Предварительная оценка: $1.2.');
    expect(markup).toContain('Модель: fixture-model.');
    expect(dialog({ models: [] })).not.toContain('data-estimate-models');
  });

  it('opens from the control for a mixed estimate, with its lines', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({
      data: { ...costEstimate(body), billing: 'mixed', models: modelLines() },
    }) as never);
    const { view } = await mount({ answer: READINESS_MIXED });
    await view.pressMarked(...BUTTON);
    expect(view.markup()).toContain('data-start-run-dialog');
    expect(view.markup()).toContain('Opus 5.5 · по подписке · $0');
    expect(view.markup()).toContain('Sonnet 5.5 · по ключу API · $1.2');
    expect(startRun).not.toHaveBeenCalled();
  });
});
