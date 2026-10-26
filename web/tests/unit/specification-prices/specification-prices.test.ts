/**
 * «Спецификация и цены» (`W60-OPT-MATCH-01`): a document set's AR specification priced from the
 * project's price list, read-only.
 *
 * Rendered, not read from source (`D-53`): every assertion is on markup a reviewer would see.
 * The money rule is the subject: a price and an amount only on a row that counts in a total,
 * a dash elsewhere (never `0`), totals per currency, the excluded rows counted by reason, and
 * the server's decimals shown exactly.
 */

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import type { DocumentVersion, SpecificationPriceRow, SpecificationPrices } from '@/shared/api';
import { ApiError, queryKeys } from '@/shared/api';
import {
  SPECIFICATION_ROW_LIMIT,
  SPECIFICATION_STATE_MESSAGES,
  UNKNOWN_VALUE_LABEL,
  currencyLabel,
  formatDecimal,
  formatMoney,
  specificationPricesQueryOptions,
  specificationStatusLabel,
} from '@/entities/specification-price';
import { ProjectOptimisation } from '@/widgets/project-optimisation';
import {
  SpecificationPricesAnswer,
  SpecificationPricesChooser,
  SpecificationPricesSection,
  arDocumentSets,
} from '@/widgets/specification-prices';

import { newClient, renderScreen, seedError } from '../screens/harness';

const ULID = '01J9ZQ8K7NHVXW3T2R5M6P4Q8F';
const PROJECT = `prj_${ULID}`;
const DOCUMENT = `doc_${ULID}`;
const OTHER_DOCUMENT = 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8G';
const VERSION = `ver_${ULID}`;
const POSITION = `prp_${ULID}`;

function row(over: Partial<SpecificationPriceRow>): SpecificationPriceRow {
  return {
    row_id: `sr-${'0'.repeat(32)}`, page_number: 14, sheet_label: '10', line_start: 3, line_end: 3,
    table_ordinal: 1, group: null, position: '1', name: 'Металлический щит МЩ-1', unit_text: 'шт',
    unit: 'шт', quantity_text: '12', quantity: '12', quantity_issue: null, mass_text: null, note: null,
    status: 'unmatched', reason: 'no_position', basis: null, price_position: null,
    candidate_position_ids: [], candidate_count: 0, amount: null, excluded_reason: 'no_position',
    ...over,
  };
}

const PRICE = {
  price_list_position_id: POSITION, row_number: 7, code: null, name: 'Мет. щит МЩ-1', mark: null,
  unit: 'шт', unit_price: '15000', currency: 'RUB', vendor: null,
};

function answer(over: Partial<SpecificationPrices> = {}): SpecificationPrices {
  const items = [
    row({ row_id: `sr-${'a'.repeat(32)}`, status: 'matched', reason: null, basis: 'name', price_position: PRICE,
      candidate_position_ids: [POSITION], candidate_count: 1, amount: '180000', excluded_reason: null }),
    row({ row_id: `sr-${'b'.repeat(32)}`, position: '2', name: 'Лента монтажная', status: 'matched', reason: null,
      basis: 'mark', price_position: { ...PRICE, unit_price: '450' }, quantity: null, quantity_text: '-',
      quantity_issue: 'not_numeric', candidate_position_ids: [POSITION], candidate_count: 1, amount: null,
      excluded_reason: 'quantity_not_numeric' }),
    row({ row_id: `sr-${'c'.repeat(32)}`, position: '3', name: 'Профиль направляющий', unit: 'п.м',
      unit_text: 'п. м', status: 'unmatched', reason: 'unit_mismatch', candidate_position_ids: [POSITION],
      candidate_count: 1, excluded_reason: 'unit_mismatch' }),
    row({ row_id: `sr-${'d'.repeat(32)}`, position: '4', name: 'Пена монтажная', status: 'ambiguous',
      reason: 'several_positions', candidate_position_ids: [POSITION, POSITION], candidate_count: 2,
      excluded_reason: 'ambiguous' }),
  ];
  return {
    project_uid: PROJECT, document_uid: DOCUMENT, version_uid: VERSION, version_ordinal: 2, page_count: 30,
    state: 'ready', project_stage: 'R', section_code: 'AR',
    price_list: {
      price_list_id: `prl_${ULID}`, revision_number: 3, source_filename: 'Прайс 2026.csv',
      uploaded_at: '2026-10-20T08:00:00Z', default_currency: 'RUB', position_count: 9,
    },
    run_id: `run_${ULID}`, text_layer_sha256: 'e'.repeat(64),
    extraction: {
      algorithm: 'specification-text-v1', table_count: 1, row_count: 4, skipped_count: 1,
      skipped_by_reason: {
        table_header_ambiguous: 0, text_before_first_row: 0, continuation_limit: 0, anchor_ambiguous: 0,
        position_missing: 1, name_missing: 0, column_numbering: 0, rows_over_limit: 0,
      },
      skipped: [{ page_number: 14, line: 4, reason: 'position_missing', excerpt: 'План на отметке 12' }],
      tables: [],
    },
    matching: {
      algorithm: 'price-match-v1',
      counts: { matched: 2, ambiguous: 1, unmatched: 1 },
      totals: [
        { currency: 'EUR', amount: '2550.00', row_count: 1 },
        { currency: 'RUB', amount: '1502006.5', row_count: 1 },
      ],
      excluded: { no_position: 0, unit_mismatch: 1, row_unit_missing: 0, ambiguous: 1, quantity_not_numeric: 1 },
    },
    rows: { offset: 0, limit: SPECIFICATION_ROW_LIMIT, total: 4, next_offset: null, items },
    ...over,
  };
}

function render(value: SpecificationPrices): string {
  return renderToStaticMarkup(createElement(SpecificationPricesAnswer, { answer: value, onPage: () => undefined }));
}

function cellOf(markup: string, rowId: string, attribute: string): string {
  const rowStart = markup.indexOf(`data-spec-row="${rowId}"`);
  expect(rowStart).toBeGreaterThan(-1);
  const rowMarkup = markup.slice(rowStart, markup.indexOf('</tr>', rowStart));
  const match = new RegExp(`${attribute}="([^"]*)"[^>]*>(.*?)</td>`).exec(rowMarkup);
  expect(match, attribute).not.toBeNull();
  return `${match![1] ?? ''}|${(match![2] ?? '').replace(/<[^>]+>/g, '')}`;
}

describe('the money rule on screen', () => {
  const markup = render(answer());

  it('shows a price and an amount only on a row that counts in a total', () => {
    expect(cellOf(markup, `sr-${'a'.repeat(32)}`, 'data-spec-amount')).toBe('180000|180\u00a0000\u00a0руб.');
    expect(cellOf(markup, `sr-${'a'.repeat(32)}`, 'data-spec-price')).toBe('15000|15\u00a0000\u00a0руб.');
    // Matched to one position, but the quantity is no number: the position, no price, no sum.
    expect(cellOf(markup, `sr-${'b'.repeat(32)}`, 'data-spec-price')).toBe('none|—');
    expect(cellOf(markup, `sr-${'b'.repeat(32)}`, 'data-spec-amount')).toBe('none|— (количество не числом)');
    expect(cellOf(markup, `sr-${'c'.repeat(32)}`, 'data-spec-amount')).toBe('none|— (другая единица измерения)');
    expect(cellOf(markup, `sr-${'d'.repeat(32)}`, 'data-spec-amount')).toBe('none|— (несколько подходящих позиций)');
    expect(markup).not.toMatch(/>0\u00a0руб\./);
  });

  it('marks exactly the counted rows', () => {
    const counted = [...markup.matchAll(/data-spec-counted="(yes|no)"/g)].map((m) => m[1]);
    expect(counted).toEqual(['yes', 'no', 'no', 'no']);
  });

  it('gives each status its label and says why a row is not matched', () => {
    expect(markup).toContain('сопоставлено');
    expect(markup).toContain('по наименованию');
    expect(markup).toContain('по марке');
    expect(markup).toContain('позиция есть, но в другой единице измерения');
    expect(markup).toContain('подходят несколько позиций прайс-листа; кандидатов: 2');
    expect(markup).toContain('п. м');
  });

  it('keeps the totals per currency, never summed, and counts what they leave out', () => {
    expect(markup).toContain('data-spec-total="EUR"');
    expect(markup).toContain('2\u00a0550,00\u00a0евро');
    expect(markup).toContain('1\u00a0502\u00a0006,5\u00a0руб.');
    expect(markup).toContain('Итоги в разных валютах не складываются и не пересчитываются.');
    expect(markup).toContain('data-spec-excluded="3"');
    expect(markup).toContain(
      'Не вошли в итог строк: 3 — другая единица измерения: 1; несколько подходящих позиций: 1; количество не числом: 1.',
    );
  });

  it('says when nothing counts instead of showing a zero total', () => {
    const none = render(answer({
      matching: { ...answer().matching!, totals: [], counts: { matched: 0, ambiguous: 1, unmatched: 3 } },
    }));
    expect(none).toContain('data-spec-total="none"');
    expect(none).toContain('Итога нет');
    expect(none).not.toContain('data-spec-total="RUB"');
  });

  it('lists the skipped lines with their reason', () => {
    expect(markup).toContain('Строки таблиц, которые не прочитаны: 1');
    expect(markup).toContain('с. 14, строка 4: число в конце строки, но нет номера позиции');
  });

  it('names the price list, the version and the run it read', () => {
    expect(markup).toContain('«Прайс 2026.csv», редакция 3, позиций: 9');
    expect(markup).toContain('версия 2, страниц: 30, раздел АР, стадия Р');
    expect(markup).toContain(`run_${ULID}`);
  });
});

describe('every state that stops the table is said, never an empty table', () => {
  for (const state of Object.keys(SPECIFICATION_STATE_MESSAGES) as (keyof typeof SPECIFICATION_STATE_MESSAGES)[]) {
    it(state, () => {
      const markup = render(answer({ state, matching: null, rows: null, extraction: null }));
      expect(markup).toContain(`data-spec-state="${state}"`);
      expect(markup).toContain(SPECIFICATION_STATE_MESSAGES[state]);
      expect(markup).not.toContain('<table');
      expect(markup).not.toContain('data-spec-totals');
    });
  }

  it('a ready answer without a table says so', () => {
    const markup = render(answer({
      extraction: { ...answer().extraction!, table_count: 0, row_count: 0, skipped_count: 0, skipped: [] },
      rows: { offset: 0, limit: SPECIFICATION_ROW_LIMIT, total: 0, next_offset: null, items: [] },
      matching: { ...answer().matching!, totals: [], counts: { matched: 0, ambiguous: 0, unmatched: 0 },
        excluded: { no_position: 0, unit_mismatch: 0, row_unit_missing: 0, ambiguous: 0, quantity_not_numeric: 0 } },
    }));
    expect(markup).toContain('Таблицы спецификации в тексте версии не найдены');
    expect(markup).toContain('В итог вошли все строки спецификации.');
    expect(markup).not.toContain('<table');
  });
});

describe('paging', () => {
  it('pages through the rows while the totals stay whole', () => {
    const paged = render(answer({
      rows: { ...answer().rows!, offset: 50, total: 120, next_offset: 100 },
    }));
    expect(paged).toContain('Строки 51–54 из 120');
    expect(paged).toContain('Предыдущие');
    expect(paged).toContain('Следующие');
    expect(render(answer())).not.toContain('data-spec-pager');
  });
});

describe('the set chooser offers only sets confirmed as АР', () => {
  const ar = { classification: { version_uid: VERSION, project_stage: 'R', section_code: 'AR',
    confirmed_at: '2026-10-20T08:00:00Z', confirmed_by_user_uid: `usr_${ULID}` } } as const;
  const versions = [
    { document_uid: DOCUMENT, version_ordinal: 2, display_title: 'Архитектурные решения', ...ar },
    { document_uid: OTHER_DOCUMENT, version_ordinal: 1, display_title: 'Конструкции',
      classification: { ...ar.classification, section_code: 'KJ' } },
    { document_uid: 'doc_01J9ZQ8K7NHVXW3T2R5M6P4Q8H', version_ordinal: 1 },
  ] as unknown as DocumentVersion[];

  it('filters by the current version\'s confirmed section', () => {
    expect(arDocumentSets(versions).map((v) => v.document_uid)).toEqual([DOCUMENT]);
  });

  it('says when there is none, and where a section is confirmed', () => {
    const markup = renderToStaticMarkup(createElement(SpecificationPricesChooser, {
      sets: [], selected: null, onSelect: () => undefined, partial: false,
    }));
    expect(markup).toContain('В проекте нет комплектов раздела АР');
    expect(markup).toContain('Подтвердите раздел на экране версии.');
  });

  it('reads the first АР set from the project\'s documents', () => {
    const client = newClient();
    client.setQueryData(queryKeys.projects.documents(PROJECT, undefined, 50), {
      items: versions, page: { next_cursor: null },
    });
    client.setQueryData(queryKeys.optimisation.specificationPrices(PROJECT, DOCUMENT, 0, SPECIFICATION_ROW_LIMIT), answer());
    const markup = renderScreen(client, createElement(SpecificationPricesSection, { projectUid: PROJECT }));
    expect(markup).toContain('data-spec-chooser="1"');
    expect(markup).toContain('Архитектурные решения — версия 2');
    expect(markup).not.toContain('Конструкции');
    expect(markup).toContain('data-spec-state="ready"');
  });

  it('says the read failed, with the correlation id, rather than showing nothing', () => {
    const client = newClient();
    client.setQueryData(queryKeys.projects.documents(PROJECT, undefined, 50), {
      items: versions, page: { next_cursor: null },
    });
    seedError(
      client,
      queryKeys.optimisation.specificationPrices(PROJECT, DOCUMENT, 0, SPECIFICATION_ROW_LIMIT),
      new ApiError(404, {
        contract_version: '1.5.0', error_code: 'not_found', message: 'Нет такого комплекта.',
        correlation_id: '0f0e9d8c-7b6a-4948-b726-150413021100', retryable: false,
      }, '0f0e9d8c-7b6a-4948-b726-150413021100'),
    );
    const markup = renderScreen(client, createElement(SpecificationPricesSection, { projectUid: PROJECT }));
    expect(markup).toContain('Спецификация и цены не прочитаны');
    expect(markup).toContain('0f0e9d8c-7b6a-4948-b726-150413021100');
    expect(markup).not.toContain('data-spec-state');
  });
});

describe('presentation', () => {
  it('groups the exact decimal and never rounds it', () => {
    expect(formatDecimal('502006.5')).toBe('502\u00a0006,5');
    expect(formatDecimal('15432.0986375')).toBe('15\u00a0432,0986375');
    expect(formatDecimal('999')).toBe('999');
    expect(formatDecimal('-1000')).toBe('-1\u00a0000');
    expect(formatDecimal('не число')).toBe('не число');
    expect(formatMoney(null, 'RUB')).toBe('—');
    expect(formatMoney('0', 'RUB')).toBe('0\u00a0руб.');
  });

  it('names a known currency in words and shows an unknown code as it is', () => {
    expect(currencyLabel('RUB')).toBe('руб.');
    expect(currencyLabel('EUR')).toBe('евро');
    expect(currencyLabel('KZT')).toBe('KZT');
  });

  it('reports a value outside the known set instead of guessing', () => {
    expect(specificationStatusLabel('matched')).toBe('сопоставлено');
    expect(specificationStatusLabel('approved')).toBe(UNKNOWN_VALUE_LABEL);
  });

  it('keys one page of one set under the project', () => {
    expect(specificationPricesQueryOptions(PROJECT, DOCUMENT, 50).queryKey).toEqual(
      ['optimisation', 'specification-prices', PROJECT, DOCUMENT, { offset: 50, limit: SPECIFICATION_ROW_LIMIT }],
    );
    expect(queryKeys.optimisation.specificationPricesAll(PROJECT)).toEqual(['optimisation', 'specification-prices', PROJECT]);
  });
});

describe('the «Оптимизация» tab', () => {
  it('shows «Спецификация и цены» between the price lists and the vendor lists', () => {
    const markup = renderScreen(newClient(), createElement(ProjectOptimisation, {
      projectUid: PROJECT as never, roles: ['expert'],
    }));
    const price = markup.indexOf('Прайс-листы проекта');
    const specification = markup.indexOf('data-specification-prices');
    const vendors = markup.indexOf('Вендор-листы по разделам');
    expect(price).toBeGreaterThan(-1);
    expect(specification).toBeGreaterThan(price);
    expect(vendors).toBeGreaterThan(specification);
    expect(markup).toContain('Спецификация и цены');
  });
});
