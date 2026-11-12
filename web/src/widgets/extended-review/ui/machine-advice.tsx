import { EXTENDED_ADVICE as ADVICE, EXTENDED_CORRECTION_ACTION as ACTION, EXTENDED_REASONS as REASON, extendedReasonText } from '@/entities/audit-run';

import styles from './extended-review.module.css';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function correctionReason(value: unknown): string {
  const reason = text(value).trim();
  return reason ? extendedReasonText(reason) : '';
}
function EvidenceQuotes({ value }: { readonly value: unknown }) {
  const entries = Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : [];
  return entries.length === 0 ? null : <section><h5>Дословные свидетельства, указанные моделью</h5><ul>{entries.map((entry, index) => <li key={`${text(entry.source_id)}:${index}`}><p>Источник: <code>{text(entry.source_id) || 'Не передан'}</code>.</p><blockquote>{text(entry.quote)}</blockquote></li>)}</ul><p>Сверьте эти цитаты с исходными материалами выше; решение эксперта не принято.</p></section>;
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
  // `V2-ORIGINAL-REVIEW-01`: a row of the original's deterministic critic or corrector is a rule's word, not a model's, and says so.
  const rule = critic === null ? fixed?.mode === 'deterministic' : critic.mode === 'deterministic';
  return <section aria-label="Машинная рекомендация и исправленный кандидат" data-extended-machine-advice="" {...(rule ? { 'data-machine-mode': 'deterministic' } : {})}>
    <h4>Критика и уточнение кандидата</h4>
    <p>{rule ? 'Рекомендация правил оригинала (без модели) не является принятием или отклонением экспертом. Исходная запись сохранена.' : 'Рекомендация модели не является принятием или отклонением экспертом. Исходная запись сохранена.'}</p>
    {critic === null ? null : <aside data-machine-recommendation={text(critic.llm_decision)}>
      <strong>{ADVICE[text(critic.llm_decision)] ?? 'Рекомендация требует проверки'}</strong>
      {text(critic.explanation) ? <p>{text(critic.explanation)}</p> : null}
      {text(critic.human_taxonomy_reason) ? <p>Основание рекомендации: {REASON[text(critic.human_taxonomy_reason)] ?? 'Требуется экспертная сверка пояснения и источников'}</p> : null}
      {text(critic.suggested_fix) ? <p>Предложение: {text(critic.suggested_fix)}</p> : null}
      {critic.source_dependency === 'needs_more_context' ? <p>{critic.mode === 'deterministic' ? 'Правило не нашло подтверждающий источник; требуется дополнительный исходный контекст.' : 'Модель сообщает, что требуется дополнительный исходный контекст.'}</p> : critic.source_dependency === 'cross_section_required' ? <p>Для проверки требуются материалы смежного раздела.</p> : null}
      {typeof critic.confidence === 'number' && Number.isFinite(critic.confidence) && critic.confidence >= 0 && critic.confidence <= 1 ? <p>Заявленная моделью уверенность: {Math.round(critic.confidence * 100)}%. Это не оценка эксперта.</p> : null}
      {critic.mode === 'deterministic' ? <p>Проверено по правилам, без модели: наличие источника, его существование в записи и страница цитаты. Смысловая проверка не выполнялась.</p>
        : critic.evidence_checked === true ? <p>Источники просмотрены моделью; экспертная проверка не выполнена.</p> : <p>Проверка источников моделью не подтверждена.</p>}
      <EvidenceQuotes value={critic.source_evidence} />
      {critic.mode === 'substantive' ? <section aria-label="Содержательная проверка">
        {(['evidence', 'alternatives', 'materiality'] as const).map((key) => {
          const check = object(object(critic.substantive_checks)?.[key]);
          const label = { evidence: 'Доказательства', alternatives: 'Альтернативные трактовки', materiality: 'Существенность' }[key];
          return <p key={key}><strong>{label}: {check?.checked === true ? 'рассмотрены' : 'проверка не подтверждена'}.</strong> {text(check?.explanation)}</p>;
        })}
        {Array.isArray(critic.visual_evidence) ? <ul>{critic.visual_evidence.map((value, index) => { const row = object(value); return <li key={index}>Изображение <code>{text(row?.source_id)}</code>: {text(row?.explanation)}</li>; })}</ul> : null}
        {critic.validator_downgrade_reason ? <p>Для уверенного вывода не хватило подтверждённой проверки или источников; требуется экспертная сверка.</p> : null}
      </section> : null}
    </aside>}
    {fixed === null ? null : <section data-machine-correction={text(fixed.action)}>
      <p><strong>{ACTION[text(fixed.action)] ?? 'Исправление требует проверки'}</strong>{correctionReason(fixed.reason) ? ` · ${correctionReason(fixed.reason)}` : ''}</p>
      {fixed.action === 'needs_context' ? <p>{fixed.mode === 'deterministic' ? 'Правило сохранило исходное наблюдение: без источника исправить нечего. Ничего не удалено и не изменено.' : 'Модель сохранила исходное наблюдение и запросила дополнительные материалы. Завершение обработки ответа не означает разрешения этого вопроса.'}</p> : null}
      <div className={styles.evidence}>
        <section aria-label="Исходное наблюдение"><h5>Исходное наблюдение</h5>
          {original === null ? <p>Отдельный снимок исходной записи не передан; исходная запись показана выше.</p> : <><strong>{text(original.title)}</strong><p>{text(original.description)}</p></>}
        </section>
        <section aria-label="Предложенный исправленный кандидат"><h5>Исправленный кандидат</h5>
          {candidate === null ? <p>Новый текст не предложен. Исходное наблюдение не удалено.</p> : <><strong>{text(candidate.title)}</strong><p>{text(candidate.description)}</p>
            {Array.isArray(candidate.source_ids) ? <p>Источники: {candidate.source_ids.filter((item): item is string => typeof item === 'string').join(', ') || 'Не переданы'}</p> : null}
            <EvidenceQuotes value={candidate.source_evidence} />
          </>}
        </section>
      </div>
      {Array.isArray(fixed.required_context) && fixed.required_context.length > 0 ? <><h5>Что ещё требуется</h5><ul>{fixed.required_context.map((item, index) => <li key={index}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>)}</ul></> : null}
    </section>}
  </section>;
}
