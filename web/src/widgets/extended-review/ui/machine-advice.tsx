type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
const ADVICE: Readonly<Record<string, string>> = {
  accept: 'Сохранить как кандидат', reject: 'Рекомендует снять наблюдение', borderline: 'Пограничный случай',
  needs_human: 'Нужна проверка человека', rewrite: 'Рекомендует уточнить формулировку',
};
const ACTION: Readonly<Record<string, string>> = { retain: 'Сохранить исходное наблюдение', propose_revision: 'Предложено уточнение', needs_context: 'Нужны дополнительные данные' };
const REASON: Readonly<Record<string, string>> = {
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
function correctionReason(value: unknown): string {
  const reason = text(value).trim();
  return REASON[reason] ?? (/[а-яё]/i.test(reason) ? reason : reason ? 'Основание уточнения требует экспертной сверки; исходная запись сохранена в выгрузке.' : '');
}

export function MachineAdvice({ review, correction, reviewStatus, reviewReason }: {
  readonly review: unknown; readonly correction: unknown; readonly reviewStatus?: unknown; readonly reviewReason?: unknown;
}) {
  const critic = object(review);
  const fixed = object(correction);
  const candidate = object(fixed?.candidate);
  const original = object(fixed?.original);
  if (critic === null && fixed === null) return reviewStatus === 'not_reviewed' ? <p data-machine-review-status="not_reviewed">
    Машинная критика этого кандидата не выполнялась. {reviewReason === 'outside_critic_window'
      ? 'Кандидат находится за пределами окна критики.' : reviewReason === 'outside_processed_review_window'
        ? 'Кандидат находится за пределами обработанного окна проверки.' : 'Причина и исходная запись доступны в выгрузке.'}
  </p> : null;
  return <section aria-label="Машинная рекомендация и исправленный кандидат" data-extended-machine-advice="">
    <h4>Критика и уточнение кандидата</h4>
    <p>Рекомендация модели не является принятием или отклонением экспертом. Исходная запись сохранена.</p>
    {critic === null ? null : <aside data-machine-recommendation={text(critic.llm_decision)}>
      <strong>{ADVICE[text(critic.llm_decision)] ?? 'Рекомендация требует проверки'}</strong>
      {text(critic.explanation) ? <p>{text(critic.explanation)}</p> : null}
      {text(critic.human_taxonomy_reason) ? <p>Основание рекомендации: {REASON[text(critic.human_taxonomy_reason)] ?? 'Требуется экспертная сверка пояснения и источников'}</p> : null}
      {text(critic.suggested_fix) ? <p>Предложение: {text(critic.suggested_fix)}</p> : null}
      {critic.evidence_checked === true ? <p>Источники просмотрены моделью; экспертная проверка не выполнена.</p> : <p>Проверка источников моделью не подтверждена.</p>}
      {Array.isArray(critic.source_evidence) && critic.source_evidence.length > 0 ? <details><summary>Данные рекомендации и источники</summary><pre>{JSON.stringify(critic.source_evidence, null, 2)}</pre></details> : null}
    </aside>}
    {fixed === null ? null : <section data-machine-correction={text(fixed.action)}>
      <p><strong>{ACTION[text(fixed.action)] ?? 'Исправление требует проверки'}</strong>{correctionReason(fixed.reason) ? ` · ${correctionReason(fixed.reason)}` : ''}</p>
      <div className="am-decision__evidence">
        <section aria-label="Исходное наблюдение"><h5>Исходное наблюдение</h5>
          {original === null ? <p>Отдельный снимок исходной записи не передан; исходная запись показана выше.</p> : <><strong>{text(original.title)}</strong><p>{text(original.description)}</p></>}
        </section>
        <section aria-label="Предложенный исправленный кандидат"><h5>Исправленный кандидат</h5>
          {candidate === null ? <p>Новый текст не предложен. Исходное наблюдение не удалено.</p> : <><strong>{text(candidate.title)}</strong><p>{text(candidate.description)}</p>
            {Array.isArray(candidate.source_ids) ? <p>Источники: {candidate.source_ids.filter((item): item is string => typeof item === 'string').join(', ') || 'Не переданы'}</p> : null}
            {Array.isArray(candidate.source_evidence) && candidate.source_evidence.length > 0 ? <details><summary>Источники исправленного кандидата</summary><pre>{JSON.stringify(candidate.source_evidence, null, 2)}</pre></details> : null}
          </>}
        </section>
      </div>
      {Array.isArray(fixed.required_context) && fixed.required_context.length > 0 ? <><h5>Что ещё требуется</h5><ul>{fixed.required_context.map((item, index) => <li key={index}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>)}</ul></> : null}
    </section>}
  </section>;
}
