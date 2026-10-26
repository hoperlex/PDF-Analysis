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
  return base;
}
