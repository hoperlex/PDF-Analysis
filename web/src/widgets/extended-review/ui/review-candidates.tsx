'use client';

import { Fragment, useMemo, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import type { Finding } from '@/shared/api';
import { getExtendedRunReview } from '@/shared/api';
import { CATEGORY_LABELS } from '@/entities/expert-decision';
import { SEVERITY_LABELS } from '@/entities/finding';
import { routes } from '@/shared/lib';
import { candidateText as text, PROPOSAL_SEVERITIES, reviewCandidates } from '../model/review-candidates';
import type { CandidateRecord, ReviewCandidate } from '../model/review-candidates';
import { MachineAdvice } from './machine-advice';
import { ReviewWarnings } from './review-warnings';
import { SourceInspector, sourceKind, sourcePage } from './source-inspector';
import styles from './review-candidates.module.css';

const ORIGIN = { text: 'Текст', drawing: 'Чертёж', cross_check: 'Сверка', unknown: 'Источник не сохранён' };
const titleOf = (title: string) => (CATEGORY_LABELS as Readonly<Record<string, string>>)[title] ?? title;

function pagesLabel(pages: readonly number[], sheetOf?: ((page: number) => number | undefined) | undefined): string {
  const sheets = [...new Set(pages.flatMap((page) => { const sheet = sheetOf?.(page); return sheet === undefined ? [] : [sheet]; }))];
  return `${sheets.length ? `Лист ${sheets.join(', ')} · ` : ''}стр. ${pages.join(', ')}`;
}

function CandidateDetail({ row, versionUid, projectUid }: { readonly row: ReviewCandidate; readonly versionUid: string; readonly projectUid: string }) {
  const [selected, setSelected] = useState<CandidateRecord | null>(null);
  return <div className={styles.detail}>
    <div className={styles.sources} aria-label="Источники кандидата">
      {row.sources.map((source) => <button key={text(source.source_id)} type="button" className="am-button am-button--quiet am-button--small"
        onClick={() => setSelected(source)}>Стр. {sourcePage(source) ?? '—'} · {sourceKind(source)}</button>)}
    </div>
    {row.missingSources.length === 0 ? null : <p role="status">Часть исходных материалов отсутствует в сохранённой записи.</p>}
    {selected === null ? null : <SourceInspector source={selected} fallbackVersion={versionUid} projectUid={projectUid} onClose={() => setSelected(null)} />}
    {row.members.map((item, index) => <details key={`${text(item.observation_id)}:${index}`} className={styles.member}>
      <summary>{row.members.length > 1 ? `Исходное наблюдение ${index + 1} и проверка критика` : 'Исходное наблюдение и проверка критика'}</summary>
      <p>{text(item.description)}</p>
      <MachineAdvice review={item.review ?? item.critic} correction={item.correction} reviewStatus={item.review_status} reviewReason={item.review_reason} />
    </details>)}
  </div>;
}

export function ReviewCandidateTable({ value, projectUid, published = [], sheetOf }: {
  readonly value: unknown; readonly projectUid: string; readonly published?: readonly Finding[];
  readonly sheetOf?: ((page: number) => number | undefined) | undefined;
}) {
  const reading = useMemo(() => reviewCandidates(value, published), [value, published]);
  const [search, setSearch] = useState('');
  const [severity, setSeverity] = useState('all');
  const [origin, setOrigin] = useState('all');
  const [page, setPage] = useState(0);
  const [opened, setOpened] = useState<string | null>(null);
  const result = typeof value === 'object' && value !== null ? value as CandidateRecord : {};
  const needle = search.trim().toLocaleLowerCase('ru');
  const matches = reading.rows.filter((row) => (severity === 'all' || (row.severity ?? 'undetermined') === severity)
    && (origin === 'all' || row.origin === origin)
    && (!needle || `${row.title} ${row.description} ${row.recommendations.join(' ')}`.toLocaleLowerCase('ru').includes(needle)));
  const current = Math.min(page, Math.max(0, Math.ceil(matches.length / 25) - 1));
  const shown = matches.slice(current * 25, (current + 1) * 25);
  if (reading.rows.length === 0) return null;
  const changeSeverity = (next: string) => { setSeverity(next); setPage(0); };
  return <section id="review-machine-candidates" className={styles.root} aria-label="Машинные кандидаты — только просмотр" data-review-candidates={reading.rows.length}>
    <div className={styles.heading}><h2>Машинные кандидаты <span>{reading.rows.length}</span></h2><span className={styles.readonly}>Только просмотр</span></div>
    <p className={styles.note}>Сохранённые машинные наблюдения. Решения ✓/✕ доступны у находок выше. Эти строки не меняют число находок и экспертных решений.</p>
    <p className={styles.note}>Исходных наблюдений: {reading.rawCount} · групп: {reading.groupCount}{reading.publishedGroups ? ` · уже в находках: ${reading.publishedGroups}` : ''}.</p>
    {reading.groupingIncomplete ? <p role="status">Группировка неполна; показаны все исходные наблюдения.</p> : null}
    <ReviewWarnings warnings={result.warnings} />
    <div className={styles.chips} role="group" aria-label="Важность кандидатов, предложенная моделью">
      <span>Предложено моделью:</span>
      <button type="button" className="am-button am-button--quiet am-button--small" aria-pressed={severity === 'all'} onClick={() => changeSeverity('all')}>Все {reading.rows.length}</button>
      {PROPOSAL_SEVERITIES.filter((key) => reading.rows.some((row) => row.severity === key)).map((key) => <button type="button" key={key}
        className="am-button am-button--quiet am-button--small" aria-pressed={severity === key} data-candidate-filter={key} onClick={() => changeSeverity(key)}>{SEVERITY_LABELS[key]} {reading.rows.filter((row) => row.severity === key).length}</button>)}
      {reading.rows.some((row) => row.severity === undefined) ? <button type="button" className="am-button am-button--quiet am-button--small"
        aria-pressed={severity === 'undetermined'} onClick={() => changeSeverity('undetermined')}>Не определена {reading.rows.filter((row) => row.severity === undefined).length}</button> : null}
    </div>
    <div className={styles.filters}><label>Поиск замечания<input type="search" value={search} onChange={(event) => { setSearch(event.target.value); setPage(0); }} /></label>
      <label>Источник<select value={origin} onChange={(event) => { setOrigin(event.target.value); setPage(0); }}><option value="all">Все источники</option><option value="drawing">Чертёж</option><option value="text">Текст</option><option value="cross_check">Сверка</option></select></label></div>
    <p className={styles.note} aria-live="polite">Показано {shown.length ? current * 25 + 1 : 0}–{current * 25 + shown.length} из {matches.length}.</p>
    <div className={styles.scroll}><table className={styles.table} aria-label="Таблица машинных кандидатов"><thead><tr>
      {['№', 'Важность', 'Лист / стр.', 'Замечание', 'Норма', 'Рекомендация', 'Решение'].map((label) => <th key={label} scope="col">{label}</th>)}
    </tr></thead><tbody>{shown.map((row) => <Fragment key={row.key}><tr data-candidate-row={row.key}>
      <td><button type="button" className="am-button am-button--quiet am-button--small" aria-expanded={opened === row.key}
        aria-label={`Открыть источники кандидата ${row.number}`} onClick={() => setOpened(opened === row.key ? null : row.key)}>К-{String(row.number).padStart(3, '0')}</button>{row.members.length > 1 ? <small>×{row.members.length}</small> : null}</td>
      <td>{row.severity === undefined ? <span className={styles.note}>Не определена</span> : <span data-candidate-proposed-severity={row.severity}>{SEVERITY_LABELS[row.severity]}<small>предложено моделью</small></span>}</td>
      <td>{row.pages.length ? pagesLabel(row.pages, sheetOf) : 'Страница не указана'}</td>
      <td><span className={styles.origin}>{ORIGIN[row.origin]}</span><strong>{titleOf(row.title)}</strong><p>{row.description}</p></td>
      <td>{row.norms.length === 0 ? <span className={styles.note}>Основание не подтверждено</span> : row.norms.map((norm, index) => <div key={`${text(norm.paragraph_id)}:${index}`} className={styles.norm}>
        <strong>{text(norm.designation) || 'Нормативный кандидат'}</strong>{text(norm.clause_number) ? <span>п. {text(norm.clause_number)}</span> : null}<small>не подтверждено</small>
        {text(norm.quote) ? <blockquote>{text(norm.quote)}</blockquote> : null}{text(norm.document_id) ? <Link href={routes.normDocument(text(norm.document_id))}>Открыть норму</Link> : null}
      </div>)}</td>
      <td>{row.recommendations.length === 0 ? <span className={styles.note}>В этом прогоне отдельно не сохранена</span> : row.recommendations.map((recommendation) => <p key={recommendation}>{recommendation}</p>)}</td>
      <td><span className={styles.readonly}>Только просмотр</span></td>
    </tr>{opened === row.key ? <tr><td colSpan={7}><CandidateDetail row={row} versionUid={text(result.version_uid)} projectUid={projectUid} /></td></tr> : null}</Fragment>)}</tbody></table></div>
    {matches.length === 0 ? <p>Под выбранные фильтры кандидаты не попали.</p> : null}
    {matches.length > 25 ? <nav className={styles.chips} aria-label="Страницы машинных кандидатов"><button type="button" className="am-button am-button--quiet" disabled={current === 0} onClick={() => setPage(current - 1)}>Предыдущие</button><span>{current + 1} / {Math.ceil(matches.length / 25)}</span><button type="button" className="am-button am-button--quiet" disabled={(current + 1) * 25 >= matches.length} onClick={() => setPage(current + 1)}>Следующие</button></nav> : null}
  </section>;
}

export function ReviewCandidates({ runId, ...props }: Omit<Parameters<typeof ReviewCandidateTable>[0], 'value'> & { readonly runId: string }) {
  const query = useQuery({ queryKey: ['extended-run-review', runId],
    queryFn: async () => (await getExtendedRunReview({ path: { run_id: runId } })).data, retry: false });
  if (query.isError) return <p role="status">Не удалось загрузить машинные кандидаты. <button type="button" className="am-button am-button--quiet" onClick={() => { void query.refetch(); }}>Повторить</button></p>;
  if (query.isPending) return <p role="status">Загружаются машинные кандидаты…</p>;
  return <ReviewCandidateTable {...props} value={query.data?.result} />;
}
