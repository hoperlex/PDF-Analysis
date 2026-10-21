/**
 * How «Нормативные ссылки» words its answer (`NORM-REFS-RUN-01`).
 *
 * Every closed vocabulary of the contract's `RunNormReferences` gets one Russian label; a value
 * this build does not know is reported as such, never guessed. The five outcomes are the
 * resolver's (`W57-PLAN.md` B3.3): the citation's edition is in the corpus, a newer edition is,
 * only an earlier edition is, the document is not, or the citation could not be read as a
 * designation. None of them is a finding and none carries a severity.
 */

import type { NormReferenceAnchor, NormReferenceItem, RunNormReferences } from '@/shared/api';

type State = RunNormReferences['state'];
type Outcome = NormReferenceItem['outcome'];

export const UNKNOWN_VALUE_LABEL = 'значение вне набора, известного этой версии приложения';

/** What each state that stops the list tells the expert, and what to do about it. */
export const NORM_REFERENCE_STATE_MESSAGES: Readonly<Record<Exclude<State, 'ready'>, string>> = {
  snapshot_not_pinned:
    'Этот прогон запущен, когда ни один снимок нормативной базы не был назначен текущим, поэтому сверять ссылки проекта не с чем. Перезапустите анализ после назначения снимка.',
  text_unavailable:
    'У прогона нет сохранённого текстового слоя, поэтому ссылки на нормативные документы прочитать не из чего.',
  too_many_citations:
    'В тексте проекта больше 1000 различных ссылок на нормативные документы или одна из ссылок длиннее 300 знаков. Такой список не показывается частями: ссылки и итоги не выводятся.',
};

/** The five outcomes, in the order they are listed and counted. */
export const NORM_REFERENCE_OUTCOME_ORDER: readonly Outcome[] = [
  'in_corpus',
  'newer_edition',
  'older_edition_only',
  'not_in_corpus',
  'not_recognised',
];

export const NORM_REFERENCE_OUTCOME_LABELS: Readonly<Record<Outcome, string>> = {
  in_corpus: 'есть в корпусе',
  newer_edition: 'в корпусе есть более новая редакция',
  older_edition_only: 'в корпусе только более ранняя редакция',
  not_in_corpus: 'нет в корпусе',
  not_recognised: 'не распознано',
};

/** One sentence per outcome: what it means, and what it does not. */
export const NORM_REFERENCE_OUTCOME_MEANINGS: Readonly<Record<Outcome, string>> = {
  in_corpus:
    'Документ с той же редакцией, что указана в проекте, есть в нормативной базе, и более новой редакции в ней нет.',
  newer_edition:
    'В нормативной базе есть более новая редакция документа, чем указана в проекте. Это сведение, а не замечание: применимость редакции решает эксперт.',
  older_edition_only:
    'Проект ссылается на редакцию новее той, что есть в нормативной базе: в ней найдена только более ранняя. Скорее всего, база не обновлена; ошибкой проекта это не считается.',
  not_in_corpus:
    'Обозначение прочитано, но такого документа нет в нормативной базе. Это не значит, что документа не существует.',
  not_recognised:
    'Фрагмент похож на ссылку, но обозначение прочитать не удалось: например, не указан год редакции.',
};

function labelOf<K extends string>(labels: Readonly<Record<K, string>>, value: string): string {
  return Object.prototype.hasOwnProperty.call(labels, value) ? labels[value as K] : UNKNOWN_VALUE_LABEL;
}

export function normReferenceOutcomeLabel(value: string): string {
  return labelOf(NORM_REFERENCE_OUTCOME_LABELS, value);
}

export function normReferenceOutcomeMeaning(value: string): string {
  return labelOf(NORM_REFERENCE_OUTCOME_MEANINGS, value);
}

export function normReferenceStateMessage(value: string): string {
  return labelOf(NORM_REFERENCE_STATE_MESSAGES, value);
}

/**
 * The pages a citation occurs on, ascending and distinct: `с. 3, 7, 12`. The server keeps at
 * most ten occurrences, so the list says how many more there are rather than hiding them.
 */
export function citationPlaces(anchors: readonly NormReferenceAnchor[], occurrenceCount: number): string {
  const pages = [...new Set(anchors.map((anchor) => anchor.page_number))].sort((a, b) => a - b);
  const places = pages.length === 1 ? `с. ${pages[0]}` : `с. ${pages.join(', ')}`;
  const hidden = occurrenceCount - anchors.length;
  return hidden > 0 ? `${places} и ещё ${hidden}` : places;
}

/** The pages with no text layer, as a sentence's list: `2, 5`. */
export function pageList(pages: readonly number[]): string {
  return pages.join(', ');
}
