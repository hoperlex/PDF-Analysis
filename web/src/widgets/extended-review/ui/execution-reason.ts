/** Saved workflow failures, distinct from a machine critic's recommendation. */
const EXECUTION_REASONS: Readonly<Record<string, string>> = {
  v2_quality_changed_requires_consent: 'Правила анализа изменились после оценки. Для новых обращений нужен новый прогон со свежей оценкой.',
  finding_proposals_changed_requires_consent: 'Правила предложений важности и рекомендаций изменились после оценки. Для новых обращений нужен новый прогон со свежей оценкой.',
  input_passport_pdf_binding_invalid: 'Исходный PDF не соответствует файлу, закреплённому за версией. Новые обращения остановлены.',
  related_context_incomplete: 'Не весь найденный связанный контекст вошёл в запрос. Ограничения сохранены в записи анализа.',
  substantive_review_reply_refused: 'Часть ответов содержательного критика не прошла проверку. Исходные наблюдения сохранены; непроверенные не получили одобрения.',
  dependency_unavailable: 'Исполнитель не вернул ответ; зависимые проверки не выполнены.',
  dependency_failed: 'Предыдущая процедура не завершилась; эта проверка не выполнялась.',
  provider_outcome_unknown: 'Ответ исполнителя не получен. Результат обращения неизвестен; оставшиеся проверки остановлены.',
  extended_provider_outcome_unknown: 'Ответ исполнителя не получен. Результат обращения неизвестен; оставшиеся проверки остановлены.',
  executor_codex_timeout: 'Codex не завершил ответ за отведённое время.',
  codex_timeout: 'Codex не завершил ответ за отведённое время.',
  executor_task_failed: 'Исполнитель сообщил об ошибке при подготовке ответа.',
  project_parameters_quote_not_in_source: 'Цитата параметра или её привязка не прошла проверку по исходному тексту.',
  project_parameters_value_not_in_quote: 'Значение параметра не подтверждено его исходной цитатой.',
  project_parameters_facts_rejected: 'Часть параметров не прошла проверку по источникам. Подтверждённые записи сохранены.',
  project_parameters_reply_partially_rejected: 'Часть ответов с параметрами не прошла проверку по источникам. Подтверждённые записи сохранены.',
  unsupported_parameter_candidates_rejected: 'Неподтверждённые кандидаты отклонены и сохранены в истории проверки. В параметры проекта они не включены.',
  rejected_unsupported_candidate: 'Кандидат отклонён: его значение или цитата не подтверждены исходным текстом.',
  extended_reply_or_source_invalid: 'Ответ модели получен, но его структура или ссылки на исходные материалы не прошли проверку.',
  comprehensive_analysis_reply_refused: 'Ответ комплексной сверки получен, но не прошёл проверку по источникам.',
  norm_verification_reply_refused: 'Ответ нормативной сверки получен, но не прошёл проверку цитат и источников.',
  finding_review_reply_refused: 'Ответ критика получен, но не прошёл проверку по исходным наблюдениям.',
  finding_correction_reply_refused: 'Ответ корректора получен, но предложенные уточнения не прошли проверку.',
  block_analysis_reply_refused: 'Ответ анализа блоков получен, но часть записей не прошла проверку. Подтверждённые записи сохранены.',
  block_ensemble_leg_failed: 'Одна ветка анализа блоков не ответила после повторов; судья проверил пакет по второй ветке.',
  block_ensemble_leg_skipped: 'Ветка анализа блоков не ответила несколько пакетов подряд и до конца прогона не спрашивается; судья проверяет пакеты по второй ветке.',
  block_ensemble_judge_failed: 'Судья анализа блоков не ответил; наблюдения обеих веток сохранены без сопоставления.',
  corrector_proposal_invents_number: 'Корректор предложил число, не подтверждённое переданными источниками. Предложение отклонено.',
  candidate_context_unavailable: 'Для модельной нормативной сверки не подготовлены подходящие цитаты. Нормативное основание этих наблюдений не подтверждено.',
  corpus_unavailable: 'Нормативный корпус недоступен; нормативная сверка не выполнена.',
  query_not_proposed: 'Для этого наблюдения модель не предложила нормативный поисковый запрос.',
  no_normative_question: 'В наблюдении нет нормативного вопроса. Поиск нормативного основания для него не требуется.',
  explicit_normative_claim_without_query: 'В наблюдении есть нормативный вопрос, но нет пригодного поискового запроса. Нормативное основание не проверено.',
  literal_standard_reference: 'Поиск подготовлен по точному обозначению нормативного документа из наблюдения.',
  literal_normative_claim: 'Поиск подготовлен по дословной формулировке нормативного вопроса из наблюдения.',
  no_norm_candidates_found: 'Поиск выполнен; нормативное основание не найдено. Это не подтверждает отсутствие требования.',
  context_window_truncated: 'Для части выводов требуется дополнительный контекст. Подробности сохранены в рекомендациях и квитанциях.',
  additional_context_required: 'Для части выводов требуется дополнительный контекст источников.',
  reply_records_rejected: 'Часть полученного ответа не прошла проверку. Корректные записи сохранены; подробности отказов доступны в выгрузке.',
  reply_semantic_repair_failed: 'Дополнительный ответ получен, но часть замечаний проверки осталась неустранённой.',
  primary_text_observations_outside_review_window: 'Часть наблюдений основного текстового анализа не прошла расширенную проверку. Исходные записи сохранены.',
  approved_phase_call_limit: 'Часть пакетов осталась за пределами согласованного плана обращений.',
  approved_global_phase_call_limit: 'Часть межоконных пакетов осталась за пределами согласованного плана обращений.',
  accepted_pair_call_limit: 'Это сочетание источников не вошло в согласованный план межоконных обращений.',
  approved_global_phase_call_limit_or_source_selection: 'Часть межоконных сочетаний источников не вошла в согласованный план проверки.',
  accepted_call_limit: 'Этот фрагмент не вошёл в согласованный план извлечения параметров.',
  accepted_input_selection_limit: 'Не все известные фрагменты вошли в согласованный план извлечения параметров.',
  no_corrections_requested: 'По сохранённым рекомендациям критика дополнительные исправления не требовались.',
  no_observations: 'Для этой процедуры нет входных наблюдений.',
  original_review_failed: 'Критик или уточнение по правилам оригинала не завершились из-за ошибки в записи. Наблюдения и результаты прежних процедур сохранены без изменений.',
  original_review_policy_invalid: 'Принятое согласие называет правила критика оригинала, которых эта версия не знает. Проверка остановлена, прогон со свежей оценкой не подменяется.',
};

function safeCode(value: unknown): string {
  return typeof value === 'string' && /^[a-z][a-z0-9_.:-]{0,159}$/i.test(value) ? value : '';
}

export function extendedExecutionReason(reason: unknown, dependency?: unknown, status?: unknown, errorCode?: unknown): string {
  const code = typeof reason === 'string' ? reason : '';
  const detailCode = safeCode(errorCode) || safeCode(dependency);
  const codes = Array.from(new Set([safeCode(reason), detailCode].filter(Boolean)));
  const detail = EXECUTION_REASONS[detailCode];
  const partialDependency = status === 'partial' && (code === 'dependency_failed' || code === 'dependency_unavailable');
  const explanation = detail ?? (partialDependency
    ? 'Часть окон или пакетов не завершилась из-за ошибки предыдущей процедуры. Выполненные результаты сохранены.'
    : EXECUTION_REASONS[code]) ?? 'Сервер сохранил причину неполного выполнения. Исходная запись доступна в полной выгрузке.';
  return `${explanation}${codes.length > 0 ? ` Код: ${codes.join(', ')}.` : ''}`;
}
