'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

import type { StageCardEvidence, StageChainRun, StageChangeCard } from '@/shared/api';
import { browserDownloadSink, deliverDownload } from '@/features/export-run';
import { buildEvidencePackage } from '@/features/export-evidence-package';

import { object, parameterCsv, parameterRows, reportCoverage, reportHtml, reportSnapshot, reportSources, stageV3DisplayText, V3_ENGINE, VERIFICATION_WORDS, v3Cards } from '../model/report';
import type { V3Parameter, V3Source } from '../model/report';
import { formatStageV3Xlsx } from '../model/xlsx';
import { packageSources } from '../model/package';

type OpenEvidence = (evidence: StageCardEvidence, card: StageChangeCard) => void;

function SourceList({ sources, card, onOpenEvidence }: { readonly sources: readonly V3Source[];
  readonly card: StageChangeCard; readonly onOpenEvidence: OpenEvidence | undefined }) {
  return sources.length === 0 ? <p>Привязка к источникам не передана.</p> : <ul>{sources.map((source) => <li key={source.sourceId}>
    <span>{source.side === 'left' ? 'П' : source.side === 'right' ? 'Р' : 'Сторона не передана'}
      {source.pageNumber === null ? '' : ` · стр. ${source.pageNumber}`}</span>{' '}
    <code>{source.sourceId}</code>{' '}
    <button type="button" className="am-button" disabled={onOpenEvidence === undefined || source.anchor?.profile_id === undefined || card.stale}
      onClick={() => { if (onOpenEvidence !== undefined && source.anchor !== undefined) onOpenEvidence(source.anchor, card); }}>Открыть источник в PDF ↗</button>
    {source.quote === '' ? <p>Полная цитата в сохранённой карточке не передана.</p> : <blockquote style={{ whiteSpace: 'pre-wrap' }}>{source.quote}</blockquote>}
    {source.versionUid === '' ? null : <p>Версия: <code>{source.versionUid}</code></p>}
  </li>)}</ul>;
}

export function StageV3ParameterSources({ parameter, card, onOpenEvidence }: { readonly parameter: V3Parameter;
  readonly card: StageChangeCard; readonly onOpenEvidence: OpenEvidence | undefined }) {
  return <details data-stage-v3-parameter-sources="">
    <summary>Источники параметра</summary>
    {parameter.parameterId === '' ? <p>Идентификатор параметра в этой карточке не сохранён.</p>
      : <p>Параметр: <code>{parameter.parameterId}</code></p>}
    <p>Событие: <code>{parameter.eventId || 'Не передано'}</code></p>
    <h6>Источники машинной сверки</h6>
    <SourceList sources={parameter.verificationSources} card={card} onOpenEvidence={onOpenEvidence} />
    <h6>Источники события</h6>
    <p>Привязка события сама по себе не подтверждает каждое значение параметра.</p>
    <SourceList sources={parameter.eventSources} card={card} onOpenEvidence={onOpenEvidence} />
  </details>;
}

export function StageV3Report({ runId, cards, run, onOpenEvidence }: { readonly runId: string;
  readonly cards: readonly StageChangeCard[]; readonly run: StageChainRun | undefined;
  readonly onOpenEvidence: OpenEvidence }) {
  const [filter, setFilter] = useState('');
  const [parameterPage, setParameterPage] = useState(0);
  const [coveragePage, setCoveragePage] = useState(0);
  const [failure, setFailure] = useState<string | null>(null);
  const [packageBusy, setPackageBusy] = useState(false);
  const [packageCancelled, setPackageCancelled] = useState(false);
  const [packageProgress, setPackageProgress] = useState<{ readonly phase: 'preparing' | 'sources' | 'packaging'; readonly completed: number; readonly total: number } | null>(null);
  const packageAbort = useRef<AbortController | null>(null);
  useEffect(() => () => { packageAbort.current?.abort(); packageAbort.current = null; }, [runId]);
  const selected = useMemo(() => v3Cards(cards), [cards]);
  const parameters = useMemo(() => selected.flatMap((card) => parameterRows(card).map((parameter) => ({ card, parameter }))), [selected]);
  const sourceCount = useMemo(() => reportSources(cards, run).length, [cards, run]);
  const coverage = useMemo(() => reportCoverage(run), [run]);
  const savedProgress = object(run?.experimental_progress);
  const excerptCards = selected.filter((card) => { const display = stageV3DisplayText(card); return display?.before.excerpt || display?.after.excerpt; }).length;
  if (run?.engine !== V3_ENGINE && selected.length === 0) return null;
  let packageProblem: string | null = null;
  try { packageSources(run); } catch (error) { packageProblem = error instanceof Error ? error.message : 'Каталог исходных PDF не прочитан.'; }
  const needle = filter.trim().toLocaleLowerCase('ru');
  const visible = needle === '' ? parameters : parameters.filter(({ parameter }) =>
    [parameter.name, parameter.subject, parameter.location, parameter.oldValue, parameter.newValue]
      .some((value) => value.toLocaleLowerCase('ru').includes(needle)));
  const parameterPages = Math.max(1, Math.ceil(visible.length / 25));
  const currentParameterPage = Math.min(parameterPage, parameterPages - 1);
  const shownParameters = visible.slice(currentParameterPage * 25, (currentParameterPage + 1) * 25);
  const coveragePages = Math.max(1, Math.ceil(coverage.length / 50));
  const currentCoveragePage = Math.min(coveragePage, coveragePages - 1);
  const shownCoverage = coverage.slice(currentCoveragePage * 50, (currentCoveragePage + 1) * 50);
  const statuses = parameters.reduce<Record<string, number>>((counts, { parameter }) => {
    const key = parameter.verdict || 'PENDING'; counts[key] = (counts[key] ?? 0) + 1; return counts;
  }, {});
  const download = (format: 'json' | 'csv' | 'html' | 'xlsx') => {
    setFailure(null);
    try {
      if (format === 'xlsx') {
        const file = formatStageV3Xlsx(runId, cards, run);
        deliverDownload(browserDownloadSink(), new Blob([file.content], { type: file.mediaType }), file.fileName);
        return;
      }
      const body = format === 'json' ? JSON.stringify(reportSnapshot(runId, cards, run), null, 2)
        : format === 'csv' ? parameterCsv(runId, cards) : reportHtml(runId, cards, run);
      const mime = format === 'json' ? 'application/json' : format === 'csv' ? 'text/csv' : 'text/html';
      deliverDownload(browserDownloadSink(), new Blob([body], { type: `${mime};charset=utf-8` }),
        `${runId}-v3-parameters.${format}`);
    } catch (error) { setFailure(error instanceof Error ? error.message : 'Не удалось подготовить файл. Повторите скачивание.'); }
  };
  const downloadPackage = async () => {
    if (packageAbort.current !== null) return;
    const controller = new AbortController();
    packageAbort.current = controller;
    setPackageBusy(true); setPackageCancelled(false); setFailure(null);
    setPackageProgress({ phase: 'preparing', completed: 0, total: 1 });
    try {
      const sources = packageSources(run);
      const xlsx = formatStageV3Xlsx(runId, cards, run);
      const file = await buildEvidencePackage({ fileName: `${runId}-v3-evidence.zip`, kind: 'stage-v3', runId,
        reports: [
          { name: 'stage-v3-parameters.xlsx', content: xlsx.content, mediaType: xlsx.mediaType },
          { name: 'stage-v3-snapshot.json', content: JSON.stringify(reportSnapshot(runId, cards, run), null, 2), mediaType: 'application/json' },
          { name: 'stage-v3-parameters.csv', content: parameterCsv(runId, cards), mediaType: 'text/csv' },
          { name: 'stage-v3-report.html', content: reportHtml(runId, cards, run), mediaType: 'text/html' },
        ], sources, signal: controller.signal,
        onProgress: (progress) => { if (packageAbort.current === controller) setPackageProgress(progress); } });
      if (!controller.signal.aborted && packageAbort.current === controller) {
        deliverDownload(browserDownloadSink(), file.blob, file.fileName);
      }
    } catch (error) {
      if (packageAbort.current === controller) {
        if (controller.signal.aborted || error instanceof Error && error.name === 'AbortError') setPackageCancelled(true);
        else setFailure(error instanceof Error ? error.message : 'Не удалось собрать ZIP с исходными PDF.');
      }
    } finally {
      if (packageAbort.current === controller) { packageAbort.current = null; setPackageBusy(false); }
    }
  };
  return <section aria-label="Отчёт V3 по параметрам и источникам" data-stage-v3-report="">
    <h3>V3 · параметры и источники</h3>
    <p>Сохранённых карточек: {selected.length} · параметров: {parameters.length} · источников в каталоге: {sourceCount}.</p>
    <p>Только текст PDF. Машинная сверка не является решением эксперта. Проверка по нормативной базе не выполнялась.</p>
    {excerptCards > 0 ? <p>Карточек с экранными фрагментами текста сторон: {excerptCards}. Полные native-цитаты находятся в сохранённом каталоге источников, JSON/HTML/XLSX; экранный префикс не обозначает весь текст.</p> : null}
    {typeof savedProgress?.plan_version === 'string' ? <p>Отчёт по закреплённому плану <code>{savedProgress.plan_version}</code>. Счётчики относятся к известным сохранённым единицам; полнота смысловой проверки этим не подтверждается.</p> : null}
    {run?.state === 'completed' ? null : <p role="status">Сравнение ещё не завершено. Отчёт содержит только уже сохранённые карточки.</p>}
    {run?.stale || selected.some((card) => card.stale) ? <p role="status">Есть устаревшие свидетельства. Это отмечено в отчёте; обновите сравнение перед экспертным решением.</p> : null}
    <dl>{Object.entries(statuses).map(([status, count]) => <div key={status}><dt>{VERIFICATION_WORDS[status] ?? 'Не проверено'}</dt><dd>{count}</dd></div>)}</dl>
    <div>{(['xlsx', 'json', 'csv', 'html'] as const).map((format) => <button type="button" className="am-button" key={format} disabled={packageBusy}
      onClick={() => download(format)}>{format.toUpperCase()} · {format === 'csv' ? 'параметры и наблюдения' : 'параметры и источники'} ↓</button>)}</div>
    <div><button type="button" className="am-button" disabled={packageBusy || packageProblem !== null}
      onClick={() => void downloadPackage()}>ZIP · отчёт и исходные PDF ↓</button>
      {packageBusy ? <button type="button" className="am-button" onClick={() => packageAbort.current?.abort()}>Отменить сборку ZIP</button> : null}</div>
    {packageProblem === null ? null : <p>{packageProblem}</p>}
    {packageBusy && packageProgress !== null ? <p role="status">{packageProgress.phase === 'preparing' ? 'Подготовка отчётов' : packageProgress.phase === 'sources' ? 'Получение исходных PDF' : 'Упаковка ZIP'}: {packageProgress.completed} из {packageProgress.total}.</p> : null}
    {packageCancelled ? <p role="status">Сборка ZIP отменена. Файл не скачан.</p> : null}
    <p>В файл входят все сохранённые карточки и решения. Фильтр ниже и несохранённые экспертные оценки на файл не влияют. HTML можно распечатать в PDF.</p>
    <p>CSV содержит строки параметров и наблюдений. Полный каталог источников и постраничное покрытие входят в XLSX, JSON и HTML.</p>
    {failure === null ? null : <p role="alert">{failure}</p>}
    {coverage.length === 0 ? <p>Постраничное покрытие в сохранённом результате не передано.</p> : <details>
      <summary>Покрытие исходных страниц · {coverage.length}</summary>
      <p>Сопоставление страницы и выполнение её разбора — разные сведения. Это учёт текстовых процедур, без подтверждения полноты инженерной проверки.</p>
      <table><thead><tr><th>Сторона</th><th>Физическая страница PDF</th><th>Сопоставление</th><th>Обработка</th></tr></thead>
        <tbody>{shownCoverage.map((page, index) => <tr key={index}><td>{page.side === 'left' ? 'П' : page.side === 'right' ? 'Р' : 'Не передано'}</td>
          <td>{typeof page.page_number === 'number' ? page.page_number : 'Не передано'}</td>
          <td>{page.mapping_status === 'MAPPED' ? 'Сопоставлена' : page.mapping_status === 'UNMATCHED' ? 'Без пары' : 'Не передано'}</td>
          <td>{page.analysis_status === 'ANALYZED' ? 'Разбор выполнен' : page.analysis_status === 'EXCLUDED_WITH_REASON' ? 'Исключена с причиной'
            : page.analysis_status === 'PARTIAL' ? 'Частично' : page.analysis_status === 'FAILED' ? 'Ошибка разбора' : 'Ожидает разбора'}</td></tr>)}</tbody>
      </table>
      {coverage.length > 50 ? <nav aria-label="Страницы покрытия V3"><button type="button" className="am-button" disabled={currentCoveragePage === 0} onClick={() => setCoveragePage(currentCoveragePage - 1)}>Предыдущие 50 страниц</button><span> {currentCoveragePage + 1} из {coveragePages} · полный каталог входит в выгрузки. </span><button type="button" className="am-button" disabled={currentCoveragePage + 1 >= coveragePages} onClick={() => setCoveragePage(currentCoveragePage + 1)}>Следующие 50 страниц</button></nav> : null}
    </details>}
    <details><summary>Таблица параметров · {parameters.length}</summary>
      <label>Поиск параметра <input type="search" value={filter} onChange={(event) => { setFilter(event.target.value); setParameterPage(0); }} /></label>
      {parameters.length === 0 ? <p>Структурированные параметры ещё не сохранены. Наблюдения без параметров включены в выгрузку.</p> : <>
        <p>По поиску: {visible.length} из {parameters.length}. На экране до 25 параметров; выгрузки содержат все сохранённые записи.</p>
        <div style={{ overflowX: 'auto' }}><table><thead><tr><th>Объект и параметр</th><th>Исходный Miner</th><th>Независимая машинная сверка</th><th>Источники</th></tr></thead>
          <tbody>{shownParameters.map(({ card, parameter }) => <tr key={parameter.key}>
            <th scope="row">{parameter.subject}<br />{parameter.name || 'Не указано'}<p>{parameter.location}</p></th>
            <td>{parameter.oldValue || 'Не указано'} → {parameter.newValue || 'Не указано'} {parameter.unit}</td>
            <td><strong>{VERIFICATION_WORDS[parameter.verdict] ?? 'Не проверено'}</strong>
              {parameter.verdict === '' ? null : <p>{parameter.verifiedOldValue || 'Не указано'} → {parameter.verifiedNewValue || 'Не указано'} {parameter.verifiedUnit}</p>}
              <p>{parameter.explanation}</p></td>
            <td><StageV3ParameterSources parameter={parameter} card={card} onOpenEvidence={onOpenEvidence} /></td>
          </tr>)}</tbody></table></div>
        {visible.length > 25 ? <nav aria-label="Страницы параметров V3"><button type="button" className="am-button" disabled={currentParameterPage === 0} onClick={() => setParameterPage(currentParameterPage - 1)}>Предыдущие параметры</button><span> {currentParameterPage + 1} из {parameterPages} </span><button type="button" className="am-button" disabled={currentParameterPage + 1 >= parameterPages} onClick={() => setParameterPage(currentParameterPage + 1)}>Следующие параметры</button></nav> : null}
      </>}
    </details>
  </section>;
}
