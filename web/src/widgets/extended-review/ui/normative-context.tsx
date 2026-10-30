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

function Paragraph({ value }: { readonly value: unknown }) {
  const row = object(value);
  if (row === null) return null;
  return <section>
    <p>Пункт {text(row.clause_number) || 'не указан'}; страница нормы {count(row.page_label)}. Символы абзаца {count(row.paragraph_character_start)}–{count(row.paragraph_character_end)} из {count(row.full_paragraph_characters)}.</p>
    <p>{row.text_reliability === 'reliable' ? 'Текст отмечен корпусом как надёжный.' : 'Надёжность текста не подтверждена; требуется сверка источника.'}{row.truncated === true ? ' Передан фрагмент абзаца.' : ' Передан весь сохранённый абзац.'}</p>
    <blockquote>{text(row.text)}</blockquote>
    <details><summary>Идентичность и отпечаток фрагмента</summary><pre>{JSON.stringify({ paragraph_id: row.paragraph_id, block_ref: row.block_ref, ordinal: row.ordinal, excerpt_sha256: row.excerpt_sha256 }, null, 2)}</pre></details>
  </section>;
}

export function NormativeContext({ policy, receipts }: { readonly policy: unknown; readonly receipts: unknown }) {
  const [expanded, setExpanded] = useState(false);
  const [page, setPage] = useState(0);
  const accepted = object(policy);
  if (accepted === null) return null;
  const records = objects(receipts);
  const pages = Math.max(1, Math.ceil(records.length / 10));
  const current = Math.min(page, pages - 1);
  return <section id="extended-normative-context" className={styles.batchPanel} aria-label="Контекст нормативных цитат">
    <h3>Контекст нормативных цитат</h3>
    <p>Модель получает исходный абзац и соседний текст нашего корпуса: до {count(accepted.max_paragraphs)} контекстов и {count(accepted.max_characters)} символов в одном уже запланированном нормативном запросе. Сокращения и недоступные абзацы показаны явно. Новые модельные шаги ради контекста не добавляются.</p>
    <p>Подготовлено запросов с контекстом: {records.length}; сохранён ответ: {records.filter((row) => row.response_received === true).length}. Подготовка запроса не означает получение ответа или проверку каждого переданного положения.</p>
    <p>Цитаты остаются привязанными к своему наблюдению. Соседние абзацы не становятся новыми нормативными основаниями. Актуальность редакции и применимость требуют экспертной сверки.</p>
    <details onToggle={(event) => setExpanded(event.currentTarget.open)}><summary>Показать фактически подготовленный контекст</summary>{expanded ? <>
      {records.length === 0 ? <p>Квитанции ещё не сохранены; завершение нормативной процедуры этим не подтверждено.</p> : <ol className={styles.batchList} start={current * 10 + 1}>{records.slice(current * 10, (current + 1) * 10).map((receipt, index) => {
        const context = object(receipt.context);
        return <li key={`${text(receipt.window_id)}:${text(receipt.batch_index)}:${index}`}>
          <h4>Окно {text(receipt.window_id)} · {receipt.response_received === true ? 'ответ сохранён' : 'запрос подготовлен, ответ не подтверждён'}</h4>
          <p>Контекстов предоставлено {count(receipt.contexts_provided)} из {count(receipt.candidate_quote_contexts)}; не предоставлено {count(receipt.contexts_not_provided)}.</p>
          {objects(context?.paragraphs).map((entry, ordinal) => <details key={`${text(entry.paragraph_id)}:${ordinal}`}>
            <summary>{text(entry.title) || 'Нормативный документ'} · {text(entry.paragraph_id)}</summary>
            {text(entry.document_id) ? <Link href={routes.normDocument(text(entry.document_id))}>Открыть документ нормы</Link> : null}
            <p>{entry.search_quote_literal_in_paragraph === true ? 'Поисковая цитата дословно найдена в исходном абзаце.' : 'Поисковая цитата не совпала с непрерывным текстом абзаца; самостоятельное нормативное подтверждение отсутствует.'}</p>
            <Paragraph value={entry.primary} />
            <details><summary>Соседние абзацы — только контекст</summary>{objects(entry.neighbors).map((neighbor, neighborIndex) => <Paragraph key={`${text(neighbor.paragraph_id)}:${neighborIndex}`} value={neighbor} />)}</details>
          </details>)}
          <details><summary>Полная квитанция, собственные цитаты входов и ограничения</summary><pre>{JSON.stringify(receipt, null, 2)}</pre></details>
        </li>;
      })}</ol>}
      {records.length > 10 ? <nav className={styles.toolbar} aria-label="Страницы нормативного контекста"><button type="button" className="am-button am-button--quiet" disabled={current === 0} onClick={() => setPage(current - 1)}>Предыдущие</button><span>{current + 1} из {pages}</span><button type="button" className="am-button am-button--quiet" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}>Следующие</button></nav> : null}
    </> : null}</details>
    <p>Полные квитанции доступны в MD, HTML, JSON и техническом XLSX независимо от страницы списка.</p>
  </section>;
}
