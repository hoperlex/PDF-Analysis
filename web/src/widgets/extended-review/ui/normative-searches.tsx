'use client';

import { useState } from 'react';
import Link from 'next/link';
import { routes } from '@/shared/lib';
import styles from './extended-review.module.css';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function objects(value: unknown): RecordValue[] { return Array.isArray(value) ? value.flatMap((entry) => { const row = object(entry); return row === null ? [] : [row]; }) : []; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
const STATUS: Readonly<Record<string, string>> = { candidates: 'Кандидаты найдены', not_found: 'Поиск не вернул попаданий', unavailable: 'Поиск недоступен или не выполнен', running: 'Поиск выполняется' };
const QUERY_STATUS: Readonly<Record<string, string>> = { completed: 'Ответ поиска получен', failed: 'Ошибка поиска', not_searched: 'Запрос не выполнен' };
const REASON: Readonly<Record<string, string>> = { corpus_unavailable: 'Нормативный корпус не закреплён за прогоном.', query_not_proposed: 'Поисковый запрос для наблюдения не был предложен.', lookup_window_exhausted: 'Запрос находится вне принятого окна поиска.', lookup_unavailable: 'Поиск завершился отказом или ошибкой. Это не отсутствие документа.' };

export function NormativeSearches({ value }: { readonly value: unknown }) {
  const [expanded, setExpanded] = useState(false);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('all');
  const [page, setPage] = useState(0);
  if (!Array.isArray(value)) return null;
  const records = objects(value);
  const needsAttention = (row: RecordValue) => row.status !== 'candidates' || row.search_tail_not_read === true
    || (typeof row.queries_without_answer === 'number' && row.queries_without_answer > 0)
    || objects(row.queries).some((query) => objects(query.hits).some((hit) => hit.candidate_quote_truncated === true));
  const needle = search.trim().toLocaleLowerCase('ru');
  const filtered = records.filter((row) => (status === 'all' || (status === 'attention' ? needsAttention(row) : row.status === status))
    && (!needle || [row.title, row.observation_id, row.window_id, ...(Array.isArray(row.proposed_queries) ? row.proposed_queries : [])]
      .map(text).join('\n').toLocaleLowerCase('ru').includes(needle)));
  const pages = Math.max(1, Math.ceil(filtered.length / 25));
  const current = Math.min(page, pages - 1);
  return <section id="extended-normative-searches" className={styles.batchPanel} aria-label="Журнал нормативного поиска">
    <h3>Журнал нормативного поиска</h3>
    <p>Сохранено квитанций наблюдений: {records.length}; требуют ручного разбора по состоянию поиска: {records.filter(needsAttention).length}. Повторные проходы сохраняются отдельно. Это журнал уже выполненных действий, без новых обращений к корпусу или модели.</p>
    <p>Отсутствие попаданий не доказывает отсутствие документа или требования. Первые три результата не означают полный поиск; непрочитанное продолжение выдачи отмечено отдельно. Найденный кандидат не подтверждает актуальность или применимость нормы.</p>
    {records.length === 0 ? <p>Квитанции поиска ещё не сохранены. По этой записи нельзя заключить, что нормативная проверка не нужна или завершена.</p> : null}
    <details onToggle={(event) => setExpanded(event.currentTarget.open)}><summary>Запросы и основания для ручной сверки</summary>{expanded ? <>
      <div className={styles.toolbar}><label>Поиск по наблюдению и запросам<input value={search} onChange={(event) => { setSearch(event.target.value); setPage(0); }} /></label>
        <label>Состояние<select value={status} onChange={(event) => { setStatus(event.target.value); setPage(0); }}><option value="all">Все</option><option value="attention">Требуют ручного разбора</option>{Object.entries(STATUS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label></div>
      <p>По фильтру {filtered.length} из {records.length}. Полные выгрузки содержат все квитанции.</p>
      <ol className={styles.batchList} start={current * 25 + 1}>{filtered.slice(current * 25, (current + 1) * 25).map((receipt, index) => <li key={`${text(receipt.window_id)}:${text(receipt.observation_id)}:${current * 25 + index}`}>
        <h4>{text(receipt.title) || 'Наблюдение'} · {STATUS[text(receipt.status)] ?? 'Состояние не передано'}</h4>
        <p>Окно {text(receipt.window_id)}; проход поиска {count(receipt.lookup_pass_ordinal)}. Запросов с ответом {count(receipt.queries_answered)}, без ответа или вне окна {count(receipt.queries_without_answer)}; выбранных кандидатов {count(receipt.selected_candidate_count)}.</p>
        {text(receipt.reason) ? <p>{REASON[text(receipt.reason)] ?? 'Требуется ручная сверка причины в исходной квитанции.'}</p> : null}
        {receipt.search_tail_not_read === true ? <p>У поиска есть непрочитанное продолжение. Журнал содержит только полученную страницу.</p> : null}
        <a href="#extended-observations">Открыть наблюдения и их исходные страницы</a>
        <ul>{objects(receipt.queries).map((query, queryIndex) => <li key={queryIndex}>
          <p className={styles.description}>{text(query.query)}</p>
          <p>{QUERY_STATUS[text(query.status)] ?? 'Состояние не передано'}{query.cache_reused === true ? '; использован ответ этого же поискового прохода' : ''}. Получено попаданий: {count(query.received_hits)}.</p>
          {query.has_more === true ? <p>За первой страницей есть дополнительные результаты.</p> : null}
          {objects(query.hits).map((hit, hitIndex) => <p key={`${text(hit.paragraph_id)}:${hitIndex}`}>{text(hit.designation)}; пункт {text(hit.clause_number) || 'не указан'}; страница {count(hit.page_label)}. {text(hit.document_id) ? <Link href={routes.normDocument(text(hit.document_id))}>Открыть норму</Link> : null}{hit.candidate_quote_truncated === true ? ' Переданная цитата сокращена.' : ''}</p>)}
        </li>)}</ul>
        <details><summary>Все предложенные запросы и полная квитанция</summary><pre>{JSON.stringify(receipt, null, 2)}</pre></details>
      </li>)}</ol>
      {filtered.length > 25 ? <nav className={styles.toolbar} aria-label="Страницы журнала нормативного поиска"><button type="button" className="am-button am-button--quiet" disabled={current === 0} onClick={() => setPage(current - 1)}>Предыдущие</button><span>{current + 1} из {pages}</span><button type="button" className="am-button am-button--quiet" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}>Следующие</button></nav> : null}
    </> : null}</details>
  </section>;
}
