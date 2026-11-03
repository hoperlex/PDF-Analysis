'use client';

import { useState } from 'react';
import { SourceInspector } from './source-inspector';
import styles from './extended-review.module.css';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function objects(value: unknown): RecordValue[] { return Array.isArray(value) ? value.flatMap((entry) => { const row = object(entry); return row === null ? [] : [row]; }) : []; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function count(value: unknown): string { return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? String(value) : '—'; }
const TYPE: Readonly<Record<string, string>> = { object_type: 'Тип объекта', storeys: 'Этажность', area: 'Площади', level: 'Отметки', dimensions: 'Размеры',
  loads: 'Нагрузки и мощности', flows: 'Расходы', temperature: 'Температуры', pressure: 'Давления', equipment: 'Оборудование', materials: 'Материалы', system: 'Системы', other: 'Другие параметры' };
const STATUS: Readonly<Record<string, string>> = { queued: 'Запланировано', running: 'Выполняется', completed: 'Завершено в рамках входного плана', partial: 'Частичный охват', failed: 'Ошибка извлечения', skipped: 'Пропущено', unavailable: 'Нет пригодного текстового источника' };

function ReviewParameterContext({ body }: { readonly body: RecordValue }) {
  const [expanded, setExpanded] = useState(false);
  const [page, setPage] = useState(0);
  const policy = object(body.review_context_policy);
  if (policy === null) return null;
  const receipts = objects(body.review_context_receipts);
  const pages = Math.max(1, Math.ceil(receipts.length / 10));
  const current = Math.min(page, pages - 1);
  const titles: Readonly<Record<string, string>> = { comprehensive_analysis: 'Комплексная сверка', finding_review: 'Машинная критика', finding_correction: 'Предложение исправления' };
  return <section aria-label="Параметры в комплексной сверке и критике">
    <h4>Параметры в комплексной сверке и критике</h4>
    <p>В существующие локальные и межоконные запросы может входить до {count(policy.max_facts)} полных кандидатов параметров, в пределах {count(policy.max_characters)} символов контекста. Эти предварительные значения помогают понять условия проекта; они не являются требованиями нормы или решениями эксперта.</p>
    <p>Подготовлено запросов: {receipts.length}; ответ сохранён: {receipts.filter((receipt) => receipt.response_received === true).length}. Подготовка контекста не подтверждает использование каждого значения моделью. Исходные источники и разрешённые ссылки ответа не расширяются.</p>
    <details onToggle={(event) => setExpanded(event.currentTarget.open)}><summary>Квитанции переданного контекста</summary>{expanded ? <>
      {receipts.length === 0 ? <p>Квитанции ещё не получены. Завершение процедур по этой записи не подтверждено.</p> : <ol className={styles.batchList} start={current * 10 + 1}>{receipts.slice(current * 10, (current + 1) * 10).map((receipt, index) => <li key={`${text(receipt.window_id)}:${text(receipt.phase_key)}:${index}`}>
        <h5>{titles[text(receipt.procedure)] ?? 'Процедура анализа'} · окно {text(receipt.window_id)}</h5>
        <p>{receipt.response_received === true ? 'Ответ сохранён' : 'Запрос подготовлен; наличие ответа не подтверждено'}. Передано кандидатов {count(receipt.facts_provided)} из {count(receipt.candidates_received)}; не передано {count(receipt.facts_not_provided)}.</p>
        <details><summary>Полный переданный контекст, ID и отпечатки</summary><pre>{JSON.stringify(receipt, null, 2)}</pre></details>
      </li>)}</ol>}
      {receipts.length > 10 ? <nav className={styles.toolbar} aria-label="Страницы контекста комплексной сверки"><button type="button" className="am-button am-button--quiet" disabled={current === 0} onClick={() => setPage(current - 1)}>Предыдущие</button><span>{current + 1} из {pages}</span><button type="button" className="am-button am-button--quiet" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}>Следующие</button></nav> : null}
    </> : null}</details>
  </section>;
}

export function ProjectParameters({ value, fallbackVersion, projectUid }: {
  readonly value: unknown; readonly fallbackVersion: string; readonly projectUid?: string;
}) {
  const [search, setSearch] = useState('');
  const [kind, setKind] = useState('all');
  const [page, setPage] = useState(0);
  const [source, setSource] = useState<RecordValue | null>(null);
  const [showContext, setShowContext] = useState(false);
  const [contextPage, setContextPage] = useState(0);
  const body = object(value);
  if (body === null) return null;
  const coverage = object(body.coverage);
  const policy = object(body.policy);
  const contextPolicy = object(body.visual_context_policy);
  const contextReceipts = objects(body.visual_context_receipts);
  const contextPages = Math.max(1, Math.ceil(contextReceipts.length / 25));
  const currentContextPage = Math.min(contextPage, contextPages - 1);
  const facts = objects(body.facts);
  const sources = new Map(objects(body.sources).map((entry) => [text(entry.source_id), entry] as const));
  const needle = search.trim().toLocaleLowerCase('ru');
  const filtered = facts.filter((fact) => (kind === 'all' || fact.parameter_type === kind) && (!needle ||
    [fact.fact_id, fact.name, fact.value, fact.unit, fact.subject].map(text).join('\n').toLocaleLowerCase('ru').includes(needle)));
  const pages = Math.max(1, Math.ceil(filtered.length / 25));
  const current = Math.min(page, pages - 1);
  return <section id="extended-project-parameters" className={styles.batchPanel} aria-label="Параметры проекта из источников">
    <h3>Параметры проекта из источников</h3>
    <p><strong>{STATUS[text(body.status)] ?? 'Состояние ещё не получено'}</strong>. Это предварительно извлечённые значения, а не утверждённый паспорт или проверка норм. Разные объекты и значения сохраняются отдельно; единицы не пересчитывались.</p>
    <p>Обращений по принятому плану: до {count(policy?.max_calls)} на весь прогон. Завершено: {count(coverage?.calls_completed)}. Сохранено кандидатов: {facts.length}.</p>
    {contextPolicy === null ? null : <section aria-label="Контекст параметров для изображений"><p>По принятой политике параметры подготавливаются перед визуальным проходом. В один запрос изображений может войти до {count(contextPolicy.max_facts)} полных кандидатов, в пределах {count(contextPolicy.max_characters)} символов контекста. Новые модельные шаги ради передачи контекста не добавляются.</p><p>Подготовлено квитанций контекста: {contextReceipts.length}; сохранён ответ на запрос: {contextReceipts.filter((receipt) => receipt.response_received === true).length}. Переданный контекст не является визуальным подтверждением или решением эксперта.</p><details onToggle={(event) => setShowContext(event.currentTarget.open)}><summary>Фактически подготовленный контекст и ответы</summary>{showContext ? <><p>Квитанции {currentContextPage + 1} из {contextPages}; до25 на странице. Все записи доступны в полной выгрузке.</p><pre>{JSON.stringify(contextReceipts.slice(currentContextPage * 25, (currentContextPage + 1) * 25), null, 2)}</pre>{contextReceipts.length > 25 ? <nav className={styles.toolbar} aria-label="Страницы визуального контекста"><button type="button" className="am-button am-button--quiet" disabled={currentContextPage === 0} onClick={() => setContextPage(currentContextPage - 1)}>Предыдущие</button><button type="button" className="am-button am-button--quiet" disabled={currentContextPage + 1 >= contextPages} onClick={() => setContextPage(currentContextPage + 1)}>Следующие</button></nav> : null}</> : null}</details></section>}
    <ReviewParameterContext body={body} />
    <dl className={styles.coverageGrid}>
      <div><dt>Известных фрагментов</dt><dd>{count(coverage?.pieces_total_known)}</dd></div>
      <div><dt>Отобрано фрагментов</dt><dd>{count(coverage?.pieces_selected)}</dd></div>
      <div><dt>Фрагментов вне отбора</dt><dd>{count(coverage?.pieces_not_selected)}</dd></div>
      <div><dt>Страниц в отборе</dt><dd>{count(coverage?.pages_selected)}</dd></div>
      <div><dt>Не прочитано записей источника</dt><dd>{count(coverage?.source_records_not_scanned)}</dd></div>
    </dl>
    {coverage?.selection_complete === false ? <p>Часть текста находится вне принятого или ресурсного окна. Отсутствие параметра в списке не доказывает его отсутствие в проекте.</p> : <p>Охват текста не доказывает полноту извлечённых параметров или полноту проекта. Неразобранные изображения не заменяются догадками.</p>}
    {body.pending_manifest_truncated === true || body.omitted_manifest_truncated === true ? <p>Список примеров пропусков ограничен. Полные известные счётчики и признаки ограничения приведены в сохранённом покрытии.</p> : null}
    {text(body.reason) ? <p>Сохранено ограничение или причина завершения; точный код доступен в записи плана ниже.</p> : null}
    <div className={styles.toolbar}><label>Поиск параметров<input value={search} onChange={(event) => { setSearch(event.target.value); setPage(0); }} /></label>
      <label>Вид параметра<select value={kind} onChange={(event) => { setKind(event.target.value); setPage(0); }}><option value="all">Все</option>{Object.entries(TYPE).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label>
      <p>По фильтру {filtered.length} из {facts.length}. Полные выгрузки сохраняют весь список.</p>
    </div>
    {source === null ? null : <SourceInspector key={text(source.source_id)} source={source} fallbackVersion={fallbackVersion} {...(projectUid === undefined ? {} : { projectUid })} onClose={() => setSource(null)} />}
    {filtered.length === 0 ? <p>В текущей записи нет параметров выбранного вида. Это не заключение об отсутствии данных проекта.</p> : <ol className={styles.batchList} start={current * 25 + 1}>{filtered.slice(current * 25, (current + 1) * 25).map((fact, index) => <li key={`${text(fact.fact_id)}:${current * 25 + index}`}>
      <h4>{text(fact.name)} · {TYPE[text(fact.parameter_type)] ?? 'Параметр источника'}</h4>
      <p><strong>{text(fact.value)} {text(fact.unit)}</strong></p>
      <p>Объект/предмет: {text(fact.subject) || 'Не указан в переданной цитате'}.</p>
      {objects(fact.source_evidence).map((evidence, ordinal) => { const candidate = sources.get(text(evidence.source_id)); return <div key={ordinal}>
        <blockquote>{text(evidence.quote)}</blockquote>
        {typeof evidence.page_number === 'number' ? <p>Физическая страница PDF: {evidence.page_number}. Символы отдельной записи: {count(evidence.character_start)}–{count(evidence.character_end)}; это не PDF-координаты.</p> : null}
        {candidate === undefined ? <p>Источник не передан для просмотра; адрес не выдумывается.</p> : <button type="button" className="am-button am-button--quiet" onClick={() => setSource(candidate)}>Открыть источник значения</button>}
      </div>; })}
      <details><summary>Полная исходная запись кандидата</summary><pre>{JSON.stringify(fact, null, 2)}</pre></details>
    </li>)}</ol>}
    {filtered.length > 25 ? <nav className={styles.toolbar} aria-label="Страницы параметров"><button type="button" className="am-button am-button--quiet" disabled={current === 0} onClick={() => setPage(current - 1)}>Предыдущие</button><span>{current + 1} из {pages}</span><button type="button" className="am-button am-button--quiet" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}>Следующие</button></nav> : null}
    <details><summary>Сохранённый план, квитанции и пропуски</summary><pre>{JSON.stringify({ version: body.version, policy: body.policy, source_sha256: body.source_sha256,
      manifest_sha256: body.manifest_sha256, coverage: body.coverage, batches: body.batches, pieces: body.pieces, pending: body.pending, omitted: body.omitted, reason: body.reason }, null, 2)}</pre></details>
    <p>MD, HTML, JSON и технический XLSX ниже содержат все сохранённые параметры и их источники. Просмотр и выгрузка не обращаются к модели.</p>
  </section>;
}
