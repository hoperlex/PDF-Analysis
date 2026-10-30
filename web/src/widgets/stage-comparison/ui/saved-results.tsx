'use client';

import { useMemo, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { RunStatus, VersionUid } from '@/shared/api';
import { formatInstant, routes } from '@/shared/lib';
import { LoadingState } from '@/shared/ui';
import { readSavedResult, SavedResultReadError } from '../api/read-saved-results';
import { compareSavedResults, hasSavedPreliminary, savedObject, savedResultPages, savedResultText } from '../model/saved-results';
import type { SavedResultRow, SavedResultSide } from '../model/saved-results';
import { SAVED_COMPARISON_LABELS, savedResultsReport } from '../model/saved-results-report';
import styles from './stage-comparison.module.css';

function RecordSide({ row, side }: { readonly row: SavedResultRow['left']; readonly side: SavedResultSide }) {
  if (row === null) return <span>Нет сопоставленной записи.</span>;
  const pages = savedResultPages(row, side);
  const observation = savedObject(row.observation);
  return <div>
    <p className={styles.savedText}>{savedResultText(row)}</p>
    {pages.length > 0 ? <p>Физические страницы PDF: {pages.join(', ')}.</p> : <p>Привязка к странице не передана.</p>}
    {observation !== null && typeof observation.recommendation_text === 'string' && observation.recommendation_text ? <p className={styles.savedText}>Рекомендация: {observation.recommendation_text}</p> : null}
    <a href={`${routes.run(side.run.project_uid, side.run.run_id)}#${observation === null ? 'extended-analysis' : 'findings'}`}>Открыть прогон и источники</a>
    <details><summary>Исходная запись и полученные оценки</summary><pre className={styles.savedRaw}>{JSON.stringify(row, null, 2)}</pre></details>
  </div>;
}
function SourceStatus({ side, label }: { readonly side: SavedResultSide; readonly label: string }) {
  const result = savedObject(side.extended?.result);
  const count = hasSavedPreliminary(side) && Array.isArray(result?.observations) ? result.observations.length : null;
  return <p>{label}: {side.findings === null ? 'публикация находок не подтверждена' : `получено находок ${side.findings.length}`}; {count === null
    ? 'предварительные наблюдения недоступны или не были сохранены' : `получено предварительных наблюдений ${count}`}{side.extended?.status === 'partial' || side.extended?.status === 'failed' ? '; расширенный анализ неполон или завершился с ошибкой' : ''}. Получено: {formatInstant(side.receivedAt)}.</p>;
}

export function SavedResultsComparison({ versionUid, left, right }: {
  readonly versionUid: VersionUid; readonly left: RunStatus; readonly right: RunStatus;
}) {
  const [requested, setRequested] = useState(false);
  const [progress, setProgress] = useState({ left: 0, right: 0 });
  const [filter, setFilter] = useState('all');
  const [page, setPage] = useState(0);
  const [downloadError, setDownloadError] = useState<string | null>(null);
  const client = useQueryClient();
  const key = ['saved-run-result-comparison', versionUid, left.run_id, right.run_id] as const;
  const terminal = [left, right].every((run) => ['published', 'partial', 'failed', 'cancelled'].includes(run.state));
  const comparable = terminal && left.run_id !== right.run_id;
  const query = useQuery({ queryKey: key, enabled: requested && comparable,
    queryFn: async ({ signal }) => {
      const controller = new AbortController();
      const cancel = () => controller.abort();
      signal.addEventListener('abort', cancel, { once: true });
      if (signal.aborted) cancel();
      try {
        return await Promise.all([
          readSavedResult(left.run_id, versionUid, controller.signal, (received) => setProgress((current) => ({ ...current, left: received }))),
          readSavedResult(right.run_id, versionUid, controller.signal, (received) => setProgress((current) => ({ ...current, right: received }))),
        ]);
      } finally { controller.abort(); signal.removeEventListener('abort', cancel); }
    }, retry: false, staleTime: Infinity });
  const rows = useMemo(() => query.data === undefined ? [] : compareSavedResults(query.data[0]!, query.data[1]!), [query.data]);
  const filtered = rows.filter((row) => filter === 'all' || (filter === 'differences' ? row.comparison !== 'same' : row.kind === filter));
  const pages = Math.max(1, Math.ceil(filtered.length / 25));
  const current = Math.min(page, pages - 1);
  const start = () => { setRequested(true); setProgress({ left: 0, right: 0 }); if (requested) void query.refetch(); };
  const download = (format: 'json' | 'csv' | 'html') => {
    if (query.data === undefined) return;
    setDownloadError(null);
    try {
      const report = savedResultsReport(query.data[0]!, query.data[1]!, rows, format);
      const url = URL.createObjectURL(new Blob([report.content], { type: report.mediaType }));
      try { const link = document.createElement('a'); link.href = url; link.download = report.name; link.rel = 'noopener'; document.body.appendChild(link); link.click(); link.remove(); }
      finally { URL.revokeObjectURL(url); }
    } catch (error) { setDownloadError(error instanceof Error ? error.message : 'Не удалось сформировать выгрузку.'); }
  };
  return <section className={styles.savedPanel} aria-label="Сравнение сохранённых результатов">
    <h3>Находки и предварительные наблюдения</h3>
    <p>Сравните сохранённые результаты выбранных прогонов без новых обращений к модели. Разница относится к анализу одной версии; запись только с одной стороны не означает исправление документа.</p>
    {!terminal ? <p>Для чтения итоговых результатов дождитесь завершения обоих прогонов.</p> : null}
    {left.run_id === right.run_id ? <p>Выберите два разных прогона для сопоставления результатов.</p> : null}
    <div className={styles.choosers}>
      <button type="button" className="am-button" disabled={!comparable || query.isFetching} onClick={start}>{query.data === undefined ? 'Сравнить сохранённые результаты' : 'Перечитать результаты'}</button>
      {query.isFetching ? <button type="button" className="am-button am-button--quiet" onClick={() => { setRequested(false); void client.cancelQueries({ queryKey: key, exact: true }); }}>Отменить чтение</button> : null}
    </div>
    {query.isFetching ? <><LoadingState what="сохранённые результаты двух прогонов" /><p role="status">Получено находок: слева {progress.left}, справа {progress.right}.</p></> : null}
    {query.isError ? <p role="alert">{query.error instanceof SavedResultReadError ? query.error.message : 'Не удалось прочитать оба результата. Сравнение по неполным данным не построено; повторите чтение.'}</p> : null}
    {query.data === undefined ? null : <>
      <SourceStatus side={query.data[0]!} label="Слева" /><SourceStatus side={query.data[1]!} label="Справа" />
      <p>Находки сопоставляются по устойчивой идентичности. Предварительные наблюдения — по точному тексту и источникам, с сохранением повторов. Похожие формулировки могут остаться отдельными. Экспертные состояния в исходных записях отражают момент чтения, а не историческое решение для каждой даты запуска.</p>
      <label>Показать <select value={filter} onChange={(event) => { setFilter(event.target.value); setPage(0); }}><option value="all">Все записи</option><option value="differences">Различия</option><option value="finding">Канонические находки</option><option value="preliminary">Предварительные наблюдения</option></select></label>
      <p>По фильтру {filtered.length} из {rows.length} записей. Выгрузка включает весь полученный набор.</p>
      {filtered.length === 0 ? <p>В доступных для сопоставления данных нет записей выбранного вида. Недоступные результаты не считались пустыми.</p> : <ol className={styles.savedRows} start={current * 25 + 1}>{filtered.slice(current * 25, (current + 1) * 25).map((row) => <li key={row.key}>
        <h4>{row.kind === 'finding' ? 'Каноническая находка' : 'Предварительное наблюдение'} · {SAVED_COMPARISON_LABELS[row.comparison]}</h4>
        <div className={styles.savedSides}><section aria-label="Запись слева"><h5>Слева</h5><RecordSide row={row.left} side={query.data![0]!} /></section><section aria-label="Запись справа"><h5>Справа</h5><RecordSide row={row.right} side={query.data![1]!} /></section></div>
      </li>)}</ol>}
      {filtered.length > 25 ? <nav className={styles.choosers} aria-label="Страницы сравнения результатов"><button type="button" className="am-button am-button--quiet" disabled={current === 0} onClick={() => setPage(current - 1)}>Назад</button><span>{current + 1} из {pages}</span><button type="button" className="am-button am-button--quiet" disabled={current + 1 >= pages} onClick={() => setPage(current + 1)}>Далее</button></nav> : null}
      <div className={styles.choosers}><button type="button" className="am-button am-button--quiet" onClick={() => download('json')}>Все данные JSON</button><button type="button" className="am-button am-button--quiet" onClick={() => download('csv')}>Сравнение CSV</button><button type="button" className="am-button am-button--quiet" onClick={() => download('html')}>Полный отчёт HTML</button></div>
      {downloadError === null ? null : <p role="alert">{downloadError}</p>}
    </>}
  </section>;
}
