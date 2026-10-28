/**
 * The screens of «Сравнение версий», rendered (`CMP-VC-UI-01`): the table of document sets, the sheet matrix with its draft,
 * the transitions, the upload dialogs, the page with a module that is off and one that is not wired, the block «Сравнение» of
 * «Очередь», and the A-12 edit of the version-scoped screen.
 *
 * The static harness fires no event, so every state is a seeded cache or a prop; the logic that events drive (the draft, the
 * transfer, the gestures) is held by `model.test.ts` and `upload-model.test.ts`. Expectations are literals.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { SheetPairing } from '@/shared/api';
import { queryKeys } from '@/shared/api';
import { buildNavigation } from '@/_app/navigation';
import { VersionComparePage } from '@/_pages/version-compare';
import { StageComparisonPage } from '@/_pages/stage-comparison';
import { ExecutionQueue, ComparisonQueueBlock, ComparisonQueueBlockView } from '@/widgets/execution-queue';
import { ComparisonResult } from '@/widgets/version-comparison';
import { UploadDialogView } from '@/widgets/comparison-upload';
import type { UploadDialogViewProps } from '@/widgets/comparison-upload';
import { SheetsTabView, ProjectsAndStagesView } from '@/widgets/version-series';
import type { ProjectsAndStagesViewProps, SheetsTabViewProps } from '@/widgets/version-series';
import { screenAt, SCREEN_REGISTRY } from '@/shared/config';
import { routes } from '@/shared/lib';
import {
  COMPARISON_KEYS,
  EMPTY_DRAFT,
  INITIAL_VIEW,
  addEdit,
  columnNames,
  comparisonFailure,
  touchedPages,
} from '@/entities/version-series';

import { newClient, renderScreen, renderWith, seedError } from '../screens/harness';

import {
  DOCUMENT_UID,
  MATRIX_ID,
  PROJECT_UID,
  UPLOAD_ID,
  V1,
  V2,
  V3,
  edits,
  matrix,
  overview,
  page,
  pairs,
  proposalSets,
  queueSummary,
  series,
  transition,
  upload,
  uid,
} from './fixtures';
import { READER, refusal, seedComparison } from './seed';

const noop = (): void => undefined;
const LATIN = /[A-Za-z]/;

/** The text a reader reads: tags dropped, entities decoded, and the machine words kept out (they live in `data-` attributes). */
function text(markup: string): string {
  return markup
    .replace(/<[^>]*>/g, ' ')
    .replace(/&#x27;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ');
}

// ------------------------------------------------------------------------------ «Проекты и этапы»

function projectsProps(over: Partial<ProjectsAndStagesViewProps> = {}): ProjectsAndStagesViewProps {
  return {
    overview: overview(), view: INITIAL_VIEW, onView: noop, mayAct: true, busy: false, confirming: null, failure: null,
    onRefresh: noop, onOpen: noop, onAct: noop, onConfirmRestart: noop, onCancelRestart: noop, ...over,
  };
}
const projects = (over: Partial<ProjectsAndStagesViewProps> = {}): string => renderToStaticMarkup(createElement(ProjectsAndStagesView, projectsProps(over)));

describe('«Проекты и этапы»', () => {
  it('draws the counters, the totals, the search, the filters, «Обновить» with the time, and the legend', () => {
    const t = text(projects());
    for (const word of ['Все', 'Ждут действия', 'Идут', 'Ошибки', 'Готовы', 'версий · 90 переходов', 'Марка', 'Порядок', 'Обновить', 'обновлено 10:15:30 UTC']) {
      expect(t, word).toContain(word);
    }
    expect(projects()).toContain('placeholder="Поиск по шифру…"');
    expect(t).toContain('Щелчок по строке — сравнение листов комплекта.');
    for (const legend of ['готово', 'есть что проверить', 'идёт', 'не запускалось', 'ошибка']) expect(t).toContain(legend);
  });

  it('shows the server\'s counters when nothing is searched and the visible sets\' counts when something is', () => {
    expect(projects()).toContain('<span class="');
    const all = projects();
    expect(all).toMatch(/data-overview-filter="all"[^>]*><span[^>]*>13</);
    expect(all).toMatch(/data-overview-filter="waiting"[^>]*><span[^>]*>5</);
    const searched = projects({ view: { ...INITIAL_VIEW, query: '133/23-ГК-ЭМ1' } });
    expect(searched).toMatch(/data-overview-filter="all"[^>]*><span[^>]*>2</);
    expect(searched).toMatch(/data-overview-filter="waiting"[^>]*><span[^>]*>1</);
    expect(searched).toMatch(/data-overview-filter="failed"[^>]*><span[^>]*>1</);
  });

  it('has the table «Проект · следующий шаг», «Версии» and the steps 1, 2, 3 and 5, and says steps 4, 6 and 7 are not there', () => {
    const t = text(projects());
    for (const header of ['Проект · следующий шаг', 'Версии', '1 Загрузка', '2 Разбор версий', '3 Сопоставление листов', '5 Сравнение соседних']) {
      expect(t, header).toContain(header);
    }
    for (const missing of ['4 ИИ-проверка сомнительных пар', '6 ИИ-описание изменений', '7 Сводка и отчёт']) expect(t, missing).not.toContain(missing);
    expect(t).toContain('Шаги 4 «ИИ-проверка сомнительных пар», 6 «ИИ-описание изменений» и 7 «Сводка и отчёт» появятся позже');
  });

  it('puts every state word of the original in a cell and a next-step chip on the rows that have one', () => {
    const markup = projects();
    for (const state of ['not_started', 'queued', 'running', 'pausing', 'paused', 'interrupted', 'done', 'partial', 'stale', 'attention', 'failed', 'blocked', 'not_applicable']) {
      expect(markup, state).toContain(`data-step-state="${state}"`);
    }
    for (const next of ['upload', 'profile', 'matrix', 'ai_pairs', 'series']) expect(markup, next).toContain(`data-next-step="${next}"`);
    const t = text(markup);
    for (const word of ['загружен', 'не сопост. 4', 'строк 31 · ✎ 2', 'по старому порядку', '2 из 3 · с изм. 1', 'Далее: Разобрать версии']) expect(t, word).toContain(word);
  });

  it('shows the strip «В загрузке, ещё не в списке проектов:» with each unfinished upload', () => {
    const t = text(projects());
    expect(t).toContain('В загрузке, ещё не в списке проектов:');
    expect(t).toContain('передаётся · файлов 12 · комплектов 1 из 4');
    expect(text(projects({ overview: overview({ pending_uploads: [] }) }))).not.toContain('В загрузке, ещё не в списке проектов');
  });

  it('offers the step buttons to an expert only', () => {
    const expert = projects();
    for (const label of ['Повторить', 'Подготовить', 'Запустить', 'Пауза', 'Продолжить', 'Заново']) expect(text(expert), label).toContain(label);
    for (const action of ['prepare', 'start', 'pause', 'resume', 'finish', 'restart']) expect(expert, action).toContain(`data-step-action="${action}"`);
    const reader = projects({ mayAct: false });
    expect(reader).not.toContain('data-step-action');
  });

  it('asks before «Заново», in the original\'s words', () => {
    const set = overview().sets[5];
    const t = text(projects({ confirming: set as never }));
    expect(t).toContain('Сравнение соседних заново');
    expect(t).toContain('Все переходы будут пересчитаны по текущему порядку и составу версий. Пары листов, которые не менялись, берутся из кэша.');
    expect(t).toContain('Пересчитать');
    expect(text(projects())).not.toContain('Пересчитать');
  });

  it('says what it is when there are no sets and when the filters leave none', () => {
    expect(text(projects({ overview: overview({ sets: [] }) }))).toContain('В проекте ещё нет версий для сравнения.');
    expect(text(projects({ view: { ...INITIAL_VIEW, query: 'нет такого шифра' } }))).toContain('Ни один комплект не подходит под выбранное.');
  });

  it('a refusal of a command is shown beside the table, in Russian', () => {
    const failure = comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_series_active' }));
    expect(text(projects({ failure }))).toContain('Сравнение соседних версий этого комплекта уже идёт');
  });
});

// ------------------------------------------------------------------------------ «Сравнение листов»

function sheetsProps(over: Partial<SheetsTabViewProps> = {}): SheetsTabViewProps {
  const m = matrix();
  return {
    heading: '133/23-ГК-ЭМ1', matrix: m, edits: edits(), names: columnNames(m.columns ?? []),
    titles: new Map([[V1, 'ЭМ-изм0.pdf'], [V2, 'ЭМ-изм1.pdf'], [V3, 'ЭМ-изм2.pdf']]), series: series(), seriesFailure: null, seriesBusy: false,
    pairs: pairs(), openTransitionId: uid('ctn', 2), sides: { a: V2, b: V3 }, onSide: noop, onlyChanged: false, onOnlyChanged: noop,
    draft: EMPTY_DRAFT, notice: null, dropped: [], draftFailure: null, applying: false, mayEdit: true, prepareBusy: false,
    orderDialog: null, viewer: null, clickNote: null, onPrepare: noop, onApply: noop, onUndo: noop, onRemoveDraft: noop,
    onOpenOrder: noop, onGesture: noop, onSheet: noop, onOpenPair: noop, onOpenTransition: noop, onSeriesAct: noop, onStartSeries: noop,
    ...over,
  };
}
const sheets = (over: Partial<SheetsTabViewProps> = {}): string => renderToStaticMarkup(createElement(SheetsTabView, sheetsProps(over)));

const DRAFT = ((): SheetsTabViewProps['draft'] => {
  const revision = { matrix_id: MATRIX_ID, edit_no: 3 };
  const one = addEdit(EMPTY_DRAFT, revision, { kind: 'link', page: page(V1, 6), otherPage: page(V3, 7) });
  return addEdit(one as never, revision, { kind: 'unlink', page: page(V2, 1) }) as never;
})();

describe('«Сравнение листов»', () => {
  it('draws the header with «· версий: N», «Порядок версий» and the sheet matrix', () => {
    const t = text(sheets());
    expect(t).toContain('133/23-ГК-ЭМ1');
    expect(t).toContain('· версий: 3');
    expect(t).toContain('Порядок версий');
    expect(t).toContain('Лист \\ версия');
    expect(t).toContain('только изменения');
    expect(t).toContain('Несвязанные страницы');
  });

  it('offers «Применить сопоставления (N)» and «Отменить правку» only while a draft exists', () => {
    const none = text(sheets());
    expect(none).not.toContain('Применить сопоставления');
    expect(none).not.toContain('Отменить правку');
    expect(none).toContain('Отменить последнюю правку');
    const drafting = text(sheets({ draft: DRAFT }));
    expect(drafting).toContain('Применить сопоставления (2)');
    expect(drafting).toContain('Отменить правку');
    expect(drafting).not.toContain('Отменить последнюю правку');
    expect(drafting).toContain('Выбрано правок: 2.');
    expect(drafting).toContain('Связать лист 7 (версия №3) с листом 6 (версия №1)');
    expect(drafting).toContain('Отвязать лист 1 (версия №2) в отдельную строку');
  });

  it('marks the cells a draft touches, and locks the table while a batch is applied', () => {
    expect(touchedPages(DRAFT).size).toBe(3);
    const markup = sheets({ draft: DRAFT });
    expect(markup).toContain('data-draft=""');
    expect(sheets({ applying: true })).toMatch(/<table[^>]*inert/);
    expect(sheets()).not.toMatch(/<table[^>]*inert/);
  });

  it('draws the flags of the original on the thumbnails', () => {
    const markup = sheets();
    for (const confidence of ['high', 'medium', 'group', 'manual', 'ai']) expect(markup, confidence).toContain(`data-cell-confidence="${confidence}"`);
    for (const flag of ['duplicate', 'scan', 'split', 'bridge']) expect(markup, flag).toContain(`data-cell-flag="${flag}"`);
    const t = text(markup);
    for (const mark of ['?', '▤ группа', '✎', 'ИИ', '⧉', 'скан', '◫', '⇉', '↷']) expect(t, mark).toContain(mark);
    expect(t).toContain('стр.4');
  });

  it('draws an unmatched cell with its reason, its candidates and the two commands, and an absent cell', () => {
    const t = text(sheets());
    expect(t).toContain('⁇ не сопоставлен');
    expect(t).toContain('отличительных признаков недостаточно');
    expect(t).toContain('сходство ниже порога пары');
    expect(t).toContain('кандидаты:');
    expect(t).toContain('Связать · стр. 7');
    expect(t).toContain('Связать · стр. 8');
    expect(t).toContain('Отметить, что этого листа в версии нет');
    expect(t).toContain('∅ нет в версии');
    expect(sheets()).toContain('aria-label="Отвязать лист в отдельную строку"');
  });

  it('a reader without the expert role sees no command: no «Связать», no «⤫», no draft, no order button', () => {
    const t = text(sheets({ mayEdit: false }));
    for (const command of ['Связать', 'Отметить, что этого листа в версии нет', 'Порядок версий', 'Применить сопоставления', 'Отменить последнюю правку']) {
      expect(t, command).not.toContain(command);
    }
    expect(sheets({ mayEdit: false })).not.toContain('Отвязать лист');
    expect(sheets({ mayEdit: false })).not.toContain('draggable="true"');
    expect(t).toContain('кандидаты:');
  });

  it('draws the transitions with progress, «Листов», «✓ ◐ ● ⚠», «Состав +N / −M» and the verdict sentence', () => {
    const t = text(sheets()).replace(/\s+;/g, ';');
    expect(t).toContain('Сводка переходов');
    for (const header of ['Переход (было → стало)', 'Ход расчёта', 'Листов', 'Состав', 'Вывод']) expect(t, header).toContain(header);
    for (const mark of ['✓', '◐', '●', '⚠']) expect(t, mark).toContain(mark);
    expect(t).toContain('№1 → №2');
    expect(t).toContain('№2 → №3');
    expect(t).toContain('+1 / −2');
    expect(t).toContain('есть отличия на 3 л. (из них только оформление линий — 1); изменён состав (+1 / −2 л.); нужна проверка: 1; ошибка расчёта: 1; 2 пар опираются на связь, предложенную ИИ');
    expect(t).toContain('основное содержание совпадает, изменены только служебные зоны');
    expect(t).toContain('переходов готово: 2 из 2');
    expect(t).toContain('7 из 7');
    expect(t).toContain('ошибок: 1');
  });

  it('offers the series commands for the state it is in: «Отменить», «Продолжить», «Досчитать»', () => {
    const t = (state: 'running' | 'paused' | 'failed' | 'completed') => text(sheets({ series: series({ state }) }));
    expect(t('running')).toContain('Отменить');
    expect(t('running')).not.toContain('Продолжить');
    expect(t('paused')).toContain('Продолжить');
    expect(t('paused')).toContain('Отменить');
    expect(t('failed')).toContain('Досчитать');
    expect(t('completed')).not.toContain('Досчитать');
    expect(text(sheets({ series: series({ state: 'paused' }), mayEdit: false }))).not.toContain('Продолжить');
  });

  it('says the stored summary is for the old order, why, and that a pair of non-neighbours is not compared', () => {
    const stale = text(sheets({ series: series({ stale_reasons: ['order_changed', 'matrix_changed'] }) }));
    expect(stale).toContain('Сохранённая сводка для прежнего порядка версий.');
    expect(stale).toContain('Что изменилось: порядок версий изменился; сопоставление листов изменилось.');
    expect(text(sheets())).not.toContain('Сохранённая сводка для прежнего порядка версий.');
    expect(text(sheets({ sides: { a: V1, b: V3 } }))).toContain('Пара собрана по цепочке через промежуточные версии и не сравнивалась');
    expect(text(sheets({ sides: { a: V2, b: V2 } }))).toContain('Выберите две разные версии.');
  });

  it('says there is no series yet and offers «Запустить» to an expert', () => {
    const t = text(sheets({ series: null, pairs: null }));
    expect(t).toContain('Сравнение соседних версий этого комплекта ещё не запускалось.');
    expect(t).toContain('Запустить');
    expect(text(sheets({ series: null, pairs: null, mayEdit: false }))).not.toContain('Запустить');
  });

  it('shows the status of each row\'s pair, and «только изменения» leaves the changed rows', () => {
    const markup = sheets();
    for (const status of ['same', 'same_zones_changed', 'different', 'needs_review', 'added', 'removed', 'unmatched']) {
      expect(markup, status).toContain(`data-sheet-status="${status}"`);
    }
    const t = text(markup);
    for (const label of ['Совпадает', 'Совпадает, изменены служебные зоны', 'Есть отличия', 'Нужна проверка', 'Лист добавлен', 'Лист удалён', 'Не сопоставлен']) expect(t, label).toContain(label);
    const changed = text(sheets({ onlyChanged: true }));
    expect(changed).toContain('(5 из 7)');
    expect(changed).not.toContain('Общие данные');
    expect(changed).toContain('План этажа 1');
    expect(text(sheets({ pairs: null, onlyChanged: true }))).toContain('Общие данные');
  });

  it('marks the sides «было» and «стало» on the columns', () => {
    const markup = sheets();
    expect(markup).toMatch(/aria-pressed="true"[^>]*>Было</);
    expect(markup).toMatch(/aria-pressed="true"[^>]*>Стало</);
    expect(text(markup)).toContain('Версия №2 · стр. 8');
  });

  it('shows the orphaned edits and the history, not hiding what no longer applies', () => {
    const markup = sheets();
    expect(text(markup)).toContain('Правки, которые больше не применяются (1).');
    expect(text(markup)).toContain('Эти правки сохранены, но больше не применяются');
    expect(text(markup)).toContain('История правок (5)');
    expect(markup).toContain('data-edit-status="orphaned"');
    for (const kind of ['link', 'unlink', 'mark_absent', 'undo']) expect(markup, kind).toContain(`data-edit-kind="${kind}"`);
    for (const source of ['expert', 'migrated_sheet_link']) expect(markup, source).toContain(`data-edit-source="${source}"`);
    const t = text(markup);
    expect(t).toContain('перенесена из подтверждённых пар прежнего экрана');
    expect(t).toContain('лист 3 (версия №1)');
  });

  it('says why a matrix is not ready: not built, being built, stale with its reasons, failed', () => {
    const state = (over: Parameters<typeof matrix>[0]) => text(sheets({ matrix: matrix({ ...over }) }));
    expect(state({ state: 'absent', rows: [], progress: { ready: 0, total: 0, failed: 0 } })).toContain('Сопоставление листов ещё не собиралось');
    const building = state({ state: 'building', rows: [], progress: { ready: 10, total: 24, failed: 1 } });
    expect(building).toContain('Идёт разбор версий и сопоставление листов');
    expect(building).toContain('Разбор версий: готово 10 из 24 · ошибок 1');
    const stale = state({ state: 'stale', stale_reasons: ['order_changed', 'profiles_changed'] });
    expect(stale).toContain('Сопоставление устарело');
    expect(stale).toContain('порядок версий изменился');
    expect(stale).toContain('версии или правила разбора изменились');
    expect(state({ state: 'failed', failure_reason: 'whatever_code', rows: [] })).toContain('Не удалось подготовить версии');
    expect(state({ state: 'failed', failure_reason: 'whatever_code', rows: [] })).not.toContain('whatever_code');
  });

  it('draws a draft\'s refusal, a rebase notice and the edits a rebase took out of the draft', () => {
    const failure = comparisonFailure(refusal('conflict', { conflict_reason: 'comparison_matrix_stale' }));
    const markup = sheets({
      draft: DRAFT, draftFailure: failure, notice: 'Сопоставление изменилось, пока вы правили.',
      dropped: [{ kind: 'unlink', page: page(V2, 40) }],
    });
    const t = text(markup);
    expect(t).toContain('Сопоставление листов изменилось после того, как вы его открыли');
    expect(t).toContain('ваши правки остались в черновике');
    expect(t).toContain('Эти правки не подходят к сопоставлению, которое изменилось, и убраны из черновика (1)');
    expect(t).toContain('Отвязать лист 40 (версия №2) в отдельную строку');
    expect(markup).toContain('data-draft-notice');
  });

  it('puts the viewer in its slot and the order dialog above the tables', () => {
    const t = text(sheets({ viewer: createElement('p', null, 'Просмотр пары листов'), orderDialog: createElement('p', null, 'Диалог порядка') }));
    expect(t).toContain('Просмотр пары листов');
    expect(t).toContain('Диалог порядка');
    expect(sheets()).not.toContain('data-pair-viewer');
  });

  it('writes no Latin word a reader would read', () => {
    const readable = text(sheets({ draft: DRAFT, dropped: [{ kind: 'unlink', page: page(V2, 40) }] }));
    expect(readable).not.toMatch(LATIN);
  });
});

// ------------------------------------------------------------------------------ the page

describe('the page «Сравнение версий»', () => {
  const page_ = (seed: Parameters<typeof seedComparison>[1] = {}, initial: Parameters<typeof VersionComparePage>[0] = {}): string => {
    const client = newClient();
    seedComparison(client, seed);
    return renderScreen(client, createElement(VersionComparePage, initial));
  };

  it('is a menu item in «Работа», in the registry, with an address a builder builds', () => {
    const row = screenAt('/version-comparison');
    expect(row).toMatchObject({ label: 'Сравнение версий', group: 'work', roles: 'any-role', inMenu: true, access: 'session' });
    expect(routes.versionComparison()).toBe('/version-comparison');
    const menu = buildNavigation({ roles: ['expert'], isDefaultCredential: false, profileComplete: true });
    const work = menu.groups.find((group) => group.group === 'work');
    expect(work?.items.map((item) => item.label)).toContain('Сравнение версий');
    expect(SCREEN_REGISTRY.filter((screen) => screen.label === 'Сравнение версий').length).toBe(1);
  });

  it('asks for a project first, and takes the only project without a click', () => {
    const t = text(page_({ overview: 'none' }));
    expect(t).toContain('Корпус 1');
    const client = newClient();
    seedComparison(client, { overview: 'ok' });
    client.setQueryData(queryKeys.projects.list(undefined, 50), { items: [], page: { next_cursor: null } });
    expect(text(renderScreen(client, createElement(VersionComparePage, {})))).toContain('Проектов пока нет.');
  });

  it('shows the two tabs, the button «Загрузить проект со всеми версиями», and the table once a project is chosen', () => {
    const markup = page_({}, { initial: { projectUid: PROJECT_UID } });
    const t = text(markup);
    expect(t).toContain('Проекты и этапы');
    expect(t).toContain('Сравнение листов');
    expect(t).toContain('Загрузить проект со всеми версиями');
    expect(markup).toContain('data-comparison-overview');
    expect(markup).toMatch(/data-compare-tab="sheets"[^>]*disabled|disabled[^>]*data-compare-tab="sheets"/);
  });

  it('opens the sheets tab for the chosen set, with the viewer slot composed by the page', () => {
    const markup = page_({ sheets: true }, { initial: { projectUid: PROJECT_UID, tab: 'sheets', documentUid: DOCUMENT_UID } });
    expect(markup).toContain('data-comparison-sheets');
    expect(text(markup)).toContain('· версий: 3');
  });

  it('A MODULE THAT IS NOT WIRED (503) IS A STATE, NOT A CRASH: «Модуль ещё недоступен»', () => {
    const markup = page_({ overview: 'wired-not' }, { initial: { projectUid: PROJECT_UID } });
    expect(markup).toContain('data-comparison-module="unavailable"');
    const t = text(markup);
    expect(t).toContain('Модуль ещё недоступен');
    expect(t).toContain('Модуль «Сравнение версий» ещё недоступен. На этом стенде пока не подключена его часть: сводка по комплектам.');
    expect(markup).not.toContain('data-comparison-overview');
    expect(markup).not.toContain('data-comparison-failure');
    expect(markup).not.toContain('Сводка по комплектам не открылась');
  });

  it('shows every other failure as an error with the correlation id, and a matrix that is not wired as the module state too', () => {
    const t = text(page_({ overview: 'error' }, { initial: { projectUid: PROJECT_UID } }));
    expect(t).toContain('Сводка по комплектам не открылась');
    expect(t).toContain('Идентификатор корреляции');
    const client = newClient();
    seedComparison(client, {});
    seedError(client, COMPARISON_KEYS.matrix(PROJECT_UID, DOCUMENT_UID), refusal('dependency_unavailable', { dependency: 'comparison_matrix' }));
    const sheetsMarkup = renderScreen(client, createElement(VersionComparePage, { initial: { projectUid: PROJECT_UID, tab: 'sheets', documentUid: DOCUMENT_UID } }));
    expect(sheetsMarkup).toContain('data-comparison-module="unavailable"');
    expect(text(sheetsMarkup)).toContain('пока не подключена его часть: сопоставление листов.');
  });

  it('says the module is off when the product says so, and draws no button that sends anything', () => {
    const markup = page_({ modules: 'none' }, { initial: { projectUid: PROJECT_UID } });
    expect(markup).toContain('data-comparison-module="off"');
    expect(text(markup)).toContain('Модуль «Сравнение версий» выключен');
    expect(markup).not.toContain('data-step-action');
    expect(markup).toMatch(/<button[^>]*disabled=""[^>]*>Загрузить проект со всеми версиями/);
  });

  it('does not take an unread module set for an off one', () => {
    const markup = page_({ modules: null }, { initial: { projectUid: PROJECT_UID } });
    expect(markup).not.toContain('data-comparison-module="off"');
    expect(markup).toContain('data-step-action');
  });

  it('draws no command for a reader who is not an expert, and says why on the upload button', () => {
    const markup = page_({ account: READER }, { initial: { projectUid: PROJECT_UID } });
    expect(markup).not.toContain('data-step-action');
    expect(markup).toContain('Загружать версии для сравнения может эксперт');
  });

  it('opens the upload dialog the page was told to open', () => {
    const t = text(page_({}, { initial: { projectUid: PROJECT_UID, upload: 'single' } }));
    expect(t).toContain('Загрузка проекта и версий');
    const batch = text(page_({}, { initial: { projectUid: PROJECT_UID, upload: 'batch' } }));
    expect(batch).toContain('Загрузка нескольких проектов');
  });

  it('cold, it renders the loading state of the projects and nothing else', () => {
    const t = text(renderScreen(newClient(), createElement(VersionComparePage, {})));
    expect(t).toContain('Загрузка: проекты…');
  });
});

// ------------------------------------------------------------------------------ the upload dialogs

function dialogProps(over: Partial<UploadDialogViewProps> = {}): UploadDialogViewProps {
  return {
    mode: 'single', phase: 'pick', groups: [], skipped: 0, problem: null, compare: false, hashing: null, upload: undefined, loading: false,
    sets: [], drafts: {}, fileNames: new Map(), progress: new Map(), fileFailures: new Map(), missing: [], failure: null, unfinished: [],
    notice: null, mayAct: true, busy: false, onPick: noop, onRemoveGroup: noop, onCompare: noop, onSend: noop, onStop: noop,
    onContinue: noop, onOpenUnfinished: noop, onDraft: noop, onConfirm: noop, onConfirmAll: noop, onProposedAll: noop, onExclude: noop,
    onRetry: noop, onPause: noop, onResume: noop, onDelete: noop, onSwitch: noop, onClose: noop, ...over,
  };
}
const dialog = (over: Partial<UploadDialogViewProps> = {}): string => renderToStaticMarkup(createElement(UploadDialogView, dialogProps(over)));
const names = new Map((upload().files ?? []).map((file) => [file.file_id, file.display_name] as const));

describe('the upload dialogs', () => {
  it('«Загрузка проекта и версий» picks a folder or files, says only PDFs go, and leads to the batch', () => {
    const t = text(dialog());
    expect(t).toContain('Загрузка проекта и версий');
    expect(t).toContain('Выберите папку с PDF (вложенные папки тоже читаются) или отдельные файлы. Исходные файлы не изменяются.');
    expect(t).toContain('Выбрать папку');
    expect(t).toContain('Выбрать файлы');
    expect(t).toContain('ZIP-комплекты пока не принимаются: загрузите PDF.');
    expect(t).toContain('Пакетная загрузка: каждая папка — отдельный проект со своими версиями.');
    expect(t).not.toContain('После подготовки сравнить все соседние версии');
  });

  it('«Загрузка нескольких проектов» has the two folder buttons, the flag, and the picked projects', () => {
    const t = text(dialog({ mode: 'batch', groups: [{ group: 'Проекты/ЭМ', files: [], bytes: 3 * 1024 * 1024 }] }));
    expect(t).toContain('Загрузка нескольких проектов');
    expect(t).toContain('Добавить папку');
    expect(t).toContain('Добавить папку с проектами');
    expect(t).toContain('После подготовки сравнить все соседние версии');
    expect(t).toContain('Проекты/ЭМ');
    expect(t).toContain('Загрузить пакет');
    expect(t).not.toContain('Пакетная загрузка: каждая папка');
  });

  it('says what is wrong before sending, and that a read-only reader may not send', () => {
    expect(text(dialog({ problem: 'file_too_large' }))).toContain('Один из файлов больше 250 МиБ');
    expect(dialog({ mayAct: false })).toContain('data-upload-readonly');
    expect(dialog({ mayAct: false })).toMatch(/<button[^>]*disabled=""[^>]*>Загрузить и разобрать/);
  });

  it('shows the transfer: the files with their state, «Остановить загрузку» while it runs, «Продолжить загрузку» once stopped', () => {
    const sending = dialog({ phase: 'sending', upload: upload({ state: 'uploading' }), progress: new Map([[(upload().files ?? [])[1]?.file_id ?? '', { done: 5, total: 10 }]]) });
    expect(text(sending)).toContain('Остановить загрузку');
    expect(sending).toContain('<progress');
    for (const state of ['verified', 'uploading', 'failed', 'declared']) expect(sending, state).toContain(`data-file-state="${state}"`);
    const t = text(sending);
    for (const word of ['принят', 'передаётся', 'ошибка', 'ждёт отправки']) expect(t, word).toContain(word);
    expect(t).toContain('Контрольная сумма принятого файла не совпала с заявленной. Отправьте файл заново.');
    const stopped = text(dialog({ phase: 'stopped', upload: upload({ state: 'uploading' }), missing: ['x', 'y'] }));
    expect(stopped).toContain('Продолжить загрузку');
    expect(stopped).toContain('Выбрать те же файлы');
    expect(stopped).toContain('Не хватает файлов: 2.');
  });

  it('shows the proposal: the sets with their status labels, warnings, stage and section, the file order and labels', () => {
    const markup = dialog({ upload: upload(), sets: proposalSets(), fileNames: names, phase: 'watching' });
    const t = text(markup);
    for (const status of ['Загрузка', 'Разбор PDF', 'Требуется проверка', 'Ожидает обработки', 'Подготовка версий', 'Готово', 'Ошибка', 'Исключён']) expect(t, status).toContain(status);
    for (const state of ['uploading', 'reading', 'needs_confirmation', 'ready', 'admitting', 'done', 'failed', 'excluded']) expect(markup, state).toContain(`data-set-status="${state}"`);
    for (const warning of ['designations_differ', 'order_disagrees_with_file_numbers', 'duplicate_revision_number', 'no_stamp_found', 'scan_without_text']) expect(markup, warning).toContain(`data-proposal-warning="${warning}"`);
    expect(t).toContain('⚠ В файлах разные шифры.');
    expect(t).toContain('Предложено: стадия П — проектная, раздел «');
    expect(t).toContain('Номер в имени файла, «Изм.» и дата выпуска — подсказки; порядок версий задаёте вы.');
    expect(t).toContain('Подтвердить группировку и порядок');
    expect(t).toContain('Комплектов в загрузке больше 100: этот не поместился');
    expect(markup).toContain('value="Версия 1 Изм.0 15.01.2026"');
  });

  it('the single dialog confirms all sets at once, the batch dialog one by one and all together', () => {
    const single = text(dialog({ upload: upload(), sets: proposalSets(), fileNames: names, phase: 'watching' }));
    expect(single).toContain('Подтвердить группировку и порядок');
    expect(single).not.toContain('Подтвердить состав и порядок');
    expect(single).not.toContain('Подтвердить порядок во всех проектах');
    const batch = text(dialog({ mode: 'batch', upload: upload({ state: 'processing' }), sets: proposalSets(), fileNames: names, phase: 'watching' }));
    expect(batch).toContain('Подтвердить состав и порядок');
    expect(batch).toContain('Подтвердить порядок во всех проектах');
    expect(batch).toContain('Исключить');
    expect(batch).toContain('Повторить');
    expect(batch).toContain('Пауза после текущего проекта');
    expect(batch).toContain('Удалить пакет');
    expect(text(dialog({ mode: 'batch', upload: upload({ state: 'paused' }), phase: 'watching' }))).toContain('Продолжить обработку');
  });

  it('offers a set only the commands its state allows', () => {
    const only = (state: 'needs_confirmation' | 'failed' | 'done') =>
      text(dialog({ mode: 'batch', upload: upload(), sets: proposalSets().filter((set) => set.state === state), fileNames: names, phase: 'watching' }));
    expect(only('needs_confirmation')).toContain('Подтвердить состав и порядок');
    expect(only('needs_confirmation')).toContain('Исключить');
    expect(only('needs_confirmation')).not.toContain('Повторить');
    expect(only('failed')).toContain('Повторить');
    expect(only('failed')).toContain('Исключить');
    expect(only('failed')).not.toContain('Подтвердить состав и порядок');
    expect(only('done')).not.toContain('Исключить');
  });

  it('shows the batch\'s flag after the batch was declared, an unfinished upload to open again, and a finished one', () => {
    expect(text(dialog({ mode: 'batch', upload: upload({ compare_after_preparation: true }), phase: 'watching' }))).toContain('После подготовки будут сравнены все соседние версии.');
    const t = text(dialog({ unfinished: [upload()] }));
    expect(t).toContain('Незавершённые загрузки');
    expect(t).toContain('ждёт подтверждения · файлов 3');
    expect(t).toContain('Открыть');
    expect(text(dialog({ upload: upload({ state: 'completed' }) }))).toContain('Загрузка завершена.');
    expect(text(dialog({ phase: 'hashing', hashing: { done: 1, total: 4 } }))).toContain('Считаем контрольные суммы: файл 2 из 4…');
    expect(UPLOAD_ID).toMatch(/^cbt_/);
  });
});

// ------------------------------------------------------------------------------ «Очередь»

describe('the block «Сравнение» of «Очередь»', () => {
  it('shows the modules, the pause, the counts, the oldest queued item and the kinds', () => {
    const markup = renderToStaticMarkup(createElement(ComparisonQueueBlockView, { summary: queueSummary({ paused: true }) }));
    const t = text(markup);
    expect(t).toContain('Сравнение');
    expect(t).toContain('Включён модуль «Сравнение версий».');
    expect(t).toContain('Выдача задач приостановлена для всей установки');
    for (const count of ['ждут: 5', 'идут: 2', 'с ошибкой: 1', 'выполнены: 40', 'расход неизвестен: 1']) expect(t, count).toContain(count);
    expect(t).toContain('Самая давняя из ждущих принята 2026-10-28 08:00:00 UTC');
    expect(t).toContain('Разбор страниц версии');
    expect(t).toContain('Сборка сопоставления листов');
    expect(t).toContain('Другая работа сравнения');
    expect(markup).toContain('data-queue-module="stages"');
    expect(markup).toContain('data-queue-kind="stage_pairing"');
    expect(t).not.toContain('page_profile');
  });

  it('says so when there is no comparison work, in each module setting', () => {
    const empty = queueSummary({
      kinds: [], oldest_queued_at: undefined as never,
      counts: { cancelled: 0, failed: 0, leased: 0, paused: 0, queued: 0, retry_wait: 0, running: 0, spend_unknown: 0, succeeded: 0 },
    });
    delete (empty as { oldest_queued_at?: unknown }).oldest_queued_at;
    for (const [modules, sentence] of [
      ['none', 'Модули сравнения выключены: работа не берётся.'],
      ['versions', 'Включён модуль «Сравнение версий».'],
      ['versions,stages', 'Включены модули «Сравнение версий» и «Сравнение стадий».'],
    ] as const) {
      const markup = renderToStaticMarkup(createElement(ComparisonQueueBlockView, { summary: { ...empty, modules } }));
      expect(text(markup), modules).toContain(sentence);
      expect(text(markup)).toContain('Работы сравнения в очереди нет.');
      expect(markup).toContain(`data-comparison-modules="${modules}"`);
    }
  });

  it('reads the summary through the query: loading, the module that is not wired, and any other failure', () => {
    expect(text(renderWith(newClient(), createElement(ComparisonQueueBlock)))).toContain('Загрузка: сводку сравнения…');
    const unwired = newClient();
    seedError(unwired, COMPARISON_KEYS.queue(), refusal('dependency_unavailable', { dependency: 'comparison_overview' }));
    const markup = renderWith(unwired, createElement(ComparisonQueueBlock));
    expect(markup).toContain('data-comparison-module="unavailable"');
    expect(text(markup)).toContain('Модуль сравнения ещё недоступен');
    const broken = newClient();
    seedError(broken, COMPARISON_KEYS.queue(), refusal('internal_error'));
    expect(text(renderWith(broken, createElement(ComparisonQueueBlock)))).toContain('Сводка сравнения не открылась');
  });

  it('is under the queue wherever there is a query provider, and absent where the list is rendered bare', () => {
    const items = [] as never[];
    const props = { items, roles: [], asOf: null, busy: false, workerOf: () => ({ kind: 'none' }) as never, onCancel: noop, onReaudit: noop, onPriority: noop, onNext: null, onPrevious: null };
    const client = newClient();
    client.setQueryData(COMPARISON_KEYS.queue(), queueSummary());
    expect(text(renderWith(client, createElement(ExecutionQueue, props as never)))).toContain('Включён модуль «Сравнение версий».');
    expect(renderToStaticMarkup(createElement(ExecutionQueue, props as never))).not.toContain('data-comparison-queue');
  });
});

// ------------------------------------------------------------------------------ A-12 and the heading

describe('A-12: the version-scoped screen after the matrix took over the sheet pairs', () => {
  const proposed: SheetPairing = {
    status: 'unchanged', source_page_number: 3, target_page_number: 3, suggestion_sha256: 'f'.repeat(64), basis: 'sheet_number',
  } as unknown as SheetPairing;
  const comparison = (approved: boolean) => ({
    project_uid: PROJECT_UID, document_uid: DOCUMENT_UID, source_version_uid: V1, target_version_uid: V2, mode: 'version',
    outcome: 'compared', refusal: null, comparison_sha256: 'e'.repeat(64), sheets: [proposed],
    approved_pairs: {
      evidence_state: approved ? 'sealed' : 'none', link_revision: approved ? 1 : null, raw_evidence_seal_sha256: approved ? 'd'.repeat(64) : null,
      summary: null,
      items: approved
        ? [{ sheet_link_id: 'lnk_1', source_page_number: 3, target_page_number: 3, approved_by_label: 'Сьютова Е.', approved_at: '2026-10-20T10:00:00Z', state: 'verified', diff: null }]
        : [],
    },
    sheet_diffs: null, findings: null, source: null, target: null,
  });
  const render = (handedOver: boolean, approved = false): string =>
    renderWith(newClient(), createElement(ComparisonResult, { comparison: comparison(approved) as never, onPage: noop, carry: null, mayApprove: true, handedOver }));

  it('offers «Подтвердить пару» and «Подготовить сводку» while the versions module is off', () => {
    const t = text(render(false));
    expect(t).toContain('Подтвердить пару');
    expect(render(false)).not.toContain('data-comparison-handed-over');
  });

  it('offers none of the three controls once the versions module is on, and points to «Сравнение версий»', () => {
    const t = text(render(true));
    expect(t).not.toContain('Подтвердить пару');
    expect(t).not.toContain('Подтвердить пару может эксперт');
    expect(t).not.toContain('Отозвать');
    expect(t).not.toContain('Подготовить сводку');
    expect(t).toContain('перенесены в раздел «Сравнение версий»');
    expect(render(true)).toContain('href="/version-comparison"');
    expect(render(true)).toContain('data-comparison-handed-over');
  });

  it('keeps an approval of the old record readable, without «Отозвать», and withdraws nothing', () => {
    expect(text(render(false, true))).toContain('Отозвать');
    const handed = text(render(true, true));
    expect(handed).not.toContain('Отозвать');
    expect(handed).toContain('Пара подтверждена: Сьютова Е.');
    expect(render(true, true)).toContain('data-pairing-state="approved-read-only"');
  });

  it('reads the module set from the product version: known to name the versions module hides, unknown does not', () => {
    // The widget reads `ProductVersion.comparison_modules`; the flag is the only thing that moves, so the unread case is the old screen.
    expect(text(render(false))).toContain('Подтвердить пару');
  });
});

describe('the heading of the version-scoped screen', () => {
  it('no longer reads like the menu item «Сравнение версий»', () => {
    const markup = renderScreen(newClient(), createElement(StageComparisonPage, { projectUid: PROJECT_UID, versionUid: V1 }));
    expect(markup).toContain('Сравнение этой версии и её прогонов');
    expect(markup).not.toMatch(/<h1[^>]*>Сравнение версий<\/h1>/);
    const malformed = renderScreen(newClient(), createElement(StageComparisonPage, { projectUid: 'x', versionUid: 'y' }));
    expect(malformed).toContain('Сравнение этой версии и её прогонов');
    expect(transition({ transition_id: uid('ctn', 5), source_version_uid: V1, target_version_uid: V2 }).state).toBe('completed');
    expect(series().state).toBe('completed');
  });
});

