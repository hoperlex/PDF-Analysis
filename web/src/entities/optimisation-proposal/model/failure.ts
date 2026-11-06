/**
 * A refused optimisation pass or proposal decision, said in Russian (`W60-OPT-PROPOSALS-01`).
 *
 * `startOptimisationPass` refuses an unmet precondition as `conflict` with a
 * `conflict_reason`; each reason has its own sentence here that says what to do about it, so
 * an expert is never left with the catalog's generic "conflicts with durable state".
 * `decideOptimisationProposal` refuses a `revise` without a comment and a comment that is too
 * long. Everything else falls back to the shared reading of the catalog code
 * (`failureMessage`), so no refusal is ever shown as the API's English message.
 */

import { ApiError } from '@/shared/api';
import type { FailureMessage } from '@/shared/api/failure-message';
import { failureMessage } from '@/shared/api/failure-message';

/** Every `conflict_reason` of `startOptimisationPass`, with what the expert should do. */
export const PASS_REFUSAL_TEXT: Readonly<Record<string, string>> = {
  version_unclassified:
    'Текущую версию комплекта эксперт ещё не отнёс к разделу. Подтвердите раздел на экране версии.',
  section_not_ar:
    'Сервер не принял раздел этой версии комплекта. Обновите страницу и повторите запуск.',
  price_list_missing: 'В проекте нет прайс-листа. Загрузите его выше на этой вкладке.',
  analysis_missing:
    'У текущей версии нет опубликованного прогона. Сначала запустите анализ и дождитесь публикации.',
  text_unavailable:
    'У последнего опубликованного прогона нет сохранённого текста листов, спецификацию прочитать не из чего.',
  specification_too_large:
    'В спецификации больше 10 000 строк. Проход не запущен, ничего не обрезано.',
  vendor_list_missing:
    'Для раздела этого комплекта не задан вендор-лист: нет ни списка проекта, ни общего списка администратора. Задайте его выше на этой вкладке.',
};

export const COMMENT_REQUIRED_TEXT = 'Для решения «На доработку» нужен комментарий: напишите, что изменить.';
export const COMMENT_TOO_LONG_TEXT = 'Комментарий длиннее 2000 знаков.';
/** `UI-B-12`: «Снять решение» over a proposal nobody has decided, or whose decision is already withdrawn. */
export const NOTHING_TO_REVOKE_TEXT =
  'Снимать нечего: по этому предложению нет действующего решения. Обновите страницу, возможно, его уже сняли.';

/** `UI-B-14`: every `conflict_reason` of `carryOverProposalDecisions`, with what the expert should do. */
export const CARRYOVER_REFUSAL_TEXT: Readonly<Record<string, string>> = {
  carryover_source_unknown: 'Проход, из которого переносят решения, не найден. Обновите страницу и выберите версию заново.',
  carryover_source_is_target: 'Нельзя переносить решения прохода в него же.',
  carryover_source_other_document:
    'Этот проход относится к другому комплекту документов: решения переносят только между версиями одного комплекта.',
  carryover_source_not_earlier: 'Переносить решения можно только из прохода по более ранней версии комплекта.',
};

function detailOf(error: unknown, key: string): string | null {
  if (!(error instanceof ApiError)) return null;
  const value = error.details[key];
  return typeof value === 'string' ? value : null;
}

/** The sentence for a refused start: the unmet precondition when it names one. */
export function startPassFailureMessage(error: unknown): FailureMessage {
  const base = failureMessage(error, {
    idempotency_key_reuse:
      'Этот запрос уже был отправлен для другого комплекта. Выберите комплект заново и повторите.',
  });
  const reason = detailOf(error, 'conflict_reason');
  const sentence = reason === null ? undefined : PASS_REFUSAL_TEXT[reason];
  return sentence === undefined ? base : { ...base, detail: sentence };
}

/** The sentence for a refused decision. */
export function decideFailureMessage(error: unknown): FailureMessage {
  const base = failureMessage(error, {
    idempotency_key_reuse:
      'Этот запрос уже был отправлен с другим решением или комментарием. Повторите решение заново.',
  });
  if (detailOf(error, 'field') === 'comment') {
    const constraint = detailOf(error, 'constraint');
    if (constraint === 'required') return { ...base, detail: COMMENT_REQUIRED_TEXT };
    if (constraint === 'max_length') return { ...base, detail: COMMENT_TOO_LONG_TEXT };
  }
  if (detailOf(error, 'conflict_reason') === 'no_decision_to_revoke') return { ...base, detail: NOTHING_TO_REVOKE_TEXT };
  return base;
}

/** `UI-B-14`: the sentence for a refused carryover -- the unusable source when it names one. */
export function carryOverFailureMessage(error: unknown): FailureMessage {
  const base = failureMessage(error, {
    idempotency_key_reuse:
      'Этот запрос уже был отправлен для другой версии. Выберите версию заново и повторите перенос.',
  });
  const reason = detailOf(error, 'conflict_reason');
  const sentence = reason === null ? undefined : CARRYOVER_REFUSAL_TEXT[reason];
  return sentence === undefined ? base : { ...base, detail: sentence };
}
