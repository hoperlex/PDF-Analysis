/**
 * `RUN-START-ONE-01a` (plan v3 §8, rulings `R-153a`, `R-153f`): the start of one run is one button.
 *
 * Mounted live and pressed, because what is claimed is a sequence: the click reads the estimate; an
 * estimate that charges nothing is agreed to by the click itself and the run is sent with no dialog; an
 * estimate that can charge opens exactly one dialog; an answer that the estimate or its binding changed
 * is estimated again and shown. Each claim has a negative that can fail: the request is read for the
 * selectors it must not carry, and the markup for the controls that must not be there.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { createElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  estimateRunCost: vi.fn(),
  startRun: vi.fn(),
}));

import { ApiError, estimateRunCost, queryKeys, startRun } from '@/shared/api';
import type { RunCostEstimate, RunCostEstimateRequest } from '@/shared/api';
import { StartRunControl, UNCAPPED_START_LABEL } from '@/features/start-run';

import { PROJECT_UID, VERSION_UID } from '../review/fixtures';
import { newClient } from '../screens/harness';
import { COST_CONSENT, costEstimate } from '../analysis-settings/cost-estimate-fixtures';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';

const OTHER_VERSION = 'ver_01J9ZQ8K7NHVXW3T2R5M6P4Q8C';
const FREE_DIGEST = 'c'.repeat(64);
const NEXT_DIGEST = 'd'.repeat(64);
const RUN = { run_id: 'run_01M2545JSD15ETSNNV904X993K' };
const STALE = 'Оценка изменилась с прошлого раза';
const BUTTON = ['data-start-run-button', ''] as const;
const CONFIRM = ['data-start-run-confirm', ''] as const;
const CANCEL = ['data-start-run-cancel', ''] as const;

/** The estimate of a connection the application does not bill: 0, and a ceiling of 0. */
function freeEstimate(body: RunCostEstimateRequest, digest = FREE_DIGEST): RunCostEstimate {
  return { ...costEstimate(body), billing: 'unmetered', estimated_cost_micros: 0, recommended_ceiling_micros: 0, estimate_digest: digest };
}

function refusal(status: number, code: 'conflict' | 'analysis_input_invalid', details: Record<string, string>): ApiError {
  return new ApiError(status, {
    contract_version: '1.53.0', error_code: code, message: 'refused', correlation_id: 'cid-one-click', retryable: false, details,
  }, 'cid-one-click');
}

const stale = () => refusal(409, 'conflict', { conflict_reason: 'run_cost_estimate_stale' });
const bindingChanged = () => refusal(422, 'analysis_input_invalid', { reason: 'cost_estimate_binding_changed' });

let live: LiveRender | null = null;

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: costEstimate(body) }) as never);
  vi.mocked(startRun).mockResolvedValue({ data: RUN } as never);
});
afterEach(async () => { await live?.unmount(); live = null; });

function client(roles?: readonly string[]) {
  const result = newClient();
  if (roles !== undefined) result.setQueryData(queryKeys.account.me(), { roles });
  return result;
}

async function mount(options: { versionUid?: string; roles?: readonly string[]; onStarted?: (run: unknown) => void; readinessNote?: string } = {}) {
  const cache = client(options.roles);
  const tree = (versionUid: string) => createElement(QueryClientProvider, { client: cache },
    createElement(StartRunControl, {
      projectUid: PROJECT_UID, versionUid,
      ...(options.onStarted === undefined ? {} : { onStarted: options.onStarted }),
      ...(options.readinessNote === undefined ? {} : { readinessNote: options.readinessNote }),
    } as never));
  live = await mountLive(tree(options.versionUid ?? VERSION_UID));
  return { view: live, tree, cache };
}

const click = (view: LiveRender) => view.pressMarked(...BUTTON);
const sent = (index = -1) => vi.mocked(startRun).mock.calls.at(index)![0] as { body: Record<string, unknown>; idempotencyKey: string };
const dialogs = (view: LiveRender) => view.markup().match(/data-start-run-dialog/g)?.length ?? 0;

describe('the control is one button and a line', () => {
  it('draws «Запустить», «▾» and the readiness line, and none of what was removed', async () => {
    const { view } = await mount();
    const markup = view.markup();
    expect(view.count('Запустить')).toBe(1);
    expect(markup).toContain('data-start-run-more');
    expect(markup).toContain('Маршрут: автоматически');
    // No executor, group or preset selector; no choice of how the executor is chosen; no tick-box; no estimate button.
    expect(markup).not.toContain('<select');
    expect(markup).not.toContain('<option');
    // The live markup does not print an input's type, so the claim is that the control holds no input at all.
    expect(markup).not.toContain('<input');
    expect(markup).not.toContain('Как выбрать исполнителя');
    expect(markup).not.toContain('Исполнитель');
    expect(markup).not.toContain('Группа');
    expect(markup).not.toContain('Пресет');
    expect(markup).not.toContain('Временный режим сбора статистики');
    expect(view.count('Оценить стоимость')).toBe(0);
    expect(view.count('Запустить прогон')).toBe(0);
    // The dialog is not drawn until an estimate asks for it.
    expect(dialogs(view)).toBe(0);
  });

  it('holds the temporary mode in the «▾» menu, as the only item', async () => {
    const { view } = await mount();
    const markup = view.markup();
    expect(markup).toContain(`>${UNCAPPED_START_LABEL}</button>`);
    expect(UNCAPPED_START_LABEL).toBe('Без денежного потолка (сбор статистики)');
    expect(markup.match(/role="menuitem"/g)).toHaveLength(1);
    // The meaning the tick-box had stays as the tooltip of the menu.
    expect(markup).toContain('Прикладной денежный потолок отключён; фактические вызовы и расход записываются.');
  });

  it('shows the line the next wave passes in place of «Маршрут: автоматически», and invents none', async () => {
    const { view } = await mount({ readinessNote: 'Набор: Только Claude · по подписке' });
    expect(view.markup()).toContain('Набор: Только Claude · по подписке');
    expect(view.markup()).not.toContain('Маршрут: автоматически');
  });
});

describe('an estimate that charges nothing is agreed to by the click', () => {
  it('sends the run at once with the consent of that estimate, and opens no dialog', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: freeEstimate(body) }) as never);
    const onStarted = vi.fn();
    const { view } = await mount({ onStarted });
    expect(await click(view)).toBe(true);
    expect(estimateRunCost).toHaveBeenCalledTimes(1);
    expect(estimateRunCost).toHaveBeenCalledWith({ body: { version_uid: VERSION_UID } });
    expect(startRun).toHaveBeenCalledTimes(1);
    expect(sent().body).toEqual({
      version_uid: VERSION_UID, cost_consent: { estimate_digest: FREE_DIGEST, ceiling_micros: 0, confirmed: true },
    });
    expect(dialogs(view)).toBe(0);
    expect(onStarted).toHaveBeenCalledWith(RUN);
  });

  it('keeps one key for one intent: the same estimate sent again is the same request', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: freeEstimate(body) }) as never);
    vi.mocked(startRun).mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const { view } = await mount();
    await click(view);
    await click(view);
    expect(startRun).toHaveBeenCalledTimes(2);
    expect(sent(1).idempotencyKey).toBe(sent(0).idempotencyKey);
    expect(sent(1).body).toEqual(sent(0).body);
  });

  it('is another intent when the estimate it agrees to is another one', async () => {
    vi.mocked(estimateRunCost)
      .mockImplementationOnce(async ({ body }) => ({ data: freeEstimate(body) }) as never)
      .mockImplementationOnce(async ({ body }) => ({ data: freeEstimate(body, NEXT_DIGEST) }) as never);
    vi.mocked(startRun).mockRejectedValueOnce(new TypeError('Failed to fetch'));
    const { view } = await mount();
    await click(view);
    await click(view);
    expect(sent(1).body.cost_consent).toEqual({ estimate_digest: NEXT_DIGEST, ceiling_micros: 0, confirmed: true });
    expect(sent(1).idempotencyKey).not.toBe(sent(0).idempotencyKey);
  });
});

describe('an estimate that can charge opens exactly one dialog', () => {
  it('shows the estimate and the ceiling, sends nothing, and waits for «Запустить» in the dialog', async () => {
    const { view } = await mount();
    await click(view);
    expect(dialogs(view)).toBe(1);
    expect(startRun).not.toHaveBeenCalled();
    const markup = view.markup();
    expect(markup).toContain('Предварительная оценка: $1.2.');
    expect(markup).toContain('Модель: fixture-model.');
    expect(markup).toContain('Рекомендуемый лимит: $1.5.');
    // `RUN-START-ONE-01b`: the optional subject line belongs to the queue's repeated Run; the start control draws none.
    expect(markup).not.toContain('data-start-run-subject');
    expect(view.count('Отмена')).toBe(1);
    // «Запустить» of the control is held while the dialog is open, and the dialog has its own.
    expect(await click(view)).toBe(false);
    expect(await view.pressMarked(...CONFIRM)).toBe(true);
    expect(startRun).toHaveBeenCalledTimes(1);
    expect(sent().body).toEqual({ version_uid: VERSION_UID, cost_consent: COST_CONSENT });
    expect(dialogs(view)).toBe(0);
  });

  it('is the only agreement: no tick-box, and the ceiling typed is the ceiling sent', async () => {
    const { view } = await mount();
    await click(view);
    // The only input of the dialog is the ceiling's text field: no second tick-box, no «Подтверждаю».
    expect(view.markup().match(/<input/g)).toHaveLength(1);
    expect(view.markup()).not.toContain('Подтверждаю');
    expect(await view.change('Лимит стоимости, $', '2.000001')).toBe(true);
    await view.pressMarked(...CONFIRM);
    expect(sent().body.cost_consent).toEqual({ ...COST_CONSENT, ceiling_micros: 2_000_001 });
  });

  it('keeps «Запустить» of the dialog disabled while the ceiling cannot cover the estimate', async () => {
    const { view } = await mount();
    await click(view);
    await view.change('Лимит стоимости, $', '1.1');
    expect(await view.pressMarked(...CONFIRM)).toBe(false);
    expect(view.markup()).toContain('Введите конечный лимит не ниже оценки');
    expect(startRun).not.toHaveBeenCalled();
  });

  it('«Отмена» sends nothing and closes the dialog, and the next click starts over', async () => {
    const { view } = await mount();
    await click(view);
    expect(await view.pressMarked(...CANCEL)).toBe(true);
    expect(dialogs(view)).toBe(0);
    expect(startRun).not.toHaveBeenCalled();
    await click(view);
    expect(dialogs(view)).toBe(1);
    expect(estimateRunCost).toHaveBeenCalledTimes(2);
  });

  it('a metered estimate priced at 0 is still asked about: only an unmetered one is free', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({
      data: { ...costEstimate(body), estimated_cost_micros: 0, recommended_ceiling_micros: 1 },
    }) as never);
    const { view } = await mount();
    await click(view);
    expect(dialogs(view)).toBe(1);
    expect(startRun).not.toHaveBeenCalled();
  });

  it('retries a refused send under the same key and the same consent, without a new estimate', async () => {
    vi.mocked(startRun).mockRejectedValueOnce(new ApiError(503, {
      contract_version: '1.53.0', error_code: 'dependency_unavailable', message: 'down', correlation_id: 'cid-down',
      retryable: true, details: { dependency: 'model_provider' },
    }, 'cid-down'));
    const { view } = await mount();
    await click(view);
    await view.pressMarked(...CONFIRM);
    expect(dialogs(view)).toBe(0);
    expect(view.markup()).toContain('Повторить с тем же ключом');
    await view.press('Повторить с тем же ключом');
    expect(startRun).toHaveBeenCalledTimes(2);
    expect(sent(1)).toEqual(sent(0));
    expect(estimateRunCost).toHaveBeenCalledTimes(1);
  });
});

describe('an answer that the estimate or its binding changed is estimated again and shown', () => {
  it.each([
    ['a stale digest (409)', stale],
    ['a changed model, rate or revision (422)', bindingChanged],
  ])('after %s from a free start it estimates again and opens the dialog, whatever the new figure', async (_name, error) => {
    vi.mocked(estimateRunCost)
      .mockImplementationOnce(async ({ body }) => ({ data: freeEstimate(body) }) as never)
      .mockImplementationOnce(async ({ body }) => ({ data: freeEstimate(body, NEXT_DIGEST) }) as never);
    vi.mocked(startRun).mockRejectedValueOnce(error());
    const { view } = await mount();
    await click(view);
    expect(estimateRunCost).toHaveBeenCalledTimes(2);
    expect(startRun).toHaveBeenCalledTimes(1);
    expect(dialogs(view)).toBe(1);
    expect(view.markup()).toContain(STALE);
    // The refusal is not drawn beside the button as a failure: it was answered by the new estimate.
    expect(view.markup()).not.toContain('Повторить с тем же ключом');
    await view.pressMarked(...CONFIRM);
    expect(startRun).toHaveBeenCalledTimes(2);
    expect(sent().body.cost_consent).toEqual({ estimate_digest: NEXT_DIGEST, ceiling_micros: 0, confirmed: true });
    expect(sent().idempotencyKey).not.toBe(sent(0).idempotencyKey);
    expect(dialogs(view)).toBe(0);
  });

  it('after a stale digest from the dialog it reads the estimate again and keeps a dialog open', async () => {
    vi.mocked(startRun).mockRejectedValueOnce(stale());
    const { view } = await mount();
    await click(view);
    await view.pressMarked(...CONFIRM);
    expect(estimateRunCost).toHaveBeenCalledTimes(2);
    expect(dialogs(view)).toBe(1);
    expect(view.markup()).toContain(STALE);
    expect(startRun).toHaveBeenCalledTimes(1);
  });

  it('shows the failure of the second estimate as itself and sends nothing', async () => {
    vi.mocked(estimateRunCost)
      .mockImplementationOnce(async ({ body }) => ({ data: costEstimate(body) }) as never)
      .mockRejectedValueOnce(new TypeError('Failed to fetch'));
    vi.mocked(startRun).mockRejectedValueOnce(stale());
    const { view } = await mount();
    await click(view);
    await view.pressMarked(...CONFIRM);
    expect(view.markup()).toContain('Стоимость не оценена');
    expect(dialogs(view)).toBe(0);
    expect(startRun).toHaveBeenCalledTimes(1);
  });
});

describe('the «▾» item starts without a money ceiling', () => {
  it('estimates and sends relaxed_limits, and asks once when the estimate can charge', async () => {
    const { view } = await mount();
    await view.press(UNCAPPED_START_LABEL);
    expect(estimateRunCost).toHaveBeenCalledWith({ body: { version_uid: VERSION_UID, relaxed_limits: true } });
    expect(dialogs(view)).toBe(1);
    expect(startRun).not.toHaveBeenCalled();
    // No ceiling to type, and the same meaning the tick-box had.
    expect(view.markup()).not.toContain('Лимит стоимости, $');
    expect(view.markup()).toContain('Прикладной денежный потолок отключён');
    await view.pressMarked(...CONFIRM);
    expect(sent().body).toEqual({
      version_uid: VERSION_UID, relaxed_limits: true, cost_consent: { ...COST_CONSENT, ceiling_micros: 0 },
    });
  });

  it('is agreed to by the click when the estimate charges nothing', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: freeEstimate(body) }) as never);
    const { view } = await mount();
    await view.press(UNCAPPED_START_LABEL);
    expect(dialogs(view)).toBe(0);
    expect(sent().body).toEqual({
      version_uid: VERSION_UID, relaxed_limits: true,
      cost_consent: { estimate_digest: FREE_DIGEST, ceiling_micros: 0, confirmed: true },
    });
  });

  it('is another intent than the ordinary start of the same version', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({ data: freeEstimate(body) }) as never);
    const { view } = await mount();
    await click(view);
    await view.press(UNCAPPED_START_LABEL);
    expect(sent(1).idempotencyKey).not.toBe(sent(0).idempotencyKey);
    expect('relaxed_limits' in sent(0).body).toBe(false);
  });
});

describe('who is offered the start and the «▾» item', () => {
  it.each([
    ['an expert', ['expert'], true],
    ['an expert who is also an administrator', ['expert', 'admin'], true],
    ['an administrator alone', ['admin'], false],
    ['a viewer', ['viewer'], false],
  ])('%s: %s', async (_name, roles, offered) => {
    const { view } = await mount({ roles });
    const markup = view.markup();
    expect(markup.includes('data-start-run-more')).toBe(offered);
    expect(markup.includes(`>${UNCAPPED_START_LABEL}</button>`)).toBe(offered);
    expect(markup.includes('data-start-run-button')).toBe(offered);
    expect(markup.includes('Запускать анализ может эксперт.')).toBe(!offered);
  });

  it('draws the control while the account is not known yet, as it always did', async () => {
    const { view } = await mount();
    expect(view.markup()).toContain('data-start-run-more');
  });
});

describe('the estimate cannot be read', () => {
  it('says so, sends nothing and leaves the button to try again', async () => {
    vi.mocked(estimateRunCost).mockRejectedValueOnce(new Error('legacy endpoint unavailable'));
    const { view } = await mount();
    await click(view);
    expect(view.markup()).toContain('Стоимость не оценена');
    expect(dialogs(view)).toBe(0);
    expect(startRun).not.toHaveBeenCalled();
    expect(await click(view)).toBe(true);
    expect(dialogs(view)).toBe(1);
  });

  it('explains a comparison-only PDF and stops repeat estimates', async () => {
    vi.mocked(estimateRunCost).mockRejectedValue(refusal(422, 'analysis_input_invalid', { reason: 'comparison_only_version' }));
    const { view } = await mount();
    await click(view);
    expect(view.markup()).toContain('Сервер не принимает этот PDF');
    expect(view.markup()).toContain('href="/stage-comparison"');
    expect(view.markup()).toContain('cid-one-click');
    expect(await click(view)).toBe(false);
    expect(await view.press(UNCAPPED_START_LABEL)).toBe(true);
    expect(estimateRunCost).toHaveBeenCalledTimes(1);
    expect(startRun).not.toHaveBeenCalled();
  });

  it('refuses an answer that is not the estimate of this start', async () => {
    vi.mocked(estimateRunCost).mockImplementation(async ({ body }) => ({
      data: { ...costEstimate(body), version_uid: OTHER_VERSION },
    }) as never);
    const { view } = await mount();
    await click(view);
    expect(view.markup()).toContain('Стоимость не оценена');
    expect(dialogs(view)).toBe(0);
    expect(startRun).not.toHaveBeenCalled();
  });

  it('does not act on a late reading for the version that was left', async () => {
    let complete!: (value: never) => void;
    vi.mocked(estimateRunCost).mockReturnValueOnce(new Promise((resolve) => { complete = resolve; }));
    const { view, tree } = await mount();
    await click(view);
    await view.update(tree(OTHER_VERSION));
    await view.settle(() => complete({ data: freeEstimate({ version_uid: VERSION_UID }) } as never));
    expect(dialogs(view)).toBe(0);
    expect(startRun).not.toHaveBeenCalled();
  });
});

describe('the request carries no selector', () => {
  it('names no executor, group or preset in any estimate or start, on any path', async () => {
    vi.mocked(estimateRunCost)
      .mockImplementationOnce(async ({ body }) => ({ data: freeEstimate(body) }) as never)
      .mockImplementationOnce(async ({ body }) => ({ data: costEstimate(body) }) as never)
      .mockImplementationOnce(async ({ body }) => ({ data: costEstimate(body) }) as never);
    const { view } = await mount();
    await click(view);
    await view.press(UNCAPPED_START_LABEL);
    await view.pressMarked(...CONFIRM);
    await click(view);
    await view.pressMarked(...CONFIRM);
    expect(estimateRunCost).toHaveBeenCalledTimes(3);
    expect(startRun).toHaveBeenCalledTimes(3);
    const bodies = [
      ...vi.mocked(estimateRunCost).mock.calls.map((call) => call[0].body),
      ...vi.mocked(startRun).mock.calls.map((call) => (call[0] as { body: object }).body),
    ];
    for (const body of bodies) {
      for (const key of Object.keys(body)) expect(['version_uid', 'relaxed_limits', 'cost_consent']).toContain(key);
    }
  });
});
