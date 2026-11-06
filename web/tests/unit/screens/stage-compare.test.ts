import { SearchParamsContext } from 'next/dist/shared/lib/hooks-client-context.shared-runtime';
import { createElement } from 'react';
import { describe, expect, it } from 'vitest';

import { StageComparePage } from '@/_pages/stage-compare';
import { STAGE_PAIR_KEYS } from '@/entities/stage-pair';

import { newClient, renderScreen } from './harness';
import { DOCUMENT_UID, PROJECT_UID, uid } from '../version-compare/fixtures';
import { READER, seedComparison } from '../version-compare/seed';

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

/** The screen on a given step: the address is what the screen reads, so the step is a query in the provider. */
function onStep(query: string, expert = true): string {
  const client = newClient();
  seedComparison(client, { modules: 'versions,stages', ...(expert ? {} : { account: READER }) });
  client.setQueryData([...STAGE_PAIR_KEYS.projectPairs(PROJECT_UID), 'workspace'], [PAIR_ROW]);
  client.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID), { items: [PAIR_ROW], page: { next_cursor: null } });
  client.setQueryData(STAGE_PAIR_KEYS.documents(PROJECT_UID), NAMES);
  client.setQueryData(['stage-full-runs', PAIR], [RUN_ROW]);
  client.setQueryData(['stage-full-run', RUN], RUN_ROW);
  client.setQueryData(['stage-run-card-counts', RUN], { total: 9, review: 3, project_changes: 5 });
  return renderScreen(client, createElement(SearchParamsContext.Provider, { value: new URLSearchParams(query) }, createElement(StageComparePage)));
}

function loaded(expert = true): string {
  const client = newClient();
  seedComparison(client, { modules: 'versions,stages', ...(expert ? {} : { account: READER }) });
  client.setQueryData(STAGE_PAIR_KEYS.pairs(PROJECT_UID), {
    items: [{ pair_id: PAIR, project_uid: PROJECT_UID, left_document_uid: DOCUMENT_UID, right_document_uid: RIGHT, completeness: 'unknown', state: 'confirmed', created_at: '2026-10-29T00:00:00Z' }],
    page: { next_cursor: null },
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
  return renderScreen(client, createElement(StageComparePage));
}

describe('stage comparison catalog', () => {
  it('shows confirmed pairs separately from nonbinding suggestions and offers expert acts', () => {
    const html = loaded();
    expect(html).toContain('Пары стадий');
    expect(html).toContain('Наборы PDF и ZIP');
    expect(html).toContain('Загрузить новый набор');
    expect(html).toContain('АР-01.pdf');
    expect(html).toContain('Подтвердить документ');
    expect(html).toContain('Возможные пары');
    expect(html).toContain('Полнота не указана');
    expect(html).toContain('Совпадают раздел и подтверждённый шифр');
    expect(html).toContain('Проверить связь');
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
    expect(html).toContain('Возможные пары');
    expect(html).not.toContain('Проверить связь');
    expect(html).not.toContain('>Неполный</button>');
  });

  it('does not mount the catalog when the stages module is off', () => {
    const client = newClient();
    seedComparison(client, { modules: 'versions' });
    const html = renderScreen(client, createElement(StageComparePage));
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
    for (const header of ['Проект / раздел', 'Метод и модель', 'Дата', 'Изменения', 'Требуют проверки', 'Статус']) expect(html).toContain(header);
    expect(html).toContain('Пояснительная записка · AR');
    expect(html).toContain('Пояснительная записка, редакция 2 · AR');
    expect(html).toContain('Цепочка · с ИИ');
    expect(html).not.toContain('data-stage-pair-select');
    expect(html).not.toContain('Семь шагов сравнения');
  });

  it('puts «Загрузить проекты» at the bar for an expert, and withholds it from a reader', () => {
    const expert = onStep('');
    expect(expert).toContain('data-stage-upload-open');
    expect(expert).toContain('>Загрузить проекты<');
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
