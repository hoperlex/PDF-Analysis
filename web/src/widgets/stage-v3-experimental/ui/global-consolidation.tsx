'use client';

import { useState } from 'react';
import { GLOBAL_DECISION_WORDS as DECISION, VERIFICATION_WORDS, object, string } from '../model/report';
import type { JsonObject } from '../model/report';
import styles from './global-consolidation.module.css';

function objects(value: unknown): JsonObject[] { return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : []; }
function strings(value: unknown): string[] { return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
function display(value: unknown): string { return typeof value === 'string' ? value : value === undefined ? 'Не передано' : JSON.stringify(value, null, 2) ?? 'Не передано'; }
function recordId(record: JsonObject): string { return string(record.event_id) || string(record.projectchange_id) || string(record.work_item_id) || string(record.parameter_id) || string(record.hint_id); }

function SavedRecord({ value, label = 'Полная сохранённая запись' }: { readonly value: unknown; readonly label?: string }) {
  const [open, setOpen] = useState(false);
  return <details onToggle={(event) => setOpen(event.currentTarget.open)}><summary>{label}</summary>{open ? <pre>{JSON.stringify(value, null, 2)}</pre> : null}</details>;
}

function OriginalRecords({ records, title }: { readonly records: readonly JsonObject[]; readonly title: string }) {
  const [page, setPage] = useState(0);
  const pages = Math.max(1, Math.ceil(records.length / 25));
  const current = Math.min(page, pages - 1);
  return <section aria-label={title}><h5>{title} · {records.length}</h5><p>Показано до 25 записей. Все исходные данные включены в JSON и технические выгрузки.</p>
    <ol start={current * 25 + 1}>{records.slice(current * 25, (current + 1) * 25).map((record, index) => <li key={`${recordId(record)}:${index}`}>
      <strong>{string(record.engineering_subject) || string(record.title) || string(record.parameter_name) || recordId(record) || 'Сохранённая запись'}</strong>
      {string(record.change_summary) || string(record.description) ? <p>{string(record.change_summary) || string(record.description)}</p> : null}
      <SavedRecord value={record} />
    </li>)}</ol>
    {records.length > 25 ? <nav className={styles.row} aria-label={`Страницы: ${title}`}><button type="button" className="am-button" disabled={current === 0} onClick={() => setPage(current - 1)}>Предыдущие записи</button><span>{current + 1} из {pages}</span><button type="button" className="am-button" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}>Следующие записи</button></nav> : null}
  </section>;
}

export function StageCardOriginalEvents({ experimental }: { readonly experimental: unknown }) {
  const body = object(experimental);
  const originals = objects(body?.original_events);
  const hints = objects(body?.original_hints);
  const grouping = object(body?.global_consolidation);
  const [open, setOpen] = useState(false);
  if (grouping === null && originals.length === 0 && hints.length === 0) return null;
  return <details className={styles.panel} onToggle={(event) => setOpen(event.currentTarget.open)} data-v3-original-events=""><summary>Исходные события межпакетной группы · {originals.length}</summary>
    {open ? <><p>Исходные события и отдельные машинные сверки сохранены. Группировка не является решением эксперта.</p><p>Группы: {strings(grouping?.group_ids).join(', ') || 'Не переданы'}.</p><OriginalRecords records={originals} title="Исходные события карточки" /><OriginalRecords records={hints} title="Исходные классификации карточки" /><SavedRecord value={grouping} label="Происхождение группировки карточки" /></> : null}
  </details>;
}

export function StageGlobalConsolidation({ value }: { readonly value: unknown }) {
  const body = object(value);
  const [tab, setTab] = useState('groups');
  const [page, setPage] = useState(0);
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  if (body === null) return null;
  const coverage = object(body.coverage);
  const groups = objects(body.groups);
  const decisions = objects(body.decisions);
  const events = objects(body.original_events);
  const hints = objects(body.original_hints);
  const verifications = objects(body.parameter_verifications);
  const eventIndex = new Map(events.map((event) => [string(event.projectchange_id) || string(event.event_id), event] as const));
  const records = tab === 'groups' ? groups : tab === 'decisions' ? decisions : tab === 'events' ? events : tab === 'hints' ? hints : verifications;
  const pages = Math.max(1, Math.ceil(records.length / 25));
  const current = Math.min(page, pages - 1);
  return <section id="stage-v3-global-consolidation" className={styles.panel} aria-label="Межпакетное объединение Stage V3" data-v3-global-consolidation="">
    <h3>Межпакетная сверка событий</h3>
    <p>Сохранённые модельные рекомендации и применённые правила группировки показаны отдельно. Конфликтующие значения и исходные машинные сверки не заменяются общим решением; решение принимает эксперт.</p>
    <dl className={styles.coverage}><div><dt>Кандидатных пар</dt><dd>{count(coverage?.candidate_pairs)}</dd></div><div><dt>Пар в плане</dt><dd>{count(coverage?.planned_pairs)}</dd></div><div><dt>Сравнено пар</dt><dd>{count(coverage?.compared_pairs)}</dd></div><div><dt>Не сравнено пар</dt><dd>{count(coverage?.not_compared_pairs)}</dd></div></dl>
    {coverage?.global_semantic_complete === false ? <p>Глобальная смысловая полнота не подтверждена. Поиск ограничен сохранённым набором кандидатных пар.</p> : null}
    <details><summary>Происхождение межпакетной сверки</summary><p>Версия: <code>{string(body.version)}</code>. Манифест SHA256: <code>{string(body.manifest_sha256)}</code>.</p></details>
    <div className={styles.row} role="group" aria-label="Сохранённые данные межпакетной сверки">{[['groups', `Группы · ${groups.length}`], ['decisions', `Рекомендации · ${decisions.length}`], ['events', `Исходные события · ${events.length}`], ['hints', `Исходные классификации · ${hints.length}`], ['verifications', `Машинные сверки параметров · ${verifications.length}`]].map(([key, label]) => <button type="button" className="am-button" key={key} aria-pressed={tab === key} onClick={() => { setTab(key ?? 'groups'); setPage(0); setOpenGroup(null); }}>{label}</button>)}</div>
    {records.length === 0 ? <p>Записи этого вида не переданы.</p> : <ol start={current * 25 + 1}>{records.slice(current * 25, (current + 1) * 25).map((record, index) => <li key={string(record.group_id) || string(record.pair_id) || `${tab}:${index}`}>
      {tab === 'groups' ? <><p>Группа <code>{string(record.group_id)}</code> · событий: {strings(record.event_ids).length}.</p><p>События: {strings(record.event_ids).join(', ') || 'Не переданы'}.</p><button type="button" className="am-button" onClick={() => setOpenGroup(openGroup === string(record.group_id) ? null : string(record.group_id))}>Показать исходные события группы</button>{openGroup === string(record.group_id) ? <><OriginalRecords records={strings(record.event_ids).flatMap((id) => { const event = eventIndex.get(id); return event === undefined ? [] : [event]; })} title="Исходные события выбранной группы" />{strings(record.event_ids).some((id) => !eventIndex.has(id)) ? <p>Некоторые исходные события отсутствуют в этом каталоге; их идентификаторы сохранены, данные не подменяются.</p> : null}</> : null}</> : tab === 'decisions' ? <>
        <p>Пара <code>{string(record.pair_id)}</code> · события: {strings(record.event_ids).join(', ') || 'Не переданы'}.</p>
        <p>Рекомендация модели: <strong>{DECISION[string(record.model_decision)] ?? 'Требует проверки'}</strong>. Применение к группировке: <strong>{DECISION[string(record.applied_decision)] ?? 'Не передано'}</strong>.</p>
        {string(record.reason) ? <p>{string(record.reason)}</p> : null}
        {typeof record.typed_conflict_count === 'number' ? <p>Зафиксировано конфликтов значений: {count(record.typed_conflict_count)}.</p> : null}
        {record.typed_conflicts_truncated === true ? <p>Показан сокращённый перечень конфликтов. Полные исходные значения и отдельные сверки сохранены в исходных событиях и каталоге машинных сверок.</p> : null}
        {objects(record.typed_conflicts).length > 0 ? <ul>{objects(record.typed_conflicts).map((conflict, number) => <li key={number}>Параметр {display(conflict.parameter_key)}: {display(conflict.left)} ↔ {display(conflict.right)}.</li>)}</ul> : null}
        {objects(record.source_evidence).length > 0 ? <details><summary>Указанные моделью источники и цитаты</summary><ul>{objects(record.source_evidence).map((source, number) => <li key={number}><code>{string(source.source_id) || string(source.event_id)}</code><blockquote>{string(source.quote)}</blockquote></li>)}</ul></details> : null}
      </> : <><strong>{string(record.engineering_subject) || string(record.title) || string(record.parameter_name) || recordId(record) || 'Сохранённая запись'}</strong>{string(record.change_summary) || string(record.description) ? <p>{string(record.change_summary) || string(record.description)}</p> : null}{tab === 'verifications' ? <p>Машинная сверка: {VERIFICATION_WORDS[string(object(record.result)?.verdict)] ?? 'Результат сверки не передан'} · событие <code>{string(record.projectchange_id) || string(record.event_id)}</code>.</p> : null}</>}
      <SavedRecord value={record} />
    </li>)}</ol>}
    {records.length > 25 ? <nav className={styles.row} aria-label="Страницы межпакетной сверки"><button type="button" className="am-button" disabled={current === 0} onClick={() => setPage(current - 1)}>Предыдущие 25</button><span>{current + 1} из {pages}</span><button type="button" className="am-button" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}>Следующие 25</button></nav> : null}
  </section>;
}
