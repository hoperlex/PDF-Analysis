'use client';

import { useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { routes } from '@/shared/lib';
import { MachineAdvice } from './machine-advice';
import { SourceInspector, sourceKind, sourcePage } from './source-inspector';
import styles from './extended-review.module.css';

type RecordValue = Record<string, unknown>;
function object(value: unknown): RecordValue | null { return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as RecordValue : null; }
function objects(value: unknown): RecordValue[] { return Array.isArray(value) ? value.flatMap((item) => { const row = object(item); return row === null ? [] : [row]; }) : []; }
function text(value: unknown): string { return typeof value === 'string' ? value : ''; }
function strings(value: unknown): string[] { return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []; }
const ASSESSMENT: Readonly<Record<string, string>> = { supports: 'Цитата предварительно поддерживает наблюдение', contradicts: 'Цитата предварительно противоречит наблюдению', insufficient: 'Цитаты недостаточно для вывода' };
const NORMS: Readonly<Record<string, string>> = { candidates: 'Есть кандидаты нормативных ссылок', not_found: 'Подходящие нормативные ссылки не найдены', unavailable: 'Нормативные основания не проверены или недоступны' };

export function ObservationList({ observations, sources, fallbackVersion, projectUid, anchorId = 'extended-observations' }: {
  readonly observations: readonly RecordValue[]; readonly sources: readonly RecordValue[]; readonly fallbackVersion: string; readonly projectUid?: string; readonly anchorId?: string;
}) {
  const [search, setSearch] = useState('');
  const [advice, setAdvice] = useState('all');
  const [correction, setCorrection] = useState('all');
  const [norm, setNorm] = useState('all');
  const [origin, setOrigin] = useState('all');
  const [pageSearch, setPageSearch] = useState('');
  const [pageSize, setPageSize] = useState(25);
  const [page, setPage] = useState(0);
  const [selectedSource, setSelectedSource] = useState<RecordValue | null>(null);
  const sourcePanel = useRef<HTMLDivElement>(null);
  const sourceIndex = useMemo(() => new Map(sources.flatMap((source) => text(source.source_id) ? [[text(source.source_id), source] as const] : [])), [sources]);
  const indexed = useMemo(() => observations.map((item, index) => {
    const critic = object(item.review ?? item.critic);
    const fixed = object(item.correction);
    const candidate = object(fixed?.candidate);
    const ids = strings(item.source_ids);
    const pages = [...new Set(ids.flatMap((id) => { const value = sourcePage(sourceIndex.get(id)); return value === null ? [] : [value]; }))];
    const searchable = [item.title, item.description, item.observation_id, item.cross_window_batch_key, ...strings(item.window_ids), critic?.explanation, candidate?.title, candidate?.description, ...ids].map(text).join('\n').toLocaleLowerCase('ru');
    return { item, index, critic, fixed, candidate, ids, pages, searchable };
  }), [observations, sourceIndex]);
  const requiredPage = /^[1-9]\d*$/.test(pageSearch.trim()) && Number.isSafeInteger(Number(pageSearch)) ? Number(pageSearch) : null;
  const invalidPage = pageSearch.trim() !== '' && requiredPage === null;
  const needle = search.trim().toLocaleLowerCase('ru');
  const matches = indexed.filter((row) => (!needle || row.searchable.includes(needle))
    && (advice === 'all' || (advice === 'not_reviewed' ? row.item.review_status === 'not_reviewed' : text(row.critic?.llm_decision) === advice))
    && (correction === 'all' || (correction === 'candidate' ? row.candidate !== null : correction === 'needs_context' ? row.fixed?.action === 'needs_context' : row.fixed === null))
    && (norm === 'all' || (norm === 'assessment' ? object(row.item.norm_assessment) !== null : norm === 'candidates' ? objects(row.item.norm_candidates).length > 0 : object(row.item.norm_assessment) === null))
    && (origin === 'all' || (origin === 'global' ? row.item.origin_scope === 'global_cross_window' : row.item.origin_scope !== 'global_cross_window'))
    && (requiredPage === null || row.pages.includes(requiredPage)));
  const pageCount = Math.max(1, Math.ceil(matches.length / pageSize));
  const currentPage = Math.min(page, pageCount - 1);
  const shown = matches.slice(currentPage * pageSize, (currentPage + 1) * pageSize);
  const reset = () => { setSearch(''); setAdvice('all'); setCorrection('all'); setNorm('all'); setOrigin('all'); setPageSearch(''); setPage(0); };
  const inspect = (source: RecordValue) => { setSelectedSource(source); sourcePanel.current?.scrollIntoView({ block: 'nearest' }); };
  return <section id={anchorId} aria-label="Кандидаты расширенного анализа" className={styles.candidatePanel}>
    <h3>Наблюдения и источники</h3>
    <p>Поиск и фильтры меняют только этот список. MD, HTML, JSON и технический XLSX сохраняют полную запись, включая скрытые фильтром наблюдения и исходные варианты.</p>
    <div className={styles.filters}>
      <label>Поиск по заголовку, описанию, рекомендации или источнику<input type="search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(0); }} /></label>
      <label>Рекомендация критика<select value={advice} onChange={(event) => { setAdvice(event.target.value); setPage(0); }}><option value="all">Все рекомендации</option><option value="not_reviewed">Критика не выполнялась</option><option value="accept">Рекомендует сохранить</option><option value="reject">Рекомендует снять</option><option value="borderline">Пограничный случай</option><option value="needs_human">Нужна проверка человека</option><option value="rewrite">Рекомендует уточнить</option></select></label>
      <label>Уточнение<select value={correction} onChange={(event) => { setCorrection(event.target.value); setPage(0); }}><option value="all">Все варианты</option><option value="candidate">Есть исправленный кандидат</option><option value="needs_context">Запрошен контекст</option><option value="none">Нет записи корректора</option></select></label>
      <label>Нормативные данные<select value={norm} onChange={(event) => { setNorm(event.target.value); setPage(0); }}><option value="all">Все состояния</option><option value="assessment">Есть модельная сверка цитат</option><option value="candidates">Есть кандидаты ссылок</option><option value="not_assessed">Нет модельной сверки цитат</option></select></label>
      <label>Происхождение наблюдения<select value={origin} onChange={(event) => { setOrigin(event.target.value); setPage(0); }}><option value="all">Все исходные записи</option><option value="global">Межоконная сверка</option><option value="other">Остальные исходные записи</option></select></label>
      <label>Физическая страница PDF<input type="number" min="1" step="1" value={pageSearch} aria-invalid={invalidPage} onChange={(event) => { setPageSearch(event.target.value); setPage(0); }} /></label>
      <label>На странице<select value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(0); }}><option value={25}>25</option><option value={50}>50</option><option value={100}>100</option></select></label>
    </div>
    {invalidPage ? <p role="status">Введите целый положительный номер физической страницы. Пока фильтр страницы не применяется.</p> : null}
    <div className={styles.toolbar}><p aria-live="polite">По фильтрам: <strong>{matches.length}</strong> из {observations.length}. Показано {shown.length === 0 ? 0 : currentPage * pageSize + 1}–{currentPage * pageSize + shown.length}.</p><button type="button" className="am-button am-button--quiet" onClick={reset}>Сбросить фильтры</button></div>
    <div ref={sourcePanel} id={`${anchorId}-source`}>{selectedSource === null ? null : <SourceInspector key={`${text(selectedSource.source_id)}:${text(selectedSource.version_uid) || fallbackVersion}`} source={selectedSource} fallbackVersion={fallbackVersion} {...(projectUid === undefined ? {} : { projectUid })} onClose={() => setSelectedSource(null)} />}</div>
    {observations.length === 0 ? <p>Предварительные наблюдения не получены. Это не подтверждает отсутствие проблем в документе.</p> : matches.length === 0 ? <p>Под выбранные фильтры записи не попали. Полный набор сохранён и доступен в выгрузках.</p> : <ol className={styles.observations} start={currentPage * pageSize + 1}>{shown.map(({ item, index, ids, pages }) => <li key={`${text(item.observation_id)}:${index}`} data-extended-observation={text(item.observation_id)}>
      <article>
        <div className={styles.toolbar}><h4>{text(item.title) || 'Наблюдение без заголовка'}</h4><span>{pages.length === 0 ? 'Страница не указана' : `Физические страницы: ${pages.join(', ')}`}</span></div>
        <p className={styles.description}>{text(item.description)}</p>
        {item.origin_scope === 'global_cross_window' ? <p data-cross-window-origin="">Межоконная сверка · пакет <code>{text(item.cross_window_batch_key) || 'Не передан'}</code> · исходные окна: {strings(item.window_ids).join(', ') || 'Не переданы'}.</p> : null}
        {objects(item.source_evidence).length > 0 ? <details><summary>Цитаты исходного наблюдения</summary><ul>{objects(item.source_evidence).map((evidence, number) => <li key={`${text(evidence.source_id)}:${number}`}><code>{text(evidence.source_id)}</code><blockquote>{text(evidence.quote)}</blockquote></li>)}</ul><p>Цитаты проверяются по указанным источникам; это не решение эксперта.</p></details> : null}
        <details><summary>Идентификаторы и происхождение</summary><p>Наблюдение: <code>{text(item.observation_id) || 'Не передано'}</code>. {text(item.window_id) ? <>Окно: <code>{text(item.window_id)}</code>.</> : null}</p><p>Источники: {ids.join(', ') || 'Не переданы'}.</p></details>
        <section aria-label="Источники кандидата"><h5>Проверить исходные материалы</h5>{ids.length === 0 ? <p>Идентификаторы исходных материалов не переданы.</p> : <ul className={styles.sourceButtons}>{ids.map((id) => {
          const source = sourceIndex.get(id);
          const sourceNumber = sourcePage(source);
          return <li key={id}>{source === undefined ? <span>Источник <code>{id}</code> отсутствует в этой записи; переход недоступен.</span> : <button type="button" className="am-button am-button--quiet" onClick={() => inspect(source)}>{sourceNumber === null ? 'Страница не указана' : `Стр. ${sourceNumber}`} · {sourceKind(source)}</button>}</li>;
        })}</ul>}</section>
        <details className={styles.adviceDetails} open={item.review_status === 'not_reviewed'}><summary>Машинная критика и предложенное уточнение</summary><MachineAdvice review={item.review ?? item.critic} correction={item.correction} reviewStatus={item.review_status} reviewReason={item.review_reason} />{object(item.review ?? item.critic) === null && object(item.correction) === null && item.review_status !== 'not_reviewed' ? <p>Записи критика и корректора пока не переданы. Это не означает одобрения наблюдения.</p> : null}</details>
        <details className={styles.adviceDetails}><summary>Нормативные основания · {NORMS[text(item.norm_status)] ?? 'Требуют проверки'}</summary>
          {object(item.norm_assessment) ? <aside data-norm-model-review="provisional"><strong>Модельная сверка по цитате</strong><p>{ASSESSMENT[text(object(item.norm_assessment)?.relation)] ?? 'Результат требует проверки'}</p><p>{text(object(item.norm_assessment)?.explanation)}</p><ul>{objects(object(item.norm_assessment)?.citations).map((citation, number) => <li key={text(citation.paragraph_id) || number}><code>{text(citation.paragraph_id)}</code><blockquote>{text(citation.quote)}</blockquote></li>)}</ul></aside> : <p>Модельная сверка нормативных цитат не передана.</p>}
          {objects(item.norm_candidates).map((candidate, number) => <section key={text(candidate.paragraph_id) || number}><h5>{text(candidate.designation) || 'Кандидат нормативного документа'}</h5>{text(candidate.document_id) ? <Link href={routes.normDocument(text(candidate.document_id))}>Открыть исходный документ нормы</Link> : null}<p>{text(candidate.clause_number) ? `Пункт ${text(candidate.clause_number)}. ` : ''}Страница документа нормы: {text(candidate.page_label) || (typeof candidate.page_label === 'number' ? candidate.page_label : 'Не передана')}.</p><blockquote>{text(candidate.quote)}</blockquote></section>)}
          <p>Действующая редакция, применимость и решение эксперта не подтверждены.</p>
        </details>
      </article>
    </li>)}</ol>}
    {matches.length > 0 ? <nav className={styles.toolbar} aria-label="Страницы списка кандидатов"><button type="button" className="am-button am-button--quiet" disabled={currentPage === 0} onClick={() => setPage(currentPage - 1)}>Предыдущие</button><span>Страница {currentPage + 1} из {pageCount}</span><button type="button" className="am-button am-button--quiet" disabled={currentPage + 1 >= pageCount} onClick={() => setPage(currentPage + 1)}>Следующие</button></nav> : null}
  </section>;
}
