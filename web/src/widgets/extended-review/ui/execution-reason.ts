/** Saved workflow failures, distinct from a machine critic's recommendation. */
const EXECUTION_REASONS: Readonly<Record<string, string>> = {
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
};

export function extendedExecutionReason(reason: unknown, dependency?: unknown): string {
  const code = typeof reason === 'string' ? reason : '';
  const detail = typeof dependency === 'string' ? EXECUTION_REASONS[dependency] : undefined;
  return detail ?? EXECUTION_REASONS[code] ?? 'Сохранена причина неполного выполнения; подробности доступны в исходной записи и полной выгрузке.';
}
