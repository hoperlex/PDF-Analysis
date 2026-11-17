/**
 * `UIP-S05-01` (pair S05, `Г10-B`): the window «Модели по этапам» before a start.
 *
 * The rules of the rows are functions (`widgets/run-stages-dialog/model/stage-models-rows.ts`), so each is a call. The window is read from a
 * static render drawn open (`staticOpen`), over the plan of a readiness answer or over a seeded layout. Each claim has a negative that can
 * fail: a mutation that marks a set an expert can press, writes a number the answer did not carry, names a server, draws the table for a
 * layout that has no revision, or says «прежний маршрут» on the layout's own route turns one of these red.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import { ApiError } from '@/shared/api';
import type { RunStartReadiness } from '@/shared/api';
import { LAYOUT_OFF_NOTE, NOT_ON_SERVERS, NO_LAYOUT, stageLayoutKey } from '@/entities/stage-layout';
import { StageModelsDialog, StageModelsDialogView, factOfRoles, layoutStageRows, planStageRows } from '@/widgets/run-stages-dialog';
import type { StageLayoutReading, StageModelsSource } from '@/widgets/run-stages-dialog';

import { newClient, renderScreen, seedError } from '../screens/harness';
import { LAYOUT, LAYOUT_EMPTY, LAYOUT_OFF, seedLayout } from '../workers/hosts-fixtures';
import {
  CLAUDE_CELLS, DIGEST, ENSEMBLE_CELLS, READINESS_API, READINESS_MIXED, blockedReadiness, missingCell, readiness, readinessCell,
} from './readiness-fixtures';

const noop = (): void => undefined;

/** The plan window, drawn open. */
function plan(answer: RunStartReadiness): string {
  return renderToStaticMarkup(createElement(StageModelsDialogView, { source: { kind: 'plan', readiness: answer }, onClose: noop, staticOpen: true }));
}

/** The window of a source with no plan, over a layout reading, drawn open. */
function noPlan(source: StageModelsSource, layout: StageLayoutReading | undefined): string {
  return renderToStaticMarkup(createElement(StageModelsDialogView, { source, layout, onClose: noop, staticOpen: true }));
}

const text = (markup: string): string => markup.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();

/** The text of the fact column of one stage. */
const factOf = (markup: string, stage: string): string | undefined =>
  new RegExp(`data-stage-fact="${stage}">([^<]*)</span>`).exec(markup)?.[1];

const ready = (layout: Parameters<typeof layoutStageRows>[0]): StageLayoutReading => ({ state: 'ready', layout });

const SIX = ['Анализ текста', 'Анализ блоков', 'Комплексная сверка', 'Нормы', 'Критик', 'Уточнение'];

describe('the fact of a row, by the roles of its cells', () => {
  it('says one model, a leg and a judge, and two legs side by side and a judge', () => {
    expect(factOfRoles(['main'])).toBe('одна модель');
    expect(factOfRoles(['leg1', 'judge'])).toBe('ветка и судья');
    expect(factOfRoles(['leg1', 'leg2', 'judge'])).toBe('две ветки параллельно и судья');
  });

  it('says a shape the layout does not offer by its parts and does not guess it into one of the three', () => {
    expect(factOfRoles(['leg1', 'leg2'])).toBe('две ветки параллельно');
    expect(factOfRoles(['leg1'])).toBe('ветка');
    expect(factOfRoles(['judge'])).toBe('судья');
    expect(factOfRoles([])).toBe('');
  });
});

describe('the six rows of the plan', () => {
  it('lists the six stages in the original\'s order, each with the fact its cells state', () => {
    const rows = planStageRows(readiness({ cells: [...ENSEMBLE_CELLS] }));
    expect(rows.map((row) => row.label)).toEqual(SIX);
    expect(rows.map((row) => row.cells.length)).toEqual([1, 3, 0, 0, 0, 0]);
    expect(rows[0]?.fact).toBe('одна модель');
    expect(rows[1]?.fact).toBe('две ветки параллельно и судья');
    // The cells of a row come legs first, judge last, whatever order the answer gave them in.
    expect(rows[1]?.cells.map((cell) => cell.role)).toEqual(['leg1', 'leg2', 'judge']);
  });

  it('says a stage the run does not take is not in the run, and invents no model for it', () => {
    const rows = planStageRows(readiness());
    expect(rows.map((row) => row.fact)).toEqual(['одна модель', 'одна модель', 'одна модель', 'одна модель', 'не входит в запуск', 'не входит в запуск']);
    expect(rows[4]?.cells).toEqual([]);
    expect(rows[5]?.cells).toEqual([]);
  });

  it('says the critic and the refinement run by the original\'s rules, without a model, under plan v2 and only under it', () => {
    const v2 = planStageRows(readiness({ extended_plan: 'v2' }));
    expect(v2.map((row) => row.fact).slice(4)).toEqual(['без модели (правила оригинала)', 'без модели (правила оригинала)']);
    expect(v2.map((row) => row.fact).slice(0, 4)).toEqual(['одна модель', 'одна модель', 'одна модель', 'одна модель']);
    for (const extended of [undefined, null, 'v3'] as const) {
      const rows = planStageRows(readiness(extended === undefined ? {} : { extended_plan: extended }));
      expect(rows.map((row) => row.fact).slice(4), String(extended)).toEqual(['не входит в запуск', 'не входит в запуск']);
    }
    // Under v2 a row that has a cell keeps what its cell says: the rule is for the rows with none.
    const withCritic = planStageRows(readiness({ extended_plan: 'v2', cells: [...CLAUDE_CELLS, readinessCell('review', 'claude-sonnet-5-5')] }));
    expect(withCritic[4]?.fact).toBe('одна модель');
  });

  it('reads the saved layout through the same rows, every one saying the one word it was given, and no cell has an access', () => {
    const rows = layoutStageRows(LAYOUT, 'прежний маршрут');
    expect(rows.map((row) => row.label)).toEqual(SIX);
    expect(new Set(rows.map((row) => row.fact))).toEqual(new Set(['прежний маршрут']));
    expect(rows.every((row) => row.cells.length === 1)).toBe(true);
    expect(rows.flatMap((row) => row.cells.map((cell) => cell.access))).toEqual([null, null, null, null, null, null]);
    // The one cell the server names as served by none is the one that says so.
    expect(rows.flatMap((row) => row.cells).filter((cell) => !cell.available).map((cell) => cell.cellKey)).toEqual(['review:main']);
    expect(layoutStageRows(LAYOUT_EMPTY, 'прежний маршрут').every((row) => row.cells.length === 0)).toBe(true);
  });
});

describe('the window over a plan', () => {
  it('is the shared window «Модели по этапам» with the set, the table of five columns, and «Закрыть»', () => {
    const markup = plan(readiness());
    expect(markup).toContain('data-stage-models-dialog');
    expect(markup).toContain('<h2');
    expect(text(markup)).toContain('Модели по этапам');
    // Three sets, the one in force marked, none of them a control.
    expect(markup).toContain('data-stage-models-kits');
    expect(text(markup)).toContain('Только Claude Только Codex Свой набор');
    expect(markup).toMatch(/aria-current="true"[^>]*data-layout-kit="claude_only"|data-layout-kit="claude_only"[^>]*aria-current="true"/);
    expect(markup.match(/aria-current="true"/g)).toHaveLength(1);
    expect(markup).not.toMatch(/<button[^>]*data-layout-kit/);
    for (const header of ['Этап', 'Модель', 'Усилие', 'Доступ', 'Фактически работает']) expect(markup, header).toContain(`>${header}</th>`);
    for (const stage of SIX) expect(markup, stage).toContain(`>${stage}</td>`);
    expect(markup).toContain('data-stage-models-close');
    expect(markup).toContain('>Закрыть</button>');
  });

  it('marks the set the answer names, and draws none while the answer names none', () => {
    expect(plan(readiness({ kit: 'codex_only' }))).toMatch(/data-layout-kit="codex_only"/);
    const codex = plan(readiness({ kit: 'codex_only' }));
    expect(/aria-current="true"[^>]*data-layout-kit="(\w+)"/.exec(codex)?.[1]).toBe('codex_only');
    const custom = plan(readiness({ kit: 'custom' }));
    expect(/aria-current="true"[^>]*data-layout-kit="(\w+)"/.exec(custom)?.[1]).toBe('custom');
    const bare = readiness();
    delete bare.kit;
    expect(plan(bare)).not.toContain('data-stage-models-kits');
  });

  it('says for each cell the model, the effort and how it is paid, in the words of the cost dialog', () => {
    const markup = plan(readiness());
    expect(text(markup)).toContain('Анализ текста Sonnet 5.5 среднее по подписке одна модель');
    expect(text(markup)).toContain('Анализ блоков Opus 5.5 среднее по подписке одна модель');
    expect(markup).toContain('data-host-access="subscription"');
    expect(markup).not.toContain('data-host-access="api"');
    expect(text(plan(READINESS_API))).toContain('по ключу API');
    expect(text(plan(READINESS_MIXED))).toContain('по ключу API');
    expect(text(plan(READINESS_MIXED))).toContain('по подписке');
    expect(factOf(markup, 'review')).toBe('не входит в запуск');
  });

  it('lists the cells of a stage with legs and a judge, the role in front, in the same order in every column', () => {
    const markup = plan(readiness({ cells: [...ENSEMBLE_CELLS], kit: 'codex_only' }));
    expect(text(markup)).toContain('первая ветка: Opus 5.5 вторая ветка: gpt-6-astra судья: Sonnet 5.5');
    expect(factOf(markup, 'blocks')).toBe('две ветки параллельно и судья');
    // The same three cells down the model, effort and access columns.
    expect(markup.match(/data-stage-cell="blocks:leg1"/g)).toHaveLength(3);
    expect(markup.match(/data-stage-cell="blocks:judge"/g)).toHaveLength(3);
    // The one answer of a row is named by its model alone.
    expect(markup).not.toContain('main:');
    expect(markup).toContain('data-model-effort="high"');
  });

  it('says a model no server has as such, where it stands, and marks nothing else', () => {
    expect(plan(readiness())).not.toContain(NOT_ON_SERVERS);
    const markup = plan(blockedReadiness());
    expect(markup.match(/⚠ нет на серверах/g)).toHaveLength(1);
    expect(markup).toContain('data-host-reason="not_on_any_server"');
    expect(text(markup)).toContain('Анализ блоков Opus 5.5 среднее ⚠ нет на серверах');
    // The effort is still said, and no access is claimed for a cell no server serves.
    expect(markup).not.toContain('data-host-access="none"');
    const ensemble = plan(readiness({ ready: false, cells: [readinessCell('blocks', 'claude-opus-5-5', { role: 'leg1' }), missingCell('blocks', 'gpt-6-astra', 'leg2')] }));
    expect(ensemble.match(/⚠ нет на серверах/g)).toHaveLength(1);
  });

  it('reads the plan alone: no layout is asked for, and a seeded layout does not reach it', () => {
    const client = newClient();
    seedLayout(client, LAYOUT);
    const markup = renderScreen(client, createElement(StageModelsDialog, { source: { kind: 'plan', readiness: readiness() }, onClose: noop, staticOpen: true }));
    expect(markup).not.toContain('gpt-6-astra');
    expect(markup).not.toContain('прежний маршрут');
    expect(markup).not.toContain(LAYOUT_OFF_NOTE);
  });

  it('names no server and writes no number the answer did not carry', () => {
    const said = text(plan(READINESS_MIXED));
    // The only figures a person reads are the ones in a model's own name.
    expect(said.replace(/\b(?:Sonnet|Opus) 5\.5\b/g, '')).not.toMatch(/[\d$]/);
    expect(said).not.toMatch(/сервер(?!ах)/i);
    expect(said).not.toContain(DIGEST.slice(0, 8));
  });

  it('is the window of a look: no way to start, to choose a model or to go on from here', () => {
    const markup = plan(readiness());
    expect(markup).not.toContain('Запустить');
    expect(markup).not.toContain('<select');
    expect(markup).not.toContain('<input');
    expect(markup).not.toContain('data-run-stages-dialog');
    expect(markup).not.toContain('Фактически: ');
  });
});

describe('the window with no plan to read: the saved layout, and the one word of the case', () => {
  it('says «прежний маршрут» while the layout is off, with the words that say it is off over the table', () => {
    const markup = noPlan({ kind: 'legacy' }, ready(LAYOUT_OFF));
    expect(markup).toContain(LAYOUT_OFF_NOTE);
    expect(markup).toContain('data-layout-state="off"');
    expect(SIX.every((stage) => markup.includes(`>${stage}</td>`))).toBe(true);
    for (const stage of ['text', 'blocks', 'cross_check', 'norms', 'review', 'correction']) expect(factOf(markup, stage), stage).toBe('прежний маршрут');
    // The saved layout: its models and efforts, its set marked («Свой набор» for the fixture), and no access to state.
    expect(text(markup)).toContain('Анализ текста Sonnet 5.5 среднее');
    expect(markup).toContain('gpt-6-astra');
    expect(markup).not.toContain('data-host-access');
    expect(/aria-current="true"[^>]*data-layout-kit="(\w+)"/.exec(markup)?.[1]).toBe('custom');
  });

  it('says «автоматически» after a typed 503 and «не прочитано» when the readiness was not read, with no note of an off layout', () => {
    const automatic = noPlan({ kind: 'automatic' }, ready(LAYOUT));
    const unread = noPlan({ kind: 'unread' }, ready(LAYOUT));
    for (const stage of ['text', 'blocks', 'review']) {
      expect(factOf(automatic, stage), stage).toBe('автоматически');
      expect(factOf(unread, stage), stage).toBe('не прочитано');
    }
    for (const markup of [automatic, unread]) {
      expect(markup).not.toContain(LAYOUT_OFF_NOTE);
      expect(markup).not.toContain('прежний маршрут');
    }
    // The server's own mark on the saved layout stays: the critic's model is on no server.
    expect(automatic.match(/⚠ нет на серверах/g)).toHaveLength(1);
  });

  it('says the layout is not set, instead of a table, while it has no revision, and still says it is off', () => {
    const markup = noPlan({ kind: 'legacy' }, ready(LAYOUT_EMPTY));
    expect(markup).toContain(NO_LAYOUT);
    expect(markup).toContain(LAYOUT_OFF_NOTE);
    expect(markup).not.toContain('data-stage-fact');
    expect(markup).not.toContain('data-stage-models-kits');
    expect(noPlan({ kind: 'automatic' }, ready(LAYOUT_EMPTY))).not.toContain(LAYOUT_OFF_NOTE);
  });

  it('says it is reading while the layout is read, and names the failure of a read that failed, with a way to try again', () => {
    const loading = noPlan({ kind: 'legacy' }, { state: 'loading' });
    expect(loading).toContain('Загрузка');
    expect(loading).not.toContain('data-stage-fact');
    expect(noPlan({ kind: 'legacy' }, undefined)).toContain('Загрузка');
    const failed = noPlan({ kind: 'legacy' }, { state: 'failed', detail: 'Сервис недоступен.', correlationId: 'cid-1', retry: noop });
    expect(failed).toContain('Модели по этапам не прочитаны');
    expect(failed).toContain('Сервис недоступен.');
    expect(failed).toContain('role="alert"');
    expect(failed).toContain('>Повторить</button>');
    expect(failed).not.toContain('data-stage-fact');
    // The window is still a window that closes.
    expect(failed).toContain('data-stage-models-close');
  });

  it('is read by the connected window from the cache, and a refusal of the read says so', () => {
    const client = newClient();
    seedLayout(client, LAYOUT_OFF);
    const off = renderScreen(client, createElement(StageModelsDialog, { source: { kind: 'legacy' }, onClose: noop, staticOpen: true }));
    expect(factOf(off, 'text')).toBe('прежний маршрут');
    expect(off).toContain(LAYOUT_OFF_NOTE);
    const refused = newClient();
    seedError(refused, stageLayoutKey(), new ApiError(500, {
      contract_version: '1.57.0', error_code: 'internal_error', message: 'refused', correlation_id: 'cid-layout', retryable: false, details: {},
    }, 'cid-layout'));
    const failed = renderScreen(refused, createElement(StageModelsDialog, { source: { kind: 'automatic' }, onClose: noop, staticOpen: true }));
    expect(failed).toContain('Модели по этапам не прочитаны');
    expect(failed).toContain('cid-layout');
    // Nothing seeded: it is still reading, and says so.
    expect(renderScreen(newClient(), createElement(StageModelsDialog, { source: { kind: 'legacy' }, onClose: noop, staticOpen: true }))).toContain('Загрузка');
  });
});
