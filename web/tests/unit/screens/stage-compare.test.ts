import { SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { StageComparePage } from '@/_pages/stage-compare';
import { queryKeys } from '@/shared/api';
import { PROJECT_PAGE_LIMIT } from '@/entities/project';
import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';

import { newClient, renderScreen } from './harness';
import { DOCUMENT_UID, PROJECT_UID, uid } from '../version-compare/fixtures';
import { EXPERT, READER, seedComparison } from '../version-compare/seed';

const RIGHT = uid('doc', 18);
const PAIR = uid('stp', 19);
const RUN = uid('crn', 40);

const PAIR_ROW = { pair_id: PAIR, project_uid: PROJECT_UID, left_document_uid: DOCUMENT_UID, right_document_uid: RIGHT, completeness: 'unknown', state: 'confirmed', created_at: '2026-10-29T00:00:00Z' } as const;
const RUN_ROW = {
  run_id: RUN, pair_id: PAIR, kind: 'full', state: 'running', stale: false, created_at: '2026-11-01T10:00:00Z', updated_at: '2026-11-01T10:05:00Z',
  input_sha256: 'a'.repeat(64), link_revision_id: uid('slk', 41), pinned_version_uids: [], with_ai: true, engine: 'classic',
  steps: [1, 2, 3, 4, 5, 6, 7].map((no) => ({ step_id: uid('cst', no), step_no: no, state: no < 5 ? 'completed' : 'running', counts: {} })),
} as const;
const NAMES = new Map([
  [DOCUMENT_UID, { title: 'Пояснительная записка', section: 'AR', stage: 'P' }],
  [RIGHT, { title: 'Пояснительная записка, редакция 2', section: 'AR', stage: 'R' }],
]);

/**
 * The screen's address is a query in the provider. The object is the top strip's (`UIP-S16-01`), so it is in the address too:
 * `?project=<uid>` unless the case is about an address that names none.
 */
function at(client: ReturnType<typeof newClient>, query: string): string {
  return renderScreen(client, createElement(SearchParamsContext.Provider, { value: new URLSearchParams(query) }, createElement(StageComparePage)));
}

const OBJECT = `project=${PROJECT_UID}`;

/** The screen on a given step: the address is what the screen reads, so the step is a query in the provider. */
function onStep(query: string, expert = true): string {
  const client = newClient();
  seedComparison(client, { modules: 'versions,stages', ...(expert ? {} : { account: READER }) });
  client.setQueryData([...STAGE_PAIR_KEYS.projectPairs(PROJECT_UID), 'workspace'], [PAIR_ROW]);
  client.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID), { items: [PAIR_ROW], page: { next_cursor: null }, unpaired_p_count: 0, unpaired_r_count: 0 });
  client.setQueryData(STAGE_PAIR_KEYS.documents(PROJECT_UID), NAMES);
  client.setQueryData(['stage-full-runs', PAIR], [RUN_ROW]);
  client.setQueryData(['stage-full-run', RUN], RUN_ROW);
  client.setQueryData(['stage-run-card-counts', RUN], { total: 9, review: 3, project_changes: 5 });
  return at(client, query === '' ? OBJECT : `${OBJECT}&${query}`);
}

function loaded(expert = true): string {
  const client = newClient();
  seedComparison(client, { modules: 'versions,stages', ...(expert ? {} : { account: READER }) });
  client.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID), {
    items: [{ pair_id: PAIR, project_uid: PROJECT_UID, left_document_uid: DOCUMENT_UID, right_document_uid: RIGHT, completeness: 'unknown', state: 'confirmed', created_at: '2026-10-29T00:00:00Z' }],
    page: { next_cursor: null }, unpaired_p_count: 3, unpaired_r_count: 2,
  });
  client.setQueryData(STAGE_PAIR_KEYS.suggestions(PROJECT_UID), {
    items: [{ left_document_uid: uid('doc', 20), right_document_uid: uid('doc', 21), reason: 'section_designation_exact', score: 1 }],
    page: { next_cursor: null },
  });
  const fileId = uid('suf', 22);
  client.setQueryData(['comparison', 'stage-uploads', PROJECT_UID, ''], {
    items: [{
      upload_id: uid('stu', 23), project_uid: PROJECT_UID, state: 'completed',
      created_at: '2026-10-29T00:00:00Z', updated_at: '2026-10-29T00:00:00Z',
      files: [{
        file_id: fileId, upload_id: uid('stu', 23), state: 'ready',
        declaration: { display_name: 'АР-01.pdf', media_kind: 'pdf', size_bytes: 12, sha256: 'a'.repeat(64) },
        received_parts: 1, received_bytes: 12, created_at: '2026-10-29T00:00:00Z',
      }],
      candidates: [{
        candidate_id: uid('suc', 24), file_id: fileId, member_number: 1,
        display_name: 'АР-01.pdf', state: 'proposed',
      }],
    }],
    page: { next_cursor: null },
  });
  return at(client, OBJECT);
}

describe('stage comparison catalog', () => {
  it('shows the nonbinding suggestions as rows of the pairs table, marked as such, and offers expert acts (UIP-S16-04)', () => {
    const html = loaded();
    expect(html).toContain('Пары стадий');
    expect(html).toContain('Наборы PDF и ZIP');
    expect(html).toContain('Загрузить новый набор');
    expect(html).toContain('АР-01.pdf');
    expect(html).toContain('Подтвердить документ');
    expect(html).not.toContain('Возможные пары');
    expect(html).toContain('Полнота не указана');
    const table = html.slice(html.indexOf('<table'), html.indexOf('</table>'));
    expect(table).toContain('>предложение<');
    expect(table).toContain('Совпадают раздел и подтверждённый шифр');
    expect(table).toMatch(/data-pair-confirm=""[^>]*>Подтвердить</);
    expect(html).not.toContain('Проверить связь');
    expect(html).toContain('Полный');
    expect(html).toContain('3. Изменения проекта');
    expect(html).toContain('4. Отчёт');
    expect(html).toContain(`href="/projects/${PROJECT_UID}/documents/${DOCUMENT_UID}"`);
  });

  it('keeps the catalog readable for a nonexpert but withholds decisions', () => {
    const html = loaded(false);
    expect(html).toContain('Пары стадий');
    expect(html).toContain('Наборы PDF и ZIP');
    expect(html).not.toContain('Загрузить новый набор');
    expect(html).toContain('АР-01.pdf');
    expect(html).not.toContain('Подтвердить документ');
    expect(html).toContain('>предложение<');
    expect(html).not.toContain('data-pair-confirm');
    expect(html).not.toContain('>Неполный</button>');
  });

  it('does not mount the catalog when the stages module is off', () => {
    const client = newClient();
    seedComparison(client, { modules: 'versions' });
    const html = at(client, OBJECT);
    expect(html).toContain('Модуль «Сравнение стадий» выключен');
    expect(html).not.toContain('Пары стадий');
    expect(html).not.toContain('Наборы PDF и ZIP');
    expect(html).not.toContain('Возможные пары');
  });
});

describe('stage comparison steps (UI-B-84, UI-B-85, UI-B-88, UI-B-93)', () => {
  it('opens on the first step: the bar, then the catalog as a table with the documents named; no pair selectors yet', () => {
    const html = onStep('');
    expect(html.indexOf('role="tablist"')).toBeGreaterThan(-1);
    expect(html.indexOf('role="tablist"')).toBeLessThan(html.indexOf('Пары стадий'));
    for (const header of ['Документ / раздел', 'Метод и модель', 'Дата', 'Изменения', 'Требуют проверки', 'Статус']) expect(html).toContain(header);
    expect(html).not.toContain('Проект / раздел');
    expect(html).toContain('Пояснительная записка · AR');
    expect(html).toContain('Пояснительная записка, редакция 2 · AR');
    expect(html).toContain('Цепочка · с ИИ');
    expect(html).not.toContain('data-stage-pair-select');
    expect(html).not.toContain('Семь шагов сравнения');
  });

  it('puts «Загрузить документы» at the bar for an expert, and withholds it from a reader', () => {
    const expert = onStep('');
    expect(expert).toContain('data-stage-upload-open');
    expect(expert).toContain('>Загрузить документы<');
    expect(expert).not.toContain('Загрузить проекты');
    expect(expert.indexOf('data-stage-upload-open')).toBeLessThan(expert.indexOf('Пары стадий'));
    expect(onStep('', false)).not.toContain('data-stage-upload-open');
  });

  it('keeps the upload panel closed until the button asks for it', () => {
    expect(onStep('')).toMatch(/<section[^>]*id="stage-upload-panel"[^>]*hidden/);
  });

  it('shows the pair and run selectors and the rail of seven steps under the bar on the sheet-map step', () => {
    const html = onStep('tab=sheets');
    expect(html.indexOf('role="tablist"')).toBeLessThan(html.indexOf('data-stage-pair-select'));
    expect(html.indexOf('data-stage-pair-select')).toBeLessThan(html.indexOf('Семь шагов сравнения'));
    expect(html).toContain('Пояснительная записка · AR → Пояснительная записка, редакция 2 · AR');
    for (const number of [1, 2, 3, 4, 5, 6, 7]) expect(html).toContain(`data-stage-step="${number}"`);
    expect(html).toContain('Остановить сравнение');
    expect(html).not.toContain('Пары стадий');
  });

  it('draws the rail on the changes step too, and not on the report step', () => {
    expect(onStep('tab=changes')).toContain('Семь шагов сравнения');
    const report = onStep('tab=journal');
    expect(report).toContain('data-stage-pair-select');
    expect(report).not.toContain('Семь шагов сравнения');
  });

  it('marks the step of the address as selected, with the others out of the tab order', () => {
    const html = onStep('tab=changes');
    expect(html).toMatch(/data-stage-tab="changes"[^>]*aria-selected="true"[^>]*tabindex="0"/);
    expect(html).toMatch(/data-stage-tab="documentation"[^>]*aria-selected="false"[^>]*tabindex="-1"/);
  });
});

describe('the top row of «Сравнение стадий» and its object (UIP-S16-01)', () => {
  const html = onStep('');

  it('has no heading line: no subtitle, no link to «Сравнение версий», no card that chooses the object', () => {
    expect(html).not.toContain('am-page__header');
    expect(html).not.toContain('am-page__subtitle');
    expect(html).not.toContain('Документы П и Р, подтверждённые пары и полнота комплекта.');
    expect(html).not.toContain('href="/version-comparison');
    expect(html).not.toMatch(/<label[^>]*>Объект/);
    expect(html).not.toContain('— выберите —');
  });

  it('keeps the heading for a reader of the screen: first in the markup, out of the flow', () => {
    expect(html).toMatch(/<h1[^>]*>Сравнение стадий<\/h1>/);
    expect(html.indexOf('<h1')).toBeLessThan(html.indexOf('role="tablist"'));
    expect(html).not.toContain('am-page__title');
  });

  it('is one line of the four steps at the left and «Загрузить документы» at the right, for an expert only', () => {
    const steps = [...html.matchAll(/data-stage-tab="(\w+)"/g)].map((match) => match[1]);
    expect(steps).toEqual(['documentation', 'sheets', 'changes', 'journal']);
    const between = html.slice(html.indexOf('role="tablist"'), html.indexOf('data-stage-upload-open'));
    expect(between).not.toMatch(/<(section|table|h[1-6]|label)\b/);
    expect(onStep('', false)).not.toContain('Загрузить документы');
  });

  it('does not offer «Загрузить документы» on the other steps: they are for the pair already loaded', () => {
    for (const step of ['tab=sheets', 'tab=changes', 'tab=journal']) expect(onStep(step)).not.toContain('Загрузить документы');
  });
});

describe('the object of «Сравнение стадий» is the one of the top strip (UIP-S16-01, UIP-G-06)', () => {
  function bare(query: string, last: string | null = null, seed: Parameters<typeof seedComparison>[1] = {}): string {
    const client = newClient();
    seedComparison(client, { modules: 'versions,stages', ...seed });
    client.setQueryData(queryKeys.account.me(), { ...EXPERT, last_project_uid: last });
    client.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID), { items: [PAIR_ROW], page: { next_cursor: null }, unpaired_p_count: 0, unpaired_r_count: 0 });
    return at(client, query);
  }

  it('opens on the object of the address', () => {
    expect(bare(OBJECT)).toContain(`data-stage-workspace="${PROJECT_UID}"`);
  });

  it('opens on the account\'s last object where the address names none', () => {
    expect(bare('', PROJECT_UID)).toContain(`data-stage-workspace="${PROJECT_UID}"`);
  });

  it('asks for an object in the top strip, in one line, for «Все объекты» and for no object, and opens no workspace', () => {
    for (const markup of [bare('project=all', PROJECT_UID), bare('', null)]) {
      expect(markup).toContain('Выберите объект в верхней строке');
      expect(markup).not.toContain('data-stage-workspace');
      expect(markup).not.toContain('role="tablist"');
    }
  });

  it('does not pick the only object for the reader: with one object and none chosen the strip is asked as well', () => {
    expect(bare('', null)).toContain('Выберите объект в верхней строке');
  });

  it('says there are no objects, and not that one is to be chosen, when the account has none', () => {
    const client = newClient();
    seedComparison(client, { modules: 'versions,stages', projects: false });
    client.setQueryData(queryKeys.projects.list(undefined, PROJECT_PAGE_LIMIT), { items: [], page: { next_cursor: null } });
    const markup = at(client, '');
    expect(markup).toContain('Объектов пока нет');
    expect(markup).not.toContain('Выберите объект в верхней строке');
  });

  it('draws nothing of the screen but its heading where the module is off, whichever object is chosen', () => {
    const markup = bare(OBJECT, null, { modules: 'versions' });
    expect(markup).toContain('Модуль «Сравнение стадий» выключен');
    expect(markup).not.toContain('Выберите объект в верхней строке');
  });
});

/** The text of the markup as a reader gets it: React's separators between a literal and an expression are not in it. */
const plain = (html: string): string => html.replace(/<!-- -->/g, '');

describe('the line over the table of pairs (UIP-S16-03)', () => {
  /** The catalog with the pairs and the suggestions given: `loaded` fixes one suggestion, this one lets a case choose. */
  function catalog(options: { expert?: boolean; suggestions?: number; unpaired?: [number, number]; nextCursor?: string | null } = {}): string {
    const { expert = true, suggestions = 1, unpaired = [3, 2], nextCursor = null } = options;
    const client = newClient();
    seedComparison(client, { modules: 'versions,stages', ...(expert ? {} : { account: READER }) });
    client.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID), {
      items: [PAIR_ROW], page: { next_cursor: nextCursor }, unpaired_p_count: unpaired[0], unpaired_r_count: unpaired[1],
    });
    client.setQueryData(STAGE_PAIR_KEYS.suggestions(PROJECT_UID), {
      items: Array.from({ length: suggestions }, (_, index) => ({
        left_document_uid: uid('doc', 20 + index), right_document_uid: uid('doc', 60 + index), reason: 'section_designation_exact', score: 1,
      })),
      page: { next_cursor: null },
    });
    client.setQueryData(STAGE_PAIR_KEYS.documents(PROJECT_UID), NAMES);
    return plain(at(client, OBJECT));
  }

  it('says «Сопоставлено · Возможных · Только П · Только Р» in one line, the last two as the server counted them', () => {
    const html = catalog({ suggestions: 2, unpaired: [7, 4] });
    expect(html).toMatch(/data-pair-counters="">Сопоставлено: 1 · Возможных: 2 · Только П: 7 · Только Р: 4</);
  });

  it('says zero documents without a pair as a number, and not as nothing', () => {
    expect(catalog({ unpaired: [0, 0] })).toContain('Только П: 0 · Только Р: 0');
  });

  it('keeps the matched and the possible pairs of a page as the page\'s, and the server\'s counts as the object\'s', () => {
    const html = catalog({ nextCursor: 'cur_2', unpaired: [5, 6] });
    expect(html).toContain('Сопоставлено: 1 на этой странице · Возможных: 1 · Только П: 5 · Только Р: 6');
  });

  it('puts the counters and both buttons over the table, the confirmation of all first', () => {
    const html = catalog({ suggestions: 3 });
    const bar = html.indexOf('data-pair-toolbar');
    const counters = html.indexOf('data-pair-counters');
    const confirmAll = html.indexOf('Подтвердить все предложения (3)');
    const launch = html.indexOf('Запустить анализ выбранных (0)');
    const table = html.indexOf('<table');
    expect(bar).toBeGreaterThan(html.indexOf('Пары стадий'));
    expect([bar, counters, confirmAll, launch, table].every((at) => at > -1)).toBe(true);
    expect(counters).toBeLessThan(confirmAll);
    expect(confirmAll).toBeLessThan(launch);
    expect(launch).toBeLessThan(table);
  });

  it('opens nothing of the batch until its button is pressed: no queue panel, no method, no estimate', () => {
    const html = catalog();
    expect(html).not.toContain('Очередь сравнения стадий');
    expect(html).not.toContain('Сравнить выбранные пары');
    // The one pair opens its own panel «Управление парой» under the table, with its own method and estimate: the batch's are not there.
    const overTable = html.slice(html.indexOf('data-pair-toolbar'), html.indexOf('<table'));
    expect(overTable).not.toContain('С описанием изменений ИИ');
    expect(overTable).not.toContain('Метод сравнения');
    expect(html).toMatch(/data-batch-launch=""[^>]*disabled/);
  });

  it('offers «Подтвердить все предложения» only where there is something to confirm', () => {
    expect(catalog({ suggestions: 0 })).not.toContain('Подтвердить все предложения');
    expect(catalog({ suggestions: 0 })).toContain('Возможных: 0');
  });

  it('keeps the counters for a reader and gives them neither button: the decisions are the expert\'s', () => {
    const html = catalog({ expert: false, suggestions: 2 });
    expect(html).toContain('Сопоставлено: 1 · Возможных: 2 · Только П: 3 · Только Р: 2');
    expect(html).not.toContain('Подтвердить все предложения');
    expect(html).not.toContain('Запустить анализ выбранных');
  });

  it('still says that the expert links the documents, and does not link them by itself', () => {
    expect(catalog()).toContain('Документы связывает эксперт.');
  });

  it('does not draw the window of the confirmation until the button asks for it', () => {
    expect(catalog({ suggestions: 2 })).not.toContain('<dialog');
  });
});
