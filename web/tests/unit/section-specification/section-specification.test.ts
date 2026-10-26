/**
 * «Оптимизация разделов» (`W63-SECTION-FORM7-01`): a section's combined Form-7 specification
 * across projects, read-only.
 *
 * Rendered, not read from source (`D-53`): every assertion is on markup a reviewer would see.
 * The subjects are the rules the screen must keep: the section only filters (rows are never
 * merged across projects and there is no section total), a price and an amount appear only on a
 * row that counts in its own project's total (a dash elsewhere, never `0`), a project without a
 * price list shows rows without any figure, every row carries its address, and a bound or a
 * missing run is said in words rather than shown as an empty table.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { SectionSpecification } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import { PROJECT_STRUCTURE_ORDER } from '@/entities/project';
import {
  SECTION_EXCLUSION_LABELS,
  SECTION_LIMIT_MESSAGES,
  SECTION_PRICE_STATE_MESSAGES,
  SECTION_ROW_LIMIT,
  SECTION_SOURCE_STATE_MESSAGES,
  SECTION_UNKNOWN_LABEL,
  sectionSourceStateMessage,
  sectionSpecificationQueryOptions,
  stageMark,
} from '@/entities/section-specification';
import { SectionPicker, SectionSpecificationAnswer, SectionSpecificationSection } from '@/widgets/section-specification';

import { newClient, renderScreen, seedError } from '../screens/harness';
import {
  SECTION_DOCUMENT_B,
  SECTION_NO_ROWS,
  SECTION_PROJECT_A,
  SECTION_PROJECT_B,
  SECTION_VERSION_B,
  sectionAnswer,
  sectionKey,
  sectionPagedAnswer,
} from './fixtures';

function render(answer: SectionSpecification, onSelect: ((uid: string) => void) | null = () => undefined): string {
  return renderToStaticMarkup(
    createElement(SectionSpecificationAnswer, { answer, onPage: () => undefined, onSelectProject: onSelect }),
  );
}

/** One row's markup, by its provenance key. */
function rowMarkup(markup: string, rowId: string): string {
  const start = markup.indexOf(`data-section-row="${rowId}"`);
  expect(start, rowId).toBeGreaterThan(-1);
  return markup.slice(start, markup.indexOf('</tr>', start));
}

function text(markup: string): string {
  return markup.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');
}

function cell(markup: string, rowId: string, attribute: string): string {
  const match = new RegExp(`${attribute}="([^"]*)"[^>]*>(.*?)</td>`).exec(rowMarkup(markup, rowId));
  expect(match, attribute).not.toBeNull();
  // Money is grouped with a no-break space; the test reads it as the eye does.
  return `${match![1] ?? ''}|${(match![2] ?? '').replace(/<[^>]+>/g, '').replace(/\u00a0/g, ' ').trim()}`;
}

const A_COUNTED = `sr-${'a'.repeat(32)}`;
const A_QUANTITY = `sr-${'b'.repeat(32)}`;
const A_AMBIGUOUS = `sr-${'c'.repeat(32)}`;
const A_UNMATCHED = `sr-${'d'.repeat(32)}`;
const B_FIRST = `sr-${'e'.repeat(32)}`;
const B_SECOND = `sr-${'f'.repeat(32)}`;

describe('the money rule on screen, project by project', () => {
  const markup = render(sectionAnswer());

  it('shows a price and an amount only on the row that counts in its own project’s total', () => {
    expect(cell(markup, A_COUNTED, 'data-section-price')).toBe('15000|15 000 руб.');
    expect(cell(markup, A_COUNTED, 'data-section-amount')).toBe('180000|180 000 руб.');
    expect(rowMarkup(markup, A_COUNTED)).toContain('data-section-counted="yes"');
    for (const id of [A_QUANTITY, A_AMBIGUOUS, A_UNMATCHED]) {
      expect(rowMarkup(markup, id)).toContain('data-section-counted="no"');
      expect(cell(markup, id, 'data-section-price')).toBe('none|—');
      expect(cell(markup, id, 'data-section-amount').startsWith('none|—')).toBe(true);
    }
    // A matched position whose quantity is not a number is matched, but not counted.
    expect(cell(markup, A_QUANTITY, 'data-section-amount')).toContain('количество не числом');
  });

  it('shows the rows of a project without a price list with no figure and says so', () => {
    for (const id of [B_FIRST, B_SECOND]) {
      const row = rowMarkup(markup, id);
      expect(row).toContain('data-section-status="price_list_missing"');
      expect(row).toContain('data-section-counted="no"');
      expect(row).toContain('нет прайс-листа проекта');
      expect(cell(markup, id, 'data-section-price')).toBe('none|—');
      expect(cell(markup, id, 'data-section-amount')).toBe('none|—');
    }
    const panel = markup.slice(markup.indexOf(`data-section-project="${SECTION_PROJECT_B}"`));
    expect(panel).toContain(SECTION_PRICE_STATE_MESSAGES.price_list_missing);
    expect(panel).toContain('data-section-price-list="none"');
    expect(panel).toContain('data-section-total="none"');
    expect(panel).not.toContain('data-section-totals=');
  });

  it('never writes an absent amount as zero', () => {
    for (const id of [A_QUANTITY, A_AMBIGUOUS, A_UNMATCHED, B_FIRST, B_SECOND]) {
      expect(text(rowMarkup(markup, id))).not.toMatch(/(^|\s)0(\s|$)/);
    }
  });

  it('keeps each project’s totals to itself, per currency, with no total for the section', () => {
    const first = markup.slice(markup.indexOf(`data-section-totals="${SECTION_PROJECT_A}"`));
    const totals = first.slice(0, first.indexOf('</div>'));
    expect(totals).toContain('data-section-total="EUR"');
    expect(totals).toContain('data-section-total="RUB"');
    expect(text(totals).replace(/\u00a0/g, ' ')).toContain('2 550 евро');
    expect(text(totals).replace(/\u00a0/g, ' ')).toContain('502 006,5 руб.');
    expect(text(totals)).toContain('Итоги в разных валютах не складываются и не пересчитываются.');
    expect(text(totals)).toContain('Не вошли в итог строк: 2');
    expect((markup.match(/data-section-totals=/g) ?? []).length).toBe(1);
    expect(text(markup)).toContain('итога по разделу нет');
    expect(text(markup)).not.toMatch(/итого по разделу/i);
  });
});

describe('rows are addressed and never merged', () => {
  const markup = render(sectionAnswer());

  it('gives every row its project, set, version, sheet and page', () => {
    const first = rowMarkup(markup, A_COUNTED);
    expect(first).toContain(`data-section-row-project="${SECTION_PROJECT_A}"`);
    expect(text(first)).toContain('Школа на пятьсот мест');
    expect(text(first)).toContain('Архитектурные решения');
    expect(text(first)).toContain('версия 2');
    expect(text(first)).toContain('л. 10 / с. 14');
    expect(first).toContain('title="строки 3–3"');
    const other = rowMarkup(markup, B_FIRST);
    expect(other).toContain(`data-section-row-project="${SECTION_PROJECT_B}"`);
    expect(text(other)).toContain('Детский сад');
    expect(text(other)).toContain('версия 1');
    expect(text(other)).toContain('с. 9');
    expect(other).toContain(`/projects/${SECTION_PROJECT_B}/documents/${SECTION_DOCUMENT_B}`);
    expect(SECTION_VERSION_B).toMatch(/^ver_/);
  });

  it('shows the same product of two projects as two rows, each under its own project', () => {
    const name = 'Металлический щит МЩ-1';
    expect((text(markup).match(new RegExp(name, 'g')) ?? []).length).toBe(2);
    expect(rowMarkup(markup, A_COUNTED)).toContain('Школа на пятьсот мест');
    expect(rowMarkup(markup, B_FIRST)).toContain('Детский сад');
  });

  it('keeps the nine columns of the form, with type, code and maker said to be inside the name', () => {
    for (const heading of [
      'Проект', 'Комплект', 'Лист / стр.', 'Поз.', 'Наименование и техническая характеристика', 'Ед. изм.',
      'Кол.', 'Масса ед.', 'Примечание', 'Сопоставление', 'Позиция прайс-листа проекта', 'Цена', 'Сумма',
    ]) {
      expect(markup).toContain(`>${heading}</th>`);
    }
    expect(text(markup)).toContain('графы «Тип, марка», «Код» и «Завод-изготовитель» не отделены от наименования');
    expect(text(rowMarkup(markup, A_COUNTED))).toContain('Изделия: Металлический щит МЩ-1');
    expect(text(rowMarkup(markup, A_COUNTED))).toContain('45,5');
    expect(text(rowMarkup(markup, A_COUNTED))).toContain('по месту');
  });

  it('pages the rows and says which ones it shows, only when there is more than a page', () => {
    expect(markup).not.toContain('data-section-pager');
    const paged = render(sectionPagedAnswer());
    expect(paged).toContain('data-section-pager');
    expect(text(paged)).toContain(`Строки ${SECTION_ROW_LIMIT + 1}–${SECTION_ROW_LIMIT + 6} из 120`);
    expect(text(paged)).toContain('Предыдущие');
    expect(text(paged)).toContain('Следующие');
    const last = render({ ...sectionPagedAnswer(), rows: { ...sectionPagedAnswer().rows!, next_offset: null } });
    expect(last).toMatch(/Следующие<\/button>/);
    expect(last).toMatch(/<button[^>]*disabled=""[^>]*>Следующие/);
  });
});

describe('what is said instead of a table', () => {
  it('names each source’s state, with what to do', () => {
    const markup = render(sectionAnswer());
    for (const state of ['ready', 'analysis_missing', 'text_unavailable', 'specification_too_large'] as const) {
      expect(markup).toContain(`data-section-source-state="${state}"`);
      expect(text(markup)).toContain(SECTION_SOURCE_STATE_MESSAGES[state]);
    }
    expect(text(markup)).toContain('таблиц: 1, строк: 4');
    expect(text(markup)).toContain('не прочитано строк таблиц: 1');
  });

  it('lists the current versions nobody classified, outside the summary, and counts them completely', () => {
    const markup = render(sectionAnswer());
    expect(markup).toContain('data-section-excluded-versions="3"');
    expect(text(markup)).toContain('Текущие версии без подтверждённого раздела: 3. В сводку они не входят.');
    expect(text(markup)).toContain(SECTION_EXCLUSION_LABELS.version_unclassified);
    expect(text(markup)).toContain('Показаны первые 1; счёт полный.');
    expect(render(sectionAnswer({ excluded: [], excluded_count: 0 }))).not.toContain('data-section-excluded-versions');
  });

  for (const reason of ['projects', 'sources', 'rows'] as const) {
    it(`says why a ${reason} bound stops the read, and shows no rows or totals`, () => {
      const answer = sectionAnswer({
        ...SECTION_NO_ROWS, state: 'section_too_large', limit_reason: reason,
        projects: reason === 'projects' ? [] : sectionAnswer().projects.map((item) => ({
          ...item, price_state: 'not_read' as const, price_list: null, matching: null, row_count: 0,
          sources: item.sources.map((source) => ({ ...source, state: 'not_read' as const, run_id: null,
            text_layer_sha256: null, row_count: null, table_count: null, skipped_by_reason: null })),
        })),
      });
      const markup = render(answer);
      expect(markup).toContain(`data-section-limit="${reason}"`);
      expect(text(markup)).toContain(SECTION_LIMIT_MESSAGES[reason]);
      expect(markup).not.toContain('<table');
      expect(markup).not.toContain('data-section-totals=');
      if (reason !== 'projects') {
        expect(text(markup)).toContain(SECTION_SOURCE_STATE_MESSAGES.not_read);
        expect(text(markup)).toContain(SECTION_PRICE_STATE_MESSAGES.not_read);
        expect(markup).toContain('Показать только этот проект');
      }
    });
  }

  it('says a section with no confirmed set is empty, and a project with none the same', () => {
    const none = { projects: [], excluded: [], excluded_count: 0, source_count: 0, row_count: 0 };
    expect(text(render(sectionAnswer(none)))).toContain('В разделе нет подтверждённых комплектов');
    const narrowed = render(sectionAnswer({ ...none, project_filter: SECTION_PROJECT_A as never }));
    expect(text(narrowed)).toContain('У выбранного проекта нет комплектов, текущая версия которых подтверждена для этого раздела.');
  });

  it('says a search that finds nothing found nothing, without touching the projects’ totals', () => {
    const markup = render(sectionAnswer({
      query: 'ёлочка', rows: { offset: 0, limit: SECTION_ROW_LIMIT, total: 0, next_offset: null, items: [] },
    }));
    expect(text(markup)).toContain('По запросу строк не найдено');
    expect(markup).toContain('data-section-totals=');
    expect(markup).not.toContain('<table');
  });

  it('offers to narrow to one project only while the section is not narrowed', () => {
    expect((render(sectionAnswer()).match(/Показать только этот проект/g) ?? []).length).toBe(2);
    expect(render(sectionAnswer(), null)).not.toContain('Показать только этот проект');
    const narrowed = render(sectionAnswer({ project_filter: SECTION_PROJECT_A as never }));
    expect(narrowed).not.toContain('Показать только этот проект');
  });

  it('reports a value outside the sets this build knows instead of guessing', () => {
    expect(sectionSourceStateMessage('half_read')).toBe(SECTION_UNKNOWN_LABEL);
    expect(stageMark('X')).toBe(SECTION_UNKNOWN_LABEL);
    expect(stageMark('P')).toBe('П');
    expect(stageMark('R')).toBe('Р');
    const answer = sectionAnswer();
    const odd = { ...answer, projects: answer.projects.map((project, index) => (index === 0
      ? { ...project, sources: project.sources.map((source) => ({ ...source, state: 'half_read' as never })) }
      : project)) };
    expect(text(render(odd))).toContain(SECTION_UNKNOWN_LABEL);
  });
});

describe('the section picker and the container', () => {
  it('lists the fifteen sections in the owner’s order, АР first', () => {
    const markup = renderToStaticMarkup(createElement(SectionPicker, { selected: 'AR', onSelect: () => undefined }));
    const values = [...markup.matchAll(/<option value="([^"]+)"/g)].map((match) => match[1]);
    expect(values).toEqual([...PROJECT_STRUCTURE_ORDER]);
    expect(values).toHaveLength(15);
    expect(markup).toContain('Архитектурные решения (АР)');
    expect(markup).toContain('data-section-picker="15"');
  });

  it('opens on АР, unfiltered, and waits on its read', () => {
    const client = newClient();
    const markup = renderScreen(client, createElement(SectionSpecificationSection));
    expect(markup).toContain('data-section-specification');
    expect(markup).toContain('Все проекты раздела');
    expect(markup).toContain('selected=""');
    expect(client.getQueryCache().getAll().map((query) => query.queryKey)).toEqual([sectionKey()]);
  });

  it('says a refused read is refused and offers to try again', () => {
    const client = newClient();
    const correlation = '0f0e9d8c-7b6a-4948-b726-150413021100';
    seedError(client, sectionKey(), new ApiError(503, {
      contract_version: '1.7.0', error_code: 'dependency_unavailable',
      message: 'Сообщение об отказе.', correlation_id: correlation, retryable: false,
    }, correlation));
    const markup = renderScreen(client, createElement(SectionSpecificationSection));
    expect(markup).toContain('data-section-failure=');
    expect(text(markup)).toContain('Сводная спецификация раздела не прочитана');
  });

  it('keys one page under the section, project filter and search', () => {
    expect(sectionSpecificationQueryOptions({ sectionCode: 'AR', projectUid: null, query: '  ', offset: 0 }).queryKey).toEqual(
      ['optimisation', 'section-specification', 'AR', { projectUid: null, q: null, offset: 0, limit: SECTION_ROW_LIMIT }],
    );
    expect(sectionSpecificationQueryOptions({ sectionCode: 'KJ', projectUid: SECTION_PROJECT_A as never, query: ' щит ', offset: 50 }).queryKey).toEqual(
      ['optimisation', 'section-specification', 'KJ', { projectUid: SECTION_PROJECT_A, q: 'щит', offset: 50, limit: SECTION_ROW_LIMIT }],
    );
    expect(queryKeys.optimisation.sectionSpecification('AR')).toEqual(
      ['optimisation', 'section-specification', 'AR', { projectUid: null, q: null, offset: 0, limit: null }],
    );
  });
});
