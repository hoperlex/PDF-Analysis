/**
 * How a price list and a vendor list are said on screen, in Russian (`W60-PRICE-LIST-01`).
 *
 * Every table here is keyed by the contract's own enum, so a member the contract adds without
 * a sentence here is a type error, not an English word on a screen. A unit price is shown from
 * its exact decimal text — digits regrouped and the point turned into the Russian decimal
 * comma — and never through a JavaScript number, which would round it.
 */

import type {
  PriceListCurrencySource,
  PriceListField,
  PriceListFormat,
  PriceListParseReport,
  PriceListRowReason,
  VendorListSource,
} from '@/shared/api';

export const ROW_REASON_LABELS: Readonly<Record<PriceListRowReason, string>> = {
  name_missing: 'нет наименования',
  unit_missing: 'нет единицы измерения',
  price_missing: 'нет цены',
  price_not_a_number: 'цена записана не числом',
  price_not_positive: 'цена не больше нуля',
  price_precision: 'в цене больше шести знаков после запятой',
  price_too_large: 'цена слишком велика',
  currency_missing: 'валюта не указана',
  currency_unrecognised: 'валюта не распознана',
  value_too_long: 'значение длиннее допустимого',
  section_unrecognised: 'раздел не распознан, позиция принята без раздела',
};

export const CURRENCY_SOURCE_LABELS: Readonly<Record<PriceListCurrencySource, string>> = {
  column: 'из столбца валюты',
  price_header: 'из заголовка столбца цены',
  default: 'валюта по умолчанию',
};

export const FIELD_LABELS: Readonly<Record<PriceListField, string>> = {
  name: 'наименование',
  unit: 'единица измерения',
  unit_price: 'цена за единицу',
  code: 'код',
  mark: 'марка',
  currency: 'валюта',
  vendor: 'поставщик',
  section: 'раздел',
};

export const FORMAT_LABELS: Readonly<Record<PriceListFormat, string>> = {
  csv: 'таблица CSV',
  xlsx: 'книга Excel',
};

export const VENDOR_SOURCE_LABELS: Readonly<Record<VendorListSource, string>> = {
  project: 'список проекта',
  global: 'общий список',
  none: 'не задан',
};

const ENCODING_LABELS: Readonly<Record<NonNullable<PriceListParseReport['encoding']>, string>> = {
  'utf-8': 'UTF-8',
  'utf-8-sig': 'UTF-8 с меткой порядка байтов',
  'utf-16': 'UTF-16',
  cp1251: 'кириллическая кодировка 1251',
};

const DELIMITER_LABELS: Readonly<Record<NonNullable<PriceListParseReport['delimiter']>, string>> = {
  ';': 'точка с запятой',
  '\t': 'табуляция',
  ',': 'запятая',
};

/** How the file was read, in one line: the format and its encoding and delimiter or sheet. */
export function sourceDescription(report: PriceListParseReport): string {
  const parts: string[] = [FORMAT_LABELS[report.format]];
  if (report.encoding !== null) parts.push(`кодировка: ${ENCODING_LABELS[report.encoding]}`);
  if (report.delimiter !== null) parts.push(`разделитель: ${DELIMITER_LABELS[report.delimiter]}`);
  if (report.sheet !== null && report.sheet !== '') parts.push(`лист «${report.sheet}»`);
  parts.push(`заголовок в строке ${report.header_row}`);
  return parts.join(', ');
}

/** Thousands separated by a narrow no-break space, the decimal point as a comma. */
export function formatUnitPrice(text: string): string {
  const [whole = '', fraction] = text.split('.');
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, '\u202f');
  return fraction === undefined ? grouped : `${grouped},${fraction}`;
}

/** The usual Russian names of the currencies a price list here is likely to state. */
const CURRENCY_LABELS: Readonly<Record<string, string>> = {
  RUB: 'руб.',
  USD: 'долл. США',
  EUR: 'евро',
  CNY: 'юань',
  KZT: 'тенге',
  BYN: 'бел. руб.',
};

/** A currency's Russian name, or its ISO 4217 code when this table has no name for it. */
export function currencyLabel(code: string): string {
  return CURRENCY_LABELS[code] ?? code;
}

/** «12 345,67 руб.»: the exact price and the currency the price list stated, never converted. */
export function formatPrice(unitPrice: string, currency: string): string {
  return `${formatUnitPrice(unitPrice)} ${currencyLabel(currency)}`;
}
