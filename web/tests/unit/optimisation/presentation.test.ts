/**
 * How the «Оптимизация» tab says a price list and a vendor list (`W60-PRICE-LIST-01`): exact
 * prices from their decimal text, currencies by name, every reason and source in Russian.
 */

import { describe, expect, it } from 'vitest';

import type { PriceListParseReport } from '@/shared/api';
import {
  PRICE_LIST_CURRENCY_SOURCE_VALUES,
  PRICE_LIST_FIELD_VALUES,
  PRICE_LIST_FORMAT_VALUES,
  PRICE_LIST_ROW_REASON_VALUES,
  VENDOR_LIST_SOURCE_VALUES,
} from '@/shared/api';
import {
  CURRENCY_SOURCE_LABELS,
  FIELD_LABELS,
  FORMAT_LABELS,
  ROW_REASON_LABELS,
  VENDOR_SOURCE_LABELS,
  currencyLabel,
  formatPrice,
  formatUnitPrice,
  sourceDescription,
} from '@/entities/price-list';

import { positionPage } from './fixtures';

const NNBSP = ' ';

describe('a price is shown from its exact text, never through a number', () => {
  it.each([
    ['125.5', '125,5'],
    ['12345.67', `12${NNBSP}345,67`],
    ['1000000', `1${NNBSP}000${NNBSP}000`],
    ['0.000001', '0,000001'],
    ['99999999999999.999999', `99${NNBSP}999${NNBSP}999${NNBSP}999${NNBSP}999,999999`],
  ])('%s reads %s', (text, shown) => {
    expect(formatUnitPrice(text)).toBe(shown);
  });

  it('keeps every digit a binary float would lose', () => {
    // 0.1 + 0.2 in floating point is 0.30000000000000004; the text is never parsed.
    expect(formatUnitPrice('0.3')).toBe('0,3');
    expect(formatUnitPrice('12345678901234.123456')).toBe(`12${NNBSP}345${NNBSP}678${NNBSP}901${NNBSP}234,123456`);
  });

  it('names the currencies it knows and shows any other by its code', () => {
    expect(formatPrice('125.5', 'RUB')).toBe('125,5 руб.');
    expect(currencyLabel('EUR')).toBe('евро');
    expect(currencyLabel('GBP')).toBe('GBP');
  });
});

describe('every contract member has its Russian label', () => {
  it.each([
    ['PriceListRowReason', PRICE_LIST_ROW_REASON_VALUES, ROW_REASON_LABELS],
    ['PriceListCurrencySource', PRICE_LIST_CURRENCY_SOURCE_VALUES, CURRENCY_SOURCE_LABELS],
    ['PriceListField', PRICE_LIST_FIELD_VALUES, FIELD_LABELS],
    ['PriceListFormat', PRICE_LIST_FORMAT_VALUES, FORMAT_LABELS],
    ['VendorListSource', VENDOR_LIST_SOURCE_VALUES, VENDOR_SOURCE_LABELS],
  ])('%s', (_name, values, labels) => {
    expect(Object.keys(labels).sort()).toEqual([...values].sort());
    for (const label of Object.values(labels)) expect(label).toMatch(/[а-яё]/i);
  });
});

describe('how the file was read', () => {
  it('says the format, encoding, delimiter and header row', () => {
    expect(sourceDescription(positionPage().parse_report)).toBe(
      'таблица CSV, кодировка: кириллическая кодировка 1251, разделитель: точка с запятой, заголовок в строке 2',
    );
  });

  it('names the sheet of a workbook', () => {
    const report: PriceListParseReport = {
      ...positionPage().parse_report,
      format: 'xlsx',
      encoding: null,
      delimiter: null,
      sheet: 'Прайс',
      header_row: 1,
    };
    expect(sourceDescription(report)).toBe('книга Excel, лист «Прайс», заголовок в строке 1');
  });
});
