/**
 * How «Оптимизация разделов» words its answer (`W63-SECTION-FORM7-01`).
 *
 * Every closed vocabulary of the contract's `SectionSpecification` gets one Russian label; a
 * value this build does not know is reported as such, never guessed. The labels of the match
 * itself (status, basis, reason, units, money) are the priced specification's own
 * (`@/entities/specification-price`); this module adds the section's: what a set's state, a
 * project's price state, a bound and an exclusion tell the expert, and what to do about it.
 */

import type {
  SectionSpecification,
  SectionSpecificationProject,
  SectionSpecificationRow,
  SectionSpecificationSource,
} from '@/shared/api';

type SourceState = SectionSpecificationSource['state'];
type PriceState = SectionSpecificationProject['price_state'];
type LimitReason = NonNullable<SectionSpecification['limit_reason']>;
type RowStatus = SectionSpecificationRow['price_status'];

export const SECTION_UNKNOWN_LABEL = 'значение вне набора, известного этой версии приложения';

/** Where a set stands, in the words of what is missing and where it is done. */
export const SECTION_SOURCE_STATE_MESSAGES: Readonly<Record<SourceState, string>> = {
  ready: 'сохранённый текст прочитан',
  analysis_missing: 'нет опубликованного прогона — запустите его на экране версии',
  text_unavailable: 'у последнего опубликованного прогона нет сохранённого текстового слоя',
  specification_too_large: 'в тексте больше 10 000 строк спецификации — строки не выводятся',
  not_read: 'не читался: раздел превышает предел одного чтения',
};

/** What a project's price state means for its rows. */
export const SECTION_PRICE_STATE_MESSAGES: Readonly<Record<PriceState, string>> = {
  priced: 'строки сопоставлены с действующим прайс-листом проекта',
  price_list_missing:
    'у проекта нет прайс-листа: строки показаны без цен и сумм, итогов нет — загрузите прайс-лист на вкладке «Оптимизация» проекта',
  not_read: 'прайс-лист не читался: раздел превышает предел одного чтения',
};

/** Why a read stopped before the rows, and the way in: one project. */
export const SECTION_LIMIT_MESSAGES: Readonly<Record<LimitReason, string>> = {
  projects:
    'В системе больше проектов, чем раздел просматривает за один раз. Сводка по всем проектам не строится.',
  sources:
    'В разделе слишком много комплектов для одного чтения. Состав раздела показан, строки и итоги — нет: выберите проект, и будут прочитаны только его комплекты.',
  rows:
    'В разделе слишком много строк спецификации для одного чтения. Состав раздела показан, строки и итоги — нет: выберите проект, и будут прочитаны только его строки.',
};

/** Why a current version is listed beside the section instead of in it. */
export const SECTION_EXCLUSION_LABELS: Readonly<Record<'version_unclassified', string>> = {
  version_unclassified: 'раздел версии не подтверждён экспертом',
};

/** A row's price status when its project has no price list. */
export const SECTION_ROW_STATUS_LABELS: Readonly<Record<RowStatus, string>> = {
  matched: 'сопоставлено',
  ambiguous: 'неоднозначно',
  unmatched: 'не сопоставлено',
  price_list_missing: 'нет прайс-листа проекта',
};

function labelOf<K extends string>(labels: Readonly<Record<K, string>>, value: string): string {
  return Object.prototype.hasOwnProperty.call(labels, value) ? labels[value as K] : SECTION_UNKNOWN_LABEL;
}

export function sectionSourceStateMessage(value: string): string {
  return labelOf(SECTION_SOURCE_STATE_MESSAGES, value);
}

export function sectionPriceStateMessage(value: string): string {
  return labelOf(SECTION_PRICE_STATE_MESSAGES, value);
}

export function sectionLimitMessage(value: string): string {
  return labelOf(SECTION_LIMIT_MESSAGES, value);
}

export function sectionExclusionLabel(value: string): string {
  return labelOf(SECTION_EXCLUSION_LABELS, value);
}

export function sectionRowStatusLabel(value: string): string {
  return labelOf(SECTION_ROW_STATUS_LABELS, value);
}

/** The stage of a confirmed version, as a designer writes it: `П` or `Р`. */
export function stageMark(stage: string): string {
  return stage === 'P' ? 'П' : stage === 'R' ? 'Р' : SECTION_UNKNOWN_LABEL;
}
