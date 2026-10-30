/** Labels for provisional extended-analysis advice, never canonical expert verdicts. */
export const EXTENDED_ADVICE: Readonly<Record<string, string>> = {
  accept: 'Рекомендует сохранить кандидат', reject: 'Рекомендует снять наблюдение', borderline: 'Пограничный случай',
  needs_human: 'Нужна проверка человека', rewrite: 'Рекомендует уточнить формулировку',
};
export const EXTENDED_CORRECTION_ACTION: Readonly<Record<string, string>> = {
  retain: 'Сохранить исходное наблюдение', propose_revision: 'Предложено уточнение', needs_context: 'Нужны дополнительные данные',
};
export const EXTENDED_NORM_STATUS: Readonly<Record<string, string>> = {
  candidates: 'Есть кандидаты нормативных ссылок', not_found: 'Подходящие нормативные ссылки не найдены',
  unavailable: 'Нормативные основания не проверены или недоступны',
};
export const EXTENDED_REASONS: Readonly<Record<string, string>> = {
  visual_or_ocr_misread: 'Возможная ошибка чтения изображения или распознанного текста',
  duplicate_or_already_covered: 'Наблюдение повторяет уже рассмотренный вопрос',
  wrong_norm_context: 'Нормативная ссылка использована вне подходящего контекста',
  acceptable_design_solution: 'Проектное решение может быть допустимым',
  not_functionally_significant: 'Функциональная значимость не подтверждена',
  insufficient_source_context: 'Недостаточно исходного контекста',
  value_already_correct: 'Значение в источнике уже соответствует проверяемому условию',
  false_positive_due_to_missing_context: 'Возможное ложное замечание из-за неполного контекста',
  requirement_not_mandatory: 'Обязательность требования не подтверждена',
  already_resolved_by_project_note: 'Вопрос может быть раскрыт в примечании проекта',
  other: 'Иное основание; требуется сверка пояснения и источников',
};
export function extendedReasonText(value: unknown): string {
  const reason = typeof value === 'string' ? value.trim() : '';
  return EXTENDED_REASONS[reason] ?? (/[а-яё]/i.test(reason) ? reason : reason ? 'Основание требует экспертной сверки; исходная запись сохранена в полной выгрузке.' : 'Не передано');
}
