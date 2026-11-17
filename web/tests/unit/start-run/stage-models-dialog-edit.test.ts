/**
 * `UIP-S05-03` (pair S05, `Г10-B`, `Г13-C`, `R-150w`): the administrator edits the set in the window «Модели по этапам» by a revision of the layout.
 *
 * What is drawn is read from a static render over a seeded cache (the role, the layout, the servers and the catalogue are seeded the way the
 * cache holds them after the first read). What a press does is read from a live mount with the generated client mocked, so no network is touched.
 * The form is the existing `LayoutEditor`; this file does not test it again (`tests/unit/stage-layout/`), it tests that the window gives it to an
 * administrator and to nobody else, reads what it needs when it opens, goes back to the table, and that a save refreshes the line under «Запустить».
 * Each claim has a negative that can fail: a mutation that draws «Изменить» for an expert, opens the form before the reads are in, draws it after a
 * read failed, or files the save under a key the readiness is not under turns one of these red.
 *
 * Not reached here: the submit of the form (`«Сохранить набор»` is a submit button, which the fake DOM of `live-render.ts` cannot press). The save
 * the form makes is `useReviseStageModelLayout`, and that command is driven below by the same hook.
 */

import { QueryClientProvider } from '@tanstack/react-query';
import { Fragment, createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/shared/api', async (importOriginal) => ({
  ...await importOriginal<Record<string, unknown>>(),
  getRunStartReadiness: vi.fn(),
  getStageModelLayout: vi.fn(),
  listExecutorHosts: vi.fn(),
  listModelCatalogue: vi.fn(),
  reviseStageModelLayout: vi.fn(),
}));

import {
  ApiError, getRunStartReadiness, getStageModelLayout, listExecutorHosts, listModelCatalogue, queryKeys, reviseStageModelLayout,
} from '@/shared/api';
import type { QueryClient } from '@tanstack/react-query';
import type { Role } from '@/shared/api';
import { executorHostsKey } from '@/entities/executor-host';
import { NO_LAYOUT, NO_LAYOUT_ADMIN } from '@/entities/stage-layout';
import { runStartReadinessKey } from '@/features/start-run';
import { draftRequest, initialDraft, useReviseStageModelLayout } from '@/features/manage-stage-layout';
import { StartRunWithReadiness } from '@/widgets/run-list';
import { StageModelsDialog, StageModelsDialogView } from '@/widgets/run-stages-dialog';
import type { StageModelsSource } from '@/widgets/run-stages-dialog';

import { PROJECT_UID, VERSION_UID } from '../review/fixtures';
import { newClient, renderScreen, seedError } from '../screens/harness';
import { mountLive } from '../analysis-settings/live-render';
import type { LiveRender } from '../analysis-settings/live-render';
import { CATALOGUE, HOST_LIST, LAYOUT, LAYOUT_EMPTY, LAYOUT_OFF, seedHosts, seedLayout } from '../workers/hosts-fixtures';
import { readiness } from './readiness-fixtures';

const noop = (): void => undefined;
const PLAN: StageModelsSource = { kind: 'plan', readiness: readiness() };

let live: LiveRender | null = null;

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getRunStartReadiness).mockResolvedValue({ data: readiness() } as never);
  vi.mocked(getStageModelLayout).mockResolvedValue({ data: LAYOUT } as never);
  vi.mocked(listExecutorHosts).mockResolvedValue({ data: HOST_LIST } as never);
  vi.mocked(listModelCatalogue).mockResolvedValue({ data: CATALOGUE } as never);
  vi.mocked(reviseStageModelLayout).mockResolvedValue({ data: LAYOUT } as never);
});
afterEach(async () => { await live?.unmount(); live = null; });

function refusal(status: number): ApiError {
  return new ApiError(status, {
    contract_version: '1.57.0', error_code: 'internal_error', message: 'refused', correlation_id: 'cid-edit', retryable: false, details: {},
  }, 'cid-edit');
}

/** A cache the way the first reads leave it: the role, and, when `reads` is set, the layout, the catalogue and the servers. */
function cacheOf(roles: readonly Role[], reads = true): QueryClient {
  const client = newClient();
  client.setQueryData(queryKeys.account.me(), { roles });
  if (reads) {
    seedLayout(client, LAYOUT);
    seedHosts(client);
  }
  return client;
}

const draw = (client: QueryClient, props: Partial<Parameters<typeof StageModelsDialog>[0]> = {}): string =>
  renderScreen(client, createElement(StageModelsDialog, { source: PLAN, onClose: noop, staticOpen: true, ...props }));

async function mount(client: QueryClient, source: StageModelsSource = PLAN) {
  live = await mountLive(createElement(QueryClientProvider, { client }, createElement(StageModelsDialog, { source, onClose: noop, staticOpen: true })));
  return live;
}

describe('who is drawn «Изменить»', () => {
  it('draws an administrator the button, beside «Закрыть», and no form until it is pressed', () => {
    const markup = draw(cacheOf(['admin']));
    expect(markup).toContain('data-stage-models-edit-open');
    expect(markup).toContain('>Изменить</button>');
    expect(markup).toContain('>Закрыть</button>');
    expect(markup).not.toContain('data-layout-editor');
    expect(markup).toContain('data-stage-fact="text"');
  });

  it('draws an expert the window to read: no button, no form, and not the form even if it were asked for', () => {
    const client = cacheOf(['expert']);
    for (const markup of [draw(client), draw(client, { initiallyEditing: true })]) {
      expect(markup).not.toContain('data-stage-models-edit-open');
      expect(markup).not.toContain('Изменить');
      expect(markup).not.toContain('data-layout-editor');
      expect(markup).not.toContain('Сохранить набор');
      expect(markup).toContain('data-stage-fact="text"');
    }
  });

  it('draws the view the button only for the one who is given a way to open the form', () => {
    const view = (onEdit?: () => void) => renderToStaticMarkup(createElement(StageModelsDialogView, { source: PLAN, onClose: noop, staticOpen: true, ...(onEdit === undefined ? {} : { onEdit }) }));
    expect(view(noop)).toContain('data-stage-models-edit-open');
    expect(view()).not.toContain('Изменить');
  });

  it('asks the administrator to press «Изменить» when no set is saved, and tells an expert it is not set', () => {
    const empty = (roles: readonly Role[]) => {
      const client = cacheOf(roles, false);
      seedLayout(client, LAYOUT_EMPTY);
      return draw(client, { source: { kind: 'legacy' } });
    };
    expect(empty(['admin'])).toContain(NO_LAYOUT_ADMIN);
    const expert = empty(['expert']);
    expect(expert).toContain(NO_LAYOUT);
    expect(expert).not.toContain('Нажмите «Изменить»');
  });
});

describe('the form, in the same window', () => {
  it('is the existing form of the layout, in place of the table, read from the layout, the servers and the catalogue', () => {
    const markup = draw(cacheOf(['admin']), { initiallyEditing: true });
    expect(markup).toContain('data-stage-models-dialog');
    expect(markup).toContain('data-layout-editor');
    expect(markup).toContain('Только Claude');
    expect(markup).toContain('Только Codex');
    expect(markup).toContain('Свой набор');
    expect(markup).toContain('>Сохранить набор</button>');
    expect(markup).toContain('>Отменить</button>');
    // In place of the table, and in place of the window's own buttons: the form has «Сохранить набор» and «Отменить».
    expect(markup).not.toContain('data-stage-fact');
    expect(markup).not.toContain('data-stage-models-close');
    expect(markup).not.toContain('data-stage-models-edit-open');
    expect(markup).not.toContain('Загрузка');
  });

  it('says it is reading the servers and the catalogue while they are read, and draws no form yet', () => {
    const client = cacheOf(['admin'], false);
    seedHosts(client);
    const markup = draw(client, { initiallyEditing: true });
    expect(markup).toContain('Загрузка: серверы и каталог моделей…');
    expect(markup).not.toContain('data-layout-editor');
    expect(markup).not.toContain('data-stage-fact');
  });

  it('does not open the form when the servers cannot be read, and names the reason with a way to try again', () => {
    const client = cacheOf(['admin']);
    client.removeQueries({ queryKey: executorHostsKey() });
    seedError(client, executorHostsKey(), refusal(500));
    const markup = draw(client, { initiallyEditing: true });
    expect(markup).toContain('data-stage-models-edit-failure');
    expect(markup).toContain('Набор моделей нельзя изменить');
    expect(markup).toContain('cid-edit');
    expect(markup).toContain('role="alert"');
    expect(markup).toContain('>Повторить</button>');
    expect(markup).not.toContain('data-layout-editor');
    expect(markup).not.toContain('Сохранить набор');
  });
});

describe('what a press does', () => {
  it('opens the form on «Изменить», and «Отменить» goes back to the table with its button', async () => {
    const view = await mount(cacheOf(['admin']));
    expect(view.count('Изменить')).toBe(1);
    expect(view.markup()).toContain('data-stage-fact="text"');
    expect(await view.press('Изменить')).toBe(true);
    expect(view.markup()).toContain('data-layout-editor');
    expect(view.markup()).not.toContain('data-stage-fact');
    expect(view.count('Изменить')).toBe(0);
    expect(await view.press('Отменить')).toBe(true);
    expect(view.markup()).not.toContain('data-layout-editor');
    expect(view.markup()).toContain('data-stage-fact="text"');
    expect(view.count('Изменить')).toBe(1);
  });

  it('gives an expert nothing to press: there is no «Изменить» to open anything with', async () => {
    const view = await mount(cacheOf(['expert']));
    expect(view.count('Изменить')).toBe(0);
    await expect(view.press('Изменить')).rejects.toThrow('found 0');
    expect(view.markup()).not.toContain('data-layout-editor');
  });

  it('reads the servers and the catalogue only once the form is opened, and says it is reading until they are in', async () => {
    // The servers never answer, so the window keeps saying that it is reading.
    vi.mocked(listExecutorHosts).mockReturnValue(new Promise(() => undefined) as never);
    const view = await mount(cacheOf(['admin'], false));
    expect(listExecutorHosts).not.toHaveBeenCalled();
    expect(listModelCatalogue).not.toHaveBeenCalled();
    await view.press('Изменить');
    expect(listExecutorHosts).toHaveBeenCalledTimes(1);
    expect(view.markup()).toContain('Загрузка: серверы и каталог моделей…');
    expect(view.markup()).not.toContain('data-layout-editor');
  });

  it('names the reason and keeps the form closed when a read is refused, in the window and not in a page', async () => {
    vi.mocked(listExecutorHosts).mockRejectedValue(refusal(500));
    const view = await mount(cacheOf(['admin'], false));
    await view.press('Изменить');
    await view.settle(() => undefined);
    expect(view.markup()).toContain('Набор моделей нельзя изменить');
    expect(view.markup()).not.toContain('data-layout-editor');
    expect(view.markup()).toContain('data-stage-models-dialog');
  });
});

describe('a save refreshes the line under «Запустить»', () => {
  it('files the revision under the key the readiness is under, so the one command refreshes both', async () => {
    const client = cacheOf(['admin', 'expert']);
    client.setQueryData(runStartReadinessKey(VERSION_UID), readiness());
    // The save the form makes, driven by the same hook: a press calls the command with the request the unchanged form builds.
    function Save() {
      const revise = useReviseStageModelLayout();
      return createElement('button', {
        type: 'button',
        onClick: () => {
          const draft = initialDraft(LAYOUT_OFF, CATALOGUE, ['claude-opus-5-5', 'claude-sonnet-5-5', 'gpt-6-astra']);
          if (draft !== null) void revise.mutateAsync({ body: draftRequest(draft), idempotencyKey: 'key-1' });
        },
      }, 'Сохранить тест');
    }
    live = await mountLive(createElement(QueryClientProvider, { client }, createElement(Fragment, null,
      createElement(StartRunWithReadiness, { projectUid: PROJECT_UID, versionUid: VERSION_UID }),
      createElement(Save),
    )));
    expect(getRunStartReadiness).not.toHaveBeenCalled();
    expect(live.markup()).toContain('Набор: Только Claude');
    // The new revision changes the plan a start would freeze: the line reads it again.
    vi.mocked(getRunStartReadiness).mockResolvedValue({ data: readiness({ kit: 'custom' }) } as never);
    expect(await live.press('Сохранить тест')).toBe(true);
    await live.settle(() => undefined);
    expect(reviseStageModelLayout).toHaveBeenCalledTimes(1);
    expect(getRunStartReadiness).toHaveBeenCalledTimes(1);
    expect(live.markup()).toContain('Набор: Свой набор');
    expect(live.markup()).not.toContain('Набор: Только Claude');
  });
});
