/**
 * How «Спецификация и цены» words its answer (`W60-OPT-MATCH-01`).
 *
 * Every closed vocabulary of the contract's `SpecificationPrices` gets one Russian label; a
 * value this build does not know is reported as such, never guessed. Money is the server's
 * exact decimal text: it is grouped for reading and never parsed into a number, so nothing is
 * rounded on the way to the screen, and an absent amount is a dash — never `0`.
 */

import type { SpecificationPriceRow, SpecificationPrices, SpecificationSkippedLine } from '@/shared/api';

type State = SpecificationPrices['state'];
type Status = SpecificationPriceRow['status'];
type Reason = NonNullable<SpecificationPriceRow['reason']>;
type Basis = NonNullable<SpecificationPriceRow['basis']>;
type Exclusion = NonNullable<SpecificationPriceRow['excluded_reason']>;
type Unit = NonNullable<SpecificationPriceRow['unit']>;
type QuantityIssue = NonNullable<SpecificationPriceRow['quantity_issue']>;
type SkipReason = SpecificationSkippedLine['reason'];

/** What each state that stops the table tells the expert, and what to do about it. */
export const SPECIFICATION_STATE_MESSAGES: Readonly<Record<Exclude<State, 'ready'>, string>> = {
  version_unclassified:
    'Текущая версия комплекта не классифицирована. Подтвердите стадию и раздел на экране версии — спецификация и цены строятся для комплекта с подтверждённым разделом.',
  section_not_ar:
    'Сервер не принял раздел этой версии комплекта. Обновите страницу и повторите чтение.',
  price_list_missing:
    'У проекта нет прайс-листа. Загрузите прайс-лист проекта, чтобы сопоставить с ним спецификацию.',
  analysis_missing:
    'У текущей версии нет опубликованного прогона. Спецификация читается из сохранённого текста прогона — запустите его на экране версии.',
  text_unavailable:
    'У последнего опубликованного прогона нет сохранённого текстового слоя, поэтому спецификацию прочитать не из чего.',
  specification_too_large:
    'В тексте версии больше 10 000 строк спецификации. Такой объём не показывается частями: строки и итоги не выводятся.',
};

export const UNKNOWN_VALUE_LABEL = 'значение вне набора, известного этой версии приложения';

export const SPECIFICATION_STATUS_LABELS: Readonly<Record<Status, string>> = {
  matched: 'сопоставлено',
  ambiguous: 'неоднозначно',
  unmatched: 'не сопоставлено',
};

export const SPECIFICATION_REASON_LABELS: Readonly<Record<Reason, string>> = {
  no_position: 'в прайс-листе нет такой позиции',
  unit_mismatch: 'позиция есть, но в другой единице измерения',
  row_unit_missing: 'у строки не указана единица измерения',
  several_positions: 'подходят несколько позиций прайс-листа',
};

export const SPECIFICATION_BASIS_LABELS: Readonly<Record<Basis, string>> = {
  code: 'по коду',
  mark: 'по марке',
  name: 'по наименованию',
};

/** Why a row is left out of every total, as the totals' footnote names it. */
export const SPECIFICATION_EXCLUSION_LABELS: Readonly<Record<Exclusion, string>> = {
  no_position: 'нет в прайс-листе',
  unit_mismatch: 'другая единица измерения',
  row_unit_missing: 'нет единицы измерения',
  ambiguous: 'несколько подходящих позиций',
  quantity_not_numeric: 'количество не числом',
};

export const SPECIFICATION_UNIT_LABELS: Readonly<Record<Unit, string>> = {
  шт: 'шт.',
  м: 'м',
  м2: 'м²',
  м3: 'м³',
  кг: 'кг',
  т: 'т',
  компл: 'компл.',
  'п.м': 'п. м',
};

export const QUANTITY_ISSUE_LABELS: Readonly<Record<QuantityIssue, string>> = {
  not_numeric: 'количество не числом',
  ambiguous: 'количество нельзя прочитать однозначно',
};

/** Why a line inside a found table became neither a row nor part of one. */
export const SPECIFICATION_SKIP_LABELS: Readonly<Record<SkipReason, string>> = {
  table_header_ambiguous: 'у таблицы две графы количества или наименования — таблица не читается',
  text_before_first_row: 'текст до первой позиции таблицы',
  continuation_limit: 'продолжение наименования длиннее трёх строк',
  anchor_ambiguous: 'в строке несколько пар «единица — количество»',
  position_missing: 'число в конце строки, но нет номера позиции',
  name_missing: 'нет наименования',
  column_numbering: 'строка нумерации граф',
  rows_over_limit: 'сверх предела в 10 000 строк',
};

/** The currencies a Russian price list is written in, named as a reader says them. */
const CURRENCY_LABELS: Readonly<Record<string, string>> = {
  RUB: 'руб.',
  EUR: 'евро',
  USD: 'долл. США',
  CNY: 'юаней',
};

function labelOf<K extends string>(labels: Readonly<Record<K, string>>, value: string): string {
  return Object.prototype.hasOwnProperty.call(labels, value) ? labels[value as K] : UNKNOWN_VALUE_LABEL;
}

export function specificationStatusLabel(value: string): string {
  return labelOf(SPECIFICATION_STATUS_LABELS, value);
}

export function specificationReasonLabel(value: string): string {
  return labelOf(SPECIFICATION_REASON_LABELS, value);
}

export function specificationBasisLabel(value: string): string {
  return labelOf(SPECIFICATION_BASIS_LABELS, value);
}

export function specificationExclusionLabel(value: string): string {
  return labelOf(SPECIFICATION_EXCLUSION_LABELS, value);
}

export function specificationUnitLabel(value: string): string {
  return labelOf(SPECIFICATION_UNIT_LABELS, value);
}

export function quantityIssueLabel(value: string): string {
  return labelOf(QUANTITY_ISSUE_LABELS, value);
}

export function specificationSkipLabel(value: string): string {
  return labelOf(SPECIFICATION_SKIP_LABELS, value);
}

export function specificationStateMessage(value: string): string {
  return labelOf(SPECIFICATION_STATE_MESSAGES, value);
}

/** A currency as words; an unlisted ISO code is shown as the code itself. */
export function currencyLabel(code: string): string {
  return CURRENCY_LABELS[code] ?? code;
}

const DECIMAL = /^(-?)(\d+)(?:\.(\d+))?$/;

/**
 * The server's exact decimal text, grouped for reading: `502006.5` → `502 006,5`.
 *
 * Text in, text out — the digits are never parsed into a number, so nothing is rounded. A
 * value that is not the contract's decimal is shown unchanged rather than repaired.
 */
export function formatDecimal(text: string): string {
  const match = DECIMAL.exec(text);
  if (match === null) return text;
  const [, sign, whole, fraction] = match as unknown as [string, string, string, string | undefined];
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, '\u00a0');
  return `${sign}${grouped}${fraction === undefined ? '' : `,${fraction}`}`;
}

/** An amount and its currency, or a dash when there is none: absent is never `0`. */
export function formatMoney(amount: string | null, currency: string | null): string {
  if (amount === null || currency === null) return '—';
  return `${formatDecimal(amount)}\u00a0${currencyLabel(currency)}`;
}
