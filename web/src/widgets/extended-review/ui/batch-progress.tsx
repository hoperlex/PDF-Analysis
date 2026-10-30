'use client';

import { useState } from 'react';
import styles from './extended-review.module.css';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function objects(value: unknown): RecordValue[] { return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : []; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
const STATUS: Readonly<Record<string, string>> = { queued: 'Запланировано', running: 'Выполняется', completed: 'Завершено', partial: 'Частично', failed: 'Ошибка', unavailable: 'Недоступно', skipped: 'Пропущено' };
const PHASE: Readonly<Record<string, string>> = { block_analysis: 'Анализ изображений', comprehensive_analysis: 'Комплексная сверка', finding_merge: 'Свод наблюдений', norm_verification: 'Сверка нормативных цитат', finding_review: 'Машинная критика', finding_correction: 'Предложения уточнения', report_generation: 'Подготовка отчёта' };

export function BatchProgress({ batches: value, coverage: reading, title = 'Пакеты обработки' }: {
  readonly batches: unknown; readonly coverage: unknown; readonly title?: string;
}) {
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState(0);
  const batches = objects(value);
  const phases = Object.entries(object(reading) ?? {}).flatMap(([phase, value]) => { const counters = object(value); return counters === null ? [] : [{ phase, counters }]; });
  if (batches.length === 0 && phases.length === 0) return null;
  const matches = batches.filter((batch) => filter === 'all' || (filter === 'active'
    ? batch.reason !== 'approved_phase_call_limit' && (batch.status === 'running' || batch.status === 'queued')
    : batch.reason === 'approved_phase_call_limit' || batch.status === 'failed' || batch.status === 'partial' || batch.status === 'unavailable'));
  const pages = Math.max(1, Math.ceil(matches.length / 25));
  const current = Math.min(page, pages - 1);
  const shown = matches.slice(current * 25, (current + 1) * 25);
  return <section className={styles.batchPanel} aria-label={title} data-extended-batches="">
    <h3>{title}</h3>
    <p>Показан известный серверу план. Новые пакеты могут появиться после предыдущих ответов. Завершение пакета не означает экспертного подтверждения его выводов.</p>
    <div className={styles.coverageGrid}>{phases.map(({ phase, counters }) => <section key={phase} data-phase-coverage={phase}>
      <h4>{PHASE[phase] ?? 'Процедура обработки'}</h4>
      <p>Пакетов завершено: <strong>{count(counters.completed)}</strong> из {count(counters.planned)} известных в плане. Осталось: {count(counters.remaining)}.</p>
      {typeof counters.completed === 'number' && typeof counters.planned === 'number' && counters.planned > 0 && counters.completed >= 0 && counters.completed <= counters.planned ? <progress value={counters.completed} max={counters.planned} aria-label={`${PHASE[phase] ?? 'Процедура'}: завершённые пакеты`} /> : null}
      <p>Обработано элементов: {count(counters.processed_items)} из {count(counters.total_items)}. Лимит пакетов процедуры в принятом плане: {count(counters.limit)}.</p>
      {typeof counters.characters_total === 'number' ? <p>Обработано символов: {count(counters.characters_processed)} из {count(counters.characters_total)}.</p> : null}
    </section>)}</div>
    {batches.length === 0 ? <p>Отдельные квитанции пакетов ещё не переданы.</p> : <>
      <div className={styles.toolbar}><label>Состояние пакетов<select value={filter} onChange={(event) => { setFilter(event.target.value); setPage(0); }}><option value="all">Все</option><option value="active">Ожидают или выполняются</option><option value="attention">Ошибка, частично или не обработано</option></select></label><p>По фильтру: {matches.length} из {batches.length}; отображается до 25 пакетов.</p></div>
      {shown.length === 0 ? <p>Квитанций с выбранным состоянием нет.</p> : <ol className={styles.batchList} start={current * 25 + 1}>{shown.map((batch, index) => <li key={text(batch.batch_key) || index} data-batch-key={text(batch.batch_key)}>
        <strong>{PHASE[text(batch.procedure)] ?? 'Процедура обработки'}</strong> · {batch.reason === 'approved_phase_call_limit' ? 'Не обработано: лимит принятого плана' : STATUS[text(batch.status)] ?? 'Состояние не передано'}
        <p>{text(batch.window_id) ? <>Окно <code>{text(batch.window_id)}</code>. </> : null}Пакет {typeof batch.index === 'number' ? batch.index + 1 : '—'}. Входных элементов: {count(batch.input_count)}. Символов на входе: {count(batch.input_characters)}.</p>
        {batch.reason === 'approved_phase_call_limit' ? <p>Этот остаток не обработан: достигнут лимит вызовов процедуры в принятом плане. Дополнительное обращение к модели не подтверждено.</p> : null}
        {Array.isArray(batch.page_numbers) ? <p>Физические страницы PDF: {batch.page_numbers.filter((page): page is number => typeof page === 'number' && Number.isSafeInteger(page) && page > 0).join(', ') || 'Не переданы'}.</p> : null}
        <details><summary>Происхождение пакета</summary><p>Ключ: <code>{text(batch.batch_key)}</code>.</p><p>Входные записи: {Array.isArray(batch.input_ids) ? batch.input_ids.filter((id): id is string => typeof id === 'string').join(', ') || 'Не переданы' : 'Не переданы'}.</p><p>Источники: {Array.isArray(batch.source_ids) ? batch.source_ids.filter((id): id is string => typeof id === 'string').join(', ') || 'Не переданы' : 'Не переданы'}.</p>{objects(batch.context_ranges).length > 0 ? <ul>{objects(batch.context_ranges).map((range, number) => <li key={number}>Стр. {count(range.page_number)} · {range.character_field === 'recognised_context' ? 'распознанный слой' : 'текстовый контекст'}: символы {count(range.character_start)}–{count(range.character_end)}, источник <code>{text(range.source_id)}</code>. Это границы текстового фрагмента, не координаты на PDF.</li>)}</ul> : null}{text(batch.reason) ? <p>Сервер сохранил ограничение; код доступен в полной выгрузке. Полнота обработки этого пакета не подтверждена.</p> : null}</details>
      </li>)}</ol>}
      {matches.length > 25 ? <nav className={styles.toolbar} aria-label="Страницы квитанций пакетов"><button type="button" className="am-button am-button--quiet" disabled={current === 0} onClick={() => setPage(current - 1)}>Предыдущие пакеты</button><span>{current + 1} из {pages}</span><button type="button" className="am-button am-button--quiet" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}>Следующие пакеты</button></nav> : null}
    </>}
  </section>;
}
