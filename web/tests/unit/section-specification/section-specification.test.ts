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
import { SectionFilterBar } from '@/_pages/section-optimisation';
import type { SectionSpecificationColumns } from '@/widgets/section-specification';
import { SectionSpecificationAnswer, SectionSpecificationSection, groupRowsByDocument } from '@/widgets/section-specification';

import { newClient, renderScreen, seedError } from '../screens/harness';
import {
  SECTION_DOCUMENT_A,
  SECTION_DOCUMENT_B,
  SECTION_DOCUMENT_UNREAD_1,
  SECTION_DOCUMENT_UNREAD_2,
  SECTION_DOCUMENT_UNREAD_3,
  SECTION_NO_ROWS,
  SECTION_PROJECT_A,
  SECTION_PROJECT_B,
  SECTION_VERSION_B,
  sectionAnswer,
  sectionKey,
  sectionPagedAnswer,
} from './fixtures';

/** The answer as the reader sees it with «Показать сопоставление с прайс-листом» on, the table these rules were written for. */
function render(
  answer: SectionSpecification,
  onSelect: ((uid: string) => void) | null = () => undefined,
  columns: SectionSpecificationColumns = 'priced',
): string {
  return renderToStaticMarkup(
    createElement(SectionSpecificationAnswer, { answer, onPage: () => undefined, onSelectProject: onSelect, columns }),
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
      expect(row).toContain('нет прайс-листа объекта');
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
    // The document is the row's group (`UIP-S11-02`): its title is on the group's row, above the rows it holds, and with every
    // object in view the group names the object too.
    expect(text(first)).toContain('Архитектурные решения');
    expect(markup.indexOf('data-section-group-row="' + SECTION_DOCUMENT_A + '"')).toBeLessThan(markup.indexOf('data-section-row="' + A_COUNTED + '"'));
    expect(text(markup.slice(markup.indexOf('data-section-group-row="' + SECTION_DOCUMENT_A + '"')))).toContain('Школа на пятьсот мест');
    expect(text(first)).toContain('версия 2');
    expect(text(first)).toContain('л. 10 / с. 14');
    expect(first).toContain('title="строки 3–3"');
    const other = rowMarkup(markup, B_FIRST);
    expect(other).toContain(`data-section-row-project="${SECTION_PROJECT_B}"`);
    expect(text(other)).toContain('версия 1');
    expect(text(other)).toContain('с. 9');
    expect(other).toContain(`/projects/${SECTION_PROJECT_B}/documents/${SECTION_DOCUMENT_B}`);
    expect(SECTION_VERSION_B).toMatch(/^ver_/);
  });

  it('links each row’s set, each source and each project to their «Оптимизация» tab (`UI-B-30`)', () => {
    // `&` and `?` are plain in the address; the document's tab is `?tab=optimisation` and a row names no pass.
    expect(rowMarkup(markup, B_FIRST)).toContain(
      `href="/projects/${SECTION_PROJECT_B}/documents/${SECTION_DOCUMENT_B}?tab=optimisation"`,
    );
    expect(rowMarkup(markup, B_FIRST)).toContain(`href="/projects/${SECTION_PROJECT_B}/documents/${SECTION_DOCUMENT_B}"`);
    expect(rowMarkup(markup, A_COUNTED)).toContain(
      `href="/projects/${SECTION_PROJECT_A}/documents/${SECTION_DOCUMENT_A}?tab=optimisation"`,
    );
    const panel = markup.slice(markup.indexOf(`data-section-project="${SECTION_PROJECT_B}"`));
    expect(panel).toContain(`href="/projects/${SECTION_PROJECT_B}?tab=optimisation"`);
    expect(panel).toContain('вкладка «Оптимизация» объекта');
    expect(panel).toContain('оптимизация комплекта');
    // The project and the set keep their own links: the new ones are added, not substituted.
    expect(panel).toContain(`href="/projects/${SECTION_PROJECT_B}"`);
  });

  it('shows the same product of two projects as two rows, each under its own document', () => {
    const name = 'Металлический щит МЩ-1';
    expect((text(markup).match(new RegExp(name, 'g')) ?? []).length).toBe(2);
    const groupA = markup.indexOf(`data-section-group-row="${SECTION_DOCUMENT_A}"`);
    const groupB = markup.indexOf(`data-section-group-row="${SECTION_DOCUMENT_B}"`);
    expect(groupA).toBeGreaterThan(-1);
    expect(groupB).toBeGreaterThan(groupA);
    // Each row sits between its own document's group row and the next group's.
    expect(markup.indexOf(`data-section-row="${A_COUNTED}"`)).toBeGreaterThan(groupA);
    expect(markup.indexOf(`data-section-row="${A_COUNTED}"`)).toBeLessThan(groupB);
    expect(markup.indexOf(`data-section-row="${B_FIRST}"`)).toBeGreaterThan(groupB);
  });

  it('keeps the nine columns of the form, with type, code and maker said to be inside the name', () => {
    for (const heading of [
      'Позиция', 'Наименование и техническая характеристика', 'Тип, марка, обозначение документа, опросного листа',
      'Код оборудования, изделия, материала', 'Завод-изготовитель', 'Единица измерения', 'Количество', 'Масса единицы, кг',
      'Примечание', 'Сопоставление', 'Позиция прайс-листа объекта', 'Цена', 'Сумма',
    ]) {
      // The first graph's heading shares its cell with the «+» and «−» of the project folds.
      expect(markup).toContain(heading === 'Позиция' ? `<span>${heading}</span>` : `${heading}</th>`);
    }
    expect(text(markup)).toContain('графы «Тип, марка», «Код» и «Завод-изготовитель» не отделены от наименования');
    // The row's category is the form's own divider row; the name is the name.
    expect(markup).toContain('data-section-category="Изделия"');
    expect(text(rowMarkup(markup, A_COUNTED))).toContain('Металлический щит МЩ-1');
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

  it('lists the current versions nobody classified in the one disclosure at the foot, and counts them completely', () => {
    const markup = render(sectionAnswer());
    expect(markup).toContain('data-section-excluded-versions="3"');
    expect(text(markup)).toContain('Текущие версии без подтверждённого раздела: 3. В сводку они не входят.');
    expect(text(markup)).toContain(SECTION_EXCLUSION_LABELS.version_unclassified);
    expect(text(markup)).toContain('Показаны первые 1; счёт полный.');
    expect(render(sectionAnswer({ excluded: [], excluded_count: 0 }))).not.toContain('data-section-excluded-versions');
  });

  it('«Неполные источники: N» is one disclosure at the bottom: the documents not read yet and the versions nobody classified', () => {
    const markup = render(sectionAnswer());
    // Three documents of the first project are not `ready`, and three current versions are unclassified.
    expect((markup.match(/data-section-incomplete=/g) ?? []).length).toBe(1);
    expect(markup).toContain('data-section-incomplete="6"');
    expect(text(markup)).toContain('Неполные источники: 6');
    expect(markup).toContain('data-section-unread-sources="3"');
    const incomplete = markup.slice(markup.indexOf('data-section-incomplete='));
    for (const state of ['analysis_missing', 'text_unavailable', 'specification_too_large'] as const) {
      expect(incomplete).toContain(`data-section-incomplete-state="${state}"`);
      expect(text(incomplete)).toContain(SECTION_SOURCE_STATE_MESSAGES[state]);
    }
    expect(text(incomplete)).toContain('Школа на пятьсот мест / Архитектурные решения, паркинг — версия 1');
    // It is the foot of the answer: after the table and after the summary, and the old block over the table is gone.
    expect(markup.indexOf('data-section-incomplete=')).toBeGreaterThan(markup.indexOf('<table'));
    expect(markup.indexOf('data-section-incomplete=')).toBeGreaterThan(markup.indexOf('data-section-summary-panel'));
    expect(text(markup)).not.toContain('Текущие версии без подтверждённого раздела: 3. В сводку они не входят. Школа');
    // The figure counts both kinds, and nothing is drawn when there is nothing to say.
    const ready = sectionAnswer({
      excluded: [], excluded_count: 0,
      projects: sectionAnswer().projects.map((project) => ({ ...project, sources: project.sources.filter((source) => source.state === 'ready') })),
    });
    expect(render(ready)).not.toContain('data-section-incomplete');
    expect(text(render(sectionAnswer({ ...ready, excluded: sectionAnswer().excluded, excluded_count: 3 })))).toContain('Неполные источники: 3');
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
        expect(markup).toContain('Показать только этот объект');
      }
    });
  }

  it('says a section with no confirmed set is empty, and a project with none the same', () => {
    const none = { projects: [], excluded: [], excluded_count: 0, source_count: 0, row_count: 0 };
    expect(text(render(sectionAnswer(none)))).toContain('В разделе нет подтверждённых комплектов');
    const narrowed = render(sectionAnswer({ ...none, project_filter: SECTION_PROJECT_A as never }));
    expect(text(narrowed)).toContain('У выбранного объекта нет комплектов, текущая версия которых подтверждена для этого раздела.');
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
    expect((render(sectionAnswer()).match(/Показать только этот объект/g) ?? []).length).toBe(2);
    expect(render(sectionAnswer(), null)).not.toContain('Показать только этот объект');
    const narrowed = render(sectionAnswer({ project_filter: SECTION_PROJECT_A as never }));
    expect(narrowed).not.toContain('Показать только этот объект');
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

describe('what stands where in the tab (`UIP-S11-03`)', () => {
  const markup = render(sectionAnswer());

  it('puts the summary by object under «Источники и итоги», closed, after the table', () => {
    expect((markup.match(/data-section-summary-panel/g) ?? []).length).toBe(1);
    const panel = markup.slice(markup.indexOf('data-section-summary-panel'));
    expect(panel.slice(0, 120)).toContain('<summary>Источники и итоги</summary>');
    expect(markup).not.toMatch(/<details[^>]*open=""[^>]*data-section-summary-panel/);
    expect(markup.indexOf('<table')).toBeLessThan(markup.indexOf('data-section-summary-panel'));
    // The documents with their state, the price list and the totals per currency are all under it.
    const inside = panel.slice(0, panel.indexOf('</details>'));
    for (const part of ['data-section-summary=', 'data-section-sources=', 'data-section-price-list=', 'data-section-totals=', 'data-section-project=']) {
      expect(inside).toContain(part);
    }
    // and none of them is above it
    const above = markup.slice(0, markup.indexOf('data-section-summary-panel'));
    for (const part of ['data-section-sources=', 'data-section-price-list=', 'data-section-totals=', 'data-section-project=']) {
      expect(above).not.toContain(part);
    }
  });

  it('keeps it open only where a bound stopped the read, because the way out — one object — is in it', () => {
    const answer = sectionAnswer();
    const stopped = sectionAnswer({
      ...SECTION_NO_ROWS, state: 'section_too_large', limit_reason: 'sources',
      projects: answer.projects.map((item) => ({
        ...item, price_state: 'not_read' as const, price_list: null, matching: null, row_count: 0,
        sources: item.sources.map((source) => ({ ...source, state: 'not_read' as const, run_id: null,
          text_layer_sha256: null, row_count: null, table_count: null, skipped_by_reason: null })),
      })),
    });
    expect(render(stopped)).toMatch(/<details[^>]*open=""[^>]*data-section-summary-panel/);
    expect(render(stopped)).toContain('Показать только этот объект');
  });

  it('says nothing of a summary where the section has no document, and never draws an empty disclosure', () => {
    const none = { projects: [], excluded: [], excluded_count: 0, source_count: 0, row_count: 0 };
    expect(render(sectionAnswer(none))).not.toContain('data-section-summary-panel');
    expect(render(sectionAnswer(none))).not.toContain('data-section-incomplete');
  });
});

describe('narrowed to one document (`UIP-S11-06`): the empty states name the document, not the project', () => {
  const none = { projects: [], excluded: [], excluded_count: 0, source_count: 0, row_count: 0 };
  const filtered = (answer: SectionSpecification): string =>
    renderToStaticMarkup(createElement(SectionSpecificationAnswer, { answer, onPage: () => undefined, onSelectProject: null, documentFiltered: true }));

  it('says a document with no confirmed current version has no rows here, and not that the section has no sets', () => {
    const said = text(filtered(sectionAnswer(none)));
    expect(said).toContain('У выбранного документа нет подтверждённой версии в этом разделе');
    expect(said).not.toContain('В разделе нет подтверждённых комплектов');
    expect(said).not.toContain('выбранного объекта');
    // Not narrowed to a document, the old sentences stand.
    expect(text(render(sectionAnswer(none)))).toContain('В разделе нет подтверждённых комплектов');
    expect(text(render(sectionAnswer({ ...none, project_filter: SECTION_PROJECT_A as never })))).toContain('У выбранного объекта нет комплектов');
  });

  it('says a document with no rows has none, and a search that finds none found none', () => {
    const answer = sectionAnswer();
    const empty = { offset: 0, limit: SECTION_ROW_LIMIT, total: 0, next_offset: null, items: [] };
    expect(text(filtered(sectionAnswer({ rows: empty, row_count: 0 })))).toContain('Строк спецификации в документе нет');
    expect(text(render(sectionAnswer({ rows: empty, row_count: 0 })))).toContain('Строк спецификации в разделе нет');
    expect(text(filtered(sectionAnswer({ query: 'ёлочка', rows: empty })))).toContain('По запросу строк не найдено');
    expect(answer.rows).not.toBeNull();
  });

  it('reads the document with the section and the project, and starts again from the first page for another', () => {
    const client = newClient();
    const markup = renderScreen(client, createElement(SectionSpecificationSection, { documentUid: SECTION_DOCUMENT_B as never }));
    expect(markup).toContain('data-section-specification');
    expect(client.getQueryCache().getAll().map((query) => query.queryKey)).toEqual([sectionKey({ documentUid: SECTION_DOCUMENT_B })]);
    expect(sectionSpecificationQueryOptions({ sectionCode: 'AR', projectUid: null, documentUid: SECTION_DOCUMENT_B as never, query: '', offset: 0 }).queryKey).toEqual([
      'optimisation', 'section-specification', 'AR', { projectUid: null, documentUid: SECTION_DOCUMENT_B, q: null, offset: 0, limit: SECTION_ROW_LIMIT },
    ]);
  });
});

describe('the section picker and the container', () => {
  it('lists the fifteen sections in the owner’s order, АР first, in the header of the page (`UIP-S11-01`)', () => {
    const markup = renderToStaticMarkup(
      createElement(SectionFilterBar, { sectionCode: 'AR', onSection: () => undefined }),
    );
    const values = [...markup.matchAll(/<option value="([^"]+)"/g)].map((match) => match[1]).filter((value) => value !== '');
    expect(values).toEqual([...PROJECT_STRUCTURE_ORDER]);
    expect(values).toHaveLength(15);
    expect(markup).toContain('Архитектурные решения (АР)');
    expect(markup).toContain('data-section-picker="15"');
    // The object is the top strip's: there is no list of projects beside the sections.
    expect(markup).not.toContain('Все объекты раздела');
    expect(markup).not.toContain('data-section-project-filter');
    expect((markup.match(/<select/g) ?? []).length).toBe(1);
  });

  it('opens on АР, unfiltered, and waits on its read', () => {
    const client = newClient();
    const markup = renderScreen(client, createElement(SectionSpecificationSection));
    expect(markup).toContain('data-section-specification');
    expect(markup).toContain('Показать сопоставление с прайс-листом');
    expect(client.getQueryCache().getAll().map((query) => query.queryKey)).toEqual([sectionKey()]);
  });

  it('has the search, «Найти», «Сбросить поиск» and the price match in ONE row over the table, and no long paragraph above it', () => {
    const markup = renderScreen(newClient(), createElement(SectionSpecificationSection));
    const forms = markup.match(/<form[\s\S]*?<\/form>/g) ?? [];
    expect(forms).toHaveLength(1);
    const row = forms[0]!;
    expect(row).toContain('aria-label="Отбор строк раздела"');
    expect(text(row)).toContain('Поиск по строкам');
    expect(row).toContain('id="section-specification-query"');
    expect(row).toMatch(/<button[^>]*type="submit"[^>]*>Найти<\/button>/);
    expect(row).toMatch(/<button[^>]*>Сбросить поиск<\/button>/);
    expect(row).toContain('data-section-columns-toggle');
    expect(text(row)).toContain('Показать сопоставление с прайс-листом');
    // The paragraph that explained the rules is not on the tab: what it said stands where it is true.
    expect(text(markup)).not.toContain('Строки спецификации (форма 7) текущих версий комплектов');
    expect(text(markup)).not.toContain('сопоставляется с прайс-листом своего объекта');
  });

  it('answers a search with the same row over the table: the row is above the answer', () => {
    const client = newClient();
    client.setQueryData(sectionKey(), sectionAnswer());
    const markup = renderScreen(client, createElement(SectionSpecificationSection));
    expect(markup.indexOf('aria-label="Отбор строк раздела"')).toBeLessThan(markup.indexOf('<table'));
    expect((markup.match(/<form/g) ?? []).length).toBe(1);
  });

  it('says a refused read is refused and offers to try again', () => {
    const client = newClient();
    const correlation = '0f0e9d8c-7b6a-4948-b726-150413021100';
    seedError(client, sectionKey(), new ApiError(503, {
      contract_version: '1.60.0', error_code: 'dependency_unavailable',
      message: 'Сообщение об отказе.', correlation_id: correlation, retryable: false,
    }, correlation));
    const markup = renderScreen(client, createElement(SectionSpecificationSection));
    expect(markup).toContain('data-section-failure=');
    expect(text(markup)).toContain('Сводная спецификация раздела не прочитана');
  });

  it('keys one page under the section, project filter and search', () => {
    expect(sectionSpecificationQueryOptions({ sectionCode: 'AR', projectUid: null, query: '  ', offset: 0 }).queryKey).toEqual(
      ['optimisation', 'section-specification', 'AR', { projectUid: null, documentUid: null, q: null, offset: 0, limit: SECTION_ROW_LIMIT }],
    );
    expect(sectionSpecificationQueryOptions({ sectionCode: 'KJ', projectUid: SECTION_PROJECT_A as never, query: ' щит ', offset: 50 }).queryKey).toEqual(
      ['optimisation', 'section-specification', 'KJ', { projectUid: SECTION_PROJECT_A, documentUid: null, q: 'щит', offset: 50, limit: SECTION_ROW_LIMIT }],
    );
    expect(queryKeys.optimisation.sectionSpecification('AR')).toEqual(
      ['optimisation', 'section-specification', 'AR', { projectUid: null, documentUid: null, q: null, offset: 0, limit: null }],
    );
  });
});

describe('the original’s Form 7: nine graphs, the rows grouped under a document that folds (`UI-B-23`, `UIP-S11-02`)', () => {
  const markup = render(sectionAnswer(), () => undefined, 'form7');
  const header = (html: string, documentUid: string): string => {
    const from = html.indexOf(`data-section-group-row="${documentUid}"`);
    expect(from, documentUid).toBeGreaterThan(-1);
    return html.slice(from, html.indexOf('</tr>', from));
  };

  it('shows the nine graphs and their numbers, and none of the price columns, by default', () => {
    expect(markup).toContain('data-section-columns="form7"');
    const head = markup.slice(markup.indexOf('<thead>'), markup.indexOf('</thead>'));
    expect((head.match(/scope="col"/g) ?? []).length).toBe(9);
    for (const number of [1, 2, 3, 4, 5, 6, 7, 8, 9]) expect(head).toContain(`>${number}</th>`);
    for (const heading of ['Сопоставление', 'Позиция прайс-листа объекта', 'Цена', 'Сумма']) {
      expect(head).not.toContain(`>${heading}</th>`);
    }
    expect(rowMarkup(markup, A_COUNTED)).not.toContain('data-section-price');
    expect(rowMarkup(markup, A_COUNTED)).not.toContain('data-section-amount');
    // The default of the component is the form; the price columns are asked for.
    expect(renderToStaticMarkup(createElement(SectionSpecificationAnswer, { answer: sectionAnswer(), onPage: null, onSelectProject: null }))).toContain(
      'data-section-columns="form7"',
    );
  });

  it('adds the four price columns, and only them, when asked', () => {
    const priced = render(sectionAnswer());
    const head = priced.slice(priced.indexOf('<thead>'), priced.indexOf('</thead>'));
    expect((head.match(/scope="col"/g) ?? []).length).toBe(13);
    expect(priced).toContain('data-section-columns="priced"');
  });

  it('groups the rows by `document_uid`: one row-group for each document of the answer, in its order, folded open', () => {
    const groups = groupRowsByDocument(sectionAnswer());
    expect(groups.map((group) => [group.documentUid, group.rows.length])).toEqual([
      [SECTION_DOCUMENT_A, 4],
      [SECTION_DOCUMENT_UNREAD_1, 0],
      [SECTION_DOCUMENT_UNREAD_2, 0],
      [SECTION_DOCUMENT_UNREAD_3, 0],
      [SECTION_DOCUMENT_B, 2],
    ]);
    expect((markup.match(/data-section-group-row=/g) ?? []).length).toBe(5);
    expect(markup).toContain('data-section-group-collapsed="no"');
    expect(markup).not.toContain('data-section-group-collapsed="yes"');
    expect(header(markup, SECTION_DOCUMENT_A)).toContain('aria-expanded="true"');
  });

  it('says «Название · v2 · 4 строки» on the group, the way the original says «⌄ МК7-РД-ЭОМ1 · v2 · 10 строк»', () => {
    expect(text(header(markup, SECTION_DOCUMENT_A))).toContain('⌄ Архитектурные решения · v2 · 4 строки');
    expect(text(header(markup, SECTION_DOCUMENT_B))).toContain('⌄ Архитектурные решения · v1 · 2 строки');
    // The number is the server's count of the document's rows, not a count of what the page holds.
    const counted = sectionAnswer();
    const more = sectionAnswer({
      projects: counted.projects.map((project, index) => (index === 0
        ? { ...project, sources: project.sources.map((source, at) => (at === 0 ? { ...source, row_count: 10 } : source)) }
        : project)),
    });
    expect(text(header(render(more, () => undefined, 'form7'), SECTION_DOCUMENT_A))).toContain('Архитектурные решения · v2 · 10 строк');
  });

  it('keys a group by the document\u2019s identity, never by its title: two documents of one title are two groups', () => {
    const answer = sectionAnswer();
    const html = render(answer, () => undefined, 'form7');
    // The two groups with rows carry the same title «Архитектурные решения» and are two row-groups.
    const titles = [SECTION_DOCUMENT_A, SECTION_DOCUMENT_B].map((uid) => text(header(html, uid)));
    expect(titles[0]).toContain('Архитектурные решения');
    expect(titles[1]).toContain('Архитектурные решения');
    expect(new Set(groupRowsByDocument(answer).map((group) => group.documentUid)).size).toBe(5);
    // And a row is under the group of its own `document_uid`, whatever its project says.
    const rows = answer.rows!.items.map((row) => (row.row_id === B_FIRST ? { ...row, document_uid: SECTION_DOCUMENT_A as never } : row));
    const moved = groupRowsByDocument(sectionAnswer({ rows: { ...answer.rows!, items: rows } }));
    expect(moved.find((group) => group.documentUid === SECTION_DOCUMENT_A)?.rows).toHaveLength(5);
    expect(moved.find((group) => group.documentUid === SECTION_DOCUMENT_B)?.rows).toHaveLength(1);
  });

  it('says a document with no table has none, in red, and keeps its group, with what is missing', () => {
    expect((markup.match(/data-section-group-empty="missing"/g) ?? []).length).toBe(3);
    expect(text(markup)).toContain('Спецификация отсутствует');
    expect(text(markup)).toContain(`Спецификация отсутствует — ${SECTION_SOURCE_STATE_MESSAGES.analysis_missing}`);
    // The name is the red one (`missing`), the document that has rows is not.
    expect(header(markup, SECTION_DOCUMENT_UNREAD_1)).toMatch(/class="[^"]*missing[^"]*"[^>]*>Архитектурные решения, паркинг</);
    expect(header(markup, SECTION_DOCUMENT_A)).not.toMatch(/class="[^"]*missing[^"]*"/);
    // Not a number of rows it has not got.
    expect(text(header(markup, SECTION_DOCUMENT_UNREAD_1))).not.toMatch(/ 0 строк/);
    expect(text(header(markup, SECTION_DOCUMENT_UNREAD_1))).toContain('v1');
    // A document the server read and found no rows in has none too, and says nothing of a state.
    const answer = sectionAnswer();
    const bare = sectionAnswer({
      projects: answer.projects.map((project, index) => (index === 1
        ? { ...project, row_count: 0, sources: project.sources.map((source) => ({ ...source, row_count: 0 })) }
        : project)),
      rows: { ...answer.rows!, items: answer.rows!.items.slice(0, 4), total: 4 },
    });
    const html = render(bare, () => undefined, 'form7');
    const group = html.slice(html.indexOf(`data-section-group-row="${SECTION_DOCUMENT_B}"`));
    expect(group.slice(0, group.indexOf('</tbody>'))).toContain('data-section-group-empty="missing"');
    expect(text(group.slice(0, group.indexOf('</tbody>')))).not.toContain('Спецификация отсутствует —');
  });

  it('names the object in the group while every object is in view, and not once the screen is narrowed to one', () => {
    expect(header(markup, SECTION_DOCUMENT_A)).toContain('data-section-group-object');
    expect(text(header(markup, SECTION_DOCUMENT_A))).toContain('Школа на пятьсот мест');
    expect(text(header(markup, SECTION_DOCUMENT_B))).toContain('Детский сад');
    expect(header(markup, SECTION_DOCUMENT_B)).toContain(`href="/projects/${SECTION_PROJECT_B}"`);
    const answer = sectionAnswer();
    const narrowed = render(
      sectionAnswer({
        project_filter: SECTION_PROJECT_B as never,
        projects: answer.projects.slice(1),
        rows: { ...answer.rows!, items: answer.rows!.items.slice(4), total: 2 },
      }),
      null,
      'form7',
    );
    expect(narrowed).not.toContain('data-section-group-object');
    expect(text(header(narrowed, SECTION_DOCUMENT_B))).not.toContain('Детский сад');
  });

  it('names a group the page boundary tore, with how many of its rows are on this page', () => {
    const answer = sectionAnswer();
    // The document says it has 4 rows; the page holds 2 of them and the other 2 are on the next page.
    const torn = sectionAnswer({ rows: { ...answer.rows!, items: [...answer.rows!.items.slice(0, 2), ...answer.rows!.items.slice(4)], total: 6, next_offset: 2 } });
    const html = render(torn, () => undefined, 'form7');
    expect(text(header(html, SECTION_DOCUMENT_A))).toContain('Архитектурные решения · v2 · 4 строки, на этой странице: 2');
    // A group the page holds whole is not torn, and a search narrows the rows and does not tear a group.
    expect(text(header(markup, SECTION_DOCUMENT_A))).not.toContain('на этой странице');
    expect(text(header(render(sectionAnswer({ query: 'щит', rows: { ...answer.rows!, items: answer.rows!.items.slice(0, 2), total: 2 } }), () => undefined, 'form7'), SECTION_DOCUMENT_A)))
      .not.toContain('на этой странице');
  });

  it('says a document whose rows are on another page has rows, and a search that spared none of them found none', () => {
    const answer = sectionAnswer();
    const otherPage = sectionAnswer({ rows: { ...answer.rows!, items: answer.rows!.items.slice(0, 4), total: 6 } });
    expect(render(otherPage, () => undefined, 'form7')).toContain('data-section-group-empty="page"');
    expect(text(render(otherPage, () => undefined, 'form7'))).toContain('Строки этого документа — на другой странице списка.');
    const searched = sectionAnswer({ query: 'щит', rows: { ...answer.rows!, items: answer.rows!.items.slice(0, 4), total: 4 } });
    expect(text(render(searched, () => undefined, 'form7'))).toContain('По текущему поиску строки спецификации этого документа на этой странице не найдены.');
  });

  it('has the original’s «+» and «−» for every group in the heading of the first graph', () => {
    expect(markup).toContain('data-section-expand-all=""');
    expect(markup).toContain('data-section-collapse-all=""');
    expect(markup).toContain('aria-label="Развернуть все документы"');
    expect(markup).toContain('aria-label="Свернуть все документы"');
    expect(markup).not.toContain('все объекты"');
  });

  it('keeps every row’s address under its name, and does not drop a row of a document the answer does not list', () => {
    const row = rowMarkup(markup, A_COUNTED);
    expect(text(row)).toContain('версия 2');
    expect(text(row)).toContain('л. 10 / с. 14');
    const answer = sectionAnswer();
    const stray = sectionAnswer({ projects: answer.projects.slice(0, 1) });
    const groups = groupRowsByDocument(stray);
    expect(groups.map((group) => group.documentUid)).toEqual([
      SECTION_DOCUMENT_A, SECTION_DOCUMENT_UNREAD_1, SECTION_DOCUMENT_UNREAD_2, SECTION_DOCUMENT_UNREAD_3, SECTION_DOCUMENT_B,
    ]);
    const last = groups[4]!;
    expect(last.source).toBeUndefined();
    expect(last.rows).toHaveLength(2);
    // The stray group is drawn, named «Документ», and its rows are in the table.
    const html = render(stray, () => undefined, 'form7');
    expect(html).toContain(`data-section-group-row="${SECTION_DOCUMENT_B}"`);
    expect(html).toContain(`data-section-row="${B_FIRST}"`);
  });
});
